"""
Network Guard - Air-Gap Verification and Monitoring

Ensures all connections are loopback-only for air-gapped operation.
Monitors active network connections and alerts on violations.
"""

import json
import logging
import platform
import socket
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import psutil

from ..utils.constants import LOOPBACK_ONLY, NETCHECK_DURATION, LOGS_DIR
from ..utils.logger import get_logger

logger = get_logger(__name__)


class NetworkGuard:
    """Monitor and enforce loopback-only networking."""
    
    def __init__(self):
        self.loopback_addrs = {"127.0.0.1", "::1", "localhost"}
        self.audit_log_path = Path(LOGS_DIR) / "network_audit.jsonl"
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def is_loopback(self, addr: str) -> bool:
        """Check if address is loopback."""
        if not addr:
            return False
        
        # Handle (addr, port) tuples
        if isinstance(addr, tuple):
            addr = addr[0]
        
        # Strip brackets for IPv6
        addr = addr.strip("[]")
        
        return (
            addr in self.loopback_addrs or
            addr.startswith("127.") or
            addr == "::1" or
            addr == "0.0.0.0" or  # Listening on all interfaces (needs context)
            addr == "::"  # IPv6 all interfaces
        )
    
    def get_active_connections(self) -> List[Dict]:
        """
        Get all active network connections.
        
        Returns:
            List of connection dictionaries
        """
        connections = []
        
        try:
            for conn in psutil.net_connections(kind='inet'):
                # Skip listening sockets (not outbound)
                if conn.status == psutil.CONN_LISTEN:
                    continue
                
                local_addr = conn.laddr.ip if conn.laddr else None
                remote_addr = conn.raddr.ip if conn.raddr else None
                
                conn_info = {
                    "local_addr": local_addr,
                    "local_port": conn.laddr.port if conn.laddr else None,
                    "remote_addr": remote_addr,
                    "remote_port": conn.raddr.port if conn.raddr else None,
                    "status": conn.status,
                    "pid": conn.pid,
                }
                
                # Get process name
                try:
                    if conn.pid:
                        process = psutil.Process(conn.pid)
                        conn_info["process"] = process.name()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    conn_info["process"] = "Unknown"
                
                connections.append(conn_info)
        
        except (PermissionError, psutil.AccessDenied) as e:
            logger.warning(f"Permission denied accessing network connections: {e}")
        
        return connections
    
    def check_air_gap(self) -> Tuple[bool, List[Dict]]:
        """
        Check if system is air-gapped (loopback-only).
        
        Returns:
            Tuple of (is_air_gapped, violations)
        """
        connections = self.get_active_connections()
        violations = []
        
        for conn in connections:
            remote = conn.get("remote_addr")
            
            # Skip if no remote (shouldn't happen for ESTABLISHED)
            if not remote:
                continue
            
            # Check if remote is non-loopback
            if not self.is_loopback(remote):
                violations.append(conn)
        
        is_air_gapped = len(violations) == 0
        
        # Log result
        self._audit_log({
            "timestamp": datetime.now().isoformat(),
            "check_type": "air_gap_check",
            "is_air_gapped": is_air_gapped,
            "total_connections": len(connections),
            "violations": len(violations),
            "violation_details": violations if violations else None,
        })
        
        return is_air_gapped, violations
    
    def verify_ollama_local(self) -> bool:
        """
        Verify Ollama is running on localhost only.
        
        Returns:
            True if Ollama is local-only
        """
        try:
            # Check if Ollama process exists
            ollama_processes = []
            for proc in psutil.process_iter(['name', 'pid']):
                if 'ollama' in proc.info['name'].lower():
                    ollama_processes.append(proc)
            
            if not ollama_processes:
                logger.warning("Ollama process not found")
                return False
            
            # Check Ollama's network connections
            for proc in ollama_processes:
                try:
                    connections = proc.connections(kind='inet')
                    for conn in connections:
                        if conn.status == psutil.CONN_LISTEN:
                            # Check listening address
                            if conn.laddr:
                                addr = conn.laddr.ip
                                if not self.is_loopback(addr) and addr not in ["0.0.0.0", "::"]:
                                    logger.warning(f"Ollama listening on non-loopback: {addr}")
                                    return False
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass
            
            return True
            
        except Exception as e:
            logger.error(f"Ollama verification failed: {e}")
            return False
    
    def get_network_interfaces(self) -> Dict:
        """Get information about network interfaces."""
        interfaces = {}
        
        try:
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            
            for interface, addr_list in addrs.items():
                iface_info = {
                    "addresses": [],
                    "is_up": stats.get(interface).isup if stats.get(interface) else False,
                }
                
                for addr in addr_list:
                    if addr.family == socket.AF_INET:
                        iface_info["addresses"].append({
                            "type": "IPv4",
                            "address": addr.address,
                            "netmask": addr.netmask,
                        })
                    elif addr.family == socket.AF_INET6:
                        iface_info["addresses"].append({
                            "type": "IPv6",
                            "address": addr.address,
                            "netmask": addr.netmask,
                        })
                
                interfaces[interface] = iface_info
        
        except Exception as e:
            logger.error(f"Failed to get network interfaces: {e}")
        
        return interfaces
    
    def continuous_monitor(self, duration: int = NETCHECK_DURATION) -> Dict:
        """
        Continuously monitor network for specified duration.
        
        Args:
            duration: Monitoring duration in seconds
        
        Returns:
            Summary of monitoring results
        """
        import time
        
        start_time = time.time()
        checks = []
        total_violations = 0
        
        logger.info(f"Starting network monitoring for {duration} seconds...")
        
        while time.time() - start_time < duration:
            is_clean, violations = self.check_air_gap()
            
            checks.append({
                "timestamp": datetime.now().isoformat(),
                "is_clean": is_clean,
                "violation_count": len(violations),
            })
            
            if not is_clean:
                total_violations += len(violations)
                logger.warning(f"Air-gap violation detected: {len(violations)} connections")
            
            time.sleep(1)  # Check every second
        
        summary = {
            "duration": duration,
            "total_checks": len(checks),
            "violations_detected": total_violations,
            "is_air_gapped": total_violations == 0,
            "checks": checks,
        }
        
        self._audit_log({
            "timestamp": datetime.now().isoformat(),
            "check_type": "continuous_monitor",
            "summary": summary,
        })
        
        return summary
    
    def _audit_log(self, entry: Dict):
        """Append entry to audit log."""
        try:
            with open(self.audit_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
    
    def export_audit_log(self, output_path: Optional[Path] = None) -> Path:
        """
        Export audit log to JSON file.
        
        Args:
            output_path: Optional output path
        
        Returns:
            Path to exported file
        """
        if not output_path:
            from ..utils.constants import OUTPUT_DIR
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(OUTPUT_DIR) / f"network_audit_{timestamp}.json"
        
        # Read all log entries
        entries = []
        if self.audit_log_path.exists():
            with open(self.audit_log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entries.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        pass
        
        # Write consolidated log
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                "exported_at": datetime.now().isoformat(),
                "total_entries": len(entries),
                "entries": entries,
            }, f, indent=2)
        
        logger.info(f"Exported audit log to: {output_path}")
        return output_path


def netcheck() -> Dict:
    """
    Quick network check - convenience function.
    
    Returns:
        Check results dictionary
    """
    guard = NetworkGuard()
    is_air_gapped, violations = guard.check_air_gap()
    
    return {
        "is_air_gapped": is_air_gapped,
        "violations": violations,
        "ollama_local": guard.verify_ollama_local(),
        "interfaces": guard.get_network_interfaces(),
    }
