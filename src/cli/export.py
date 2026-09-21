"""
Session export utilities for Sentinel AI Workbench.
Export conversations, KB stats, and audit logs.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..utils.session_state import get_session_state
from ..utils.logger import get_logger
from ..utils.constants import OUTPUT_DIR

logger = get_logger(__name__)


class SessionExporter:
    """Export session data in various formats."""
    
    def __init__(self):
        self.session_state = get_session_state()
        self.output_dir = Path(OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_session_json(
        self, 
        session_id: str,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Export session to JSON file.
        
        Args:
            session_id: Session ID to export
            output_path: Optional output path (default: auto-generated)
        
        Returns:
            Path to exported file
        """
        # Get session data
        messages = self.session_state.get_messages(session_id)
        stats = self.session_state.get_stats(session_id)
        metadata = self.session_state.get_session_metadata(session_id)
        
        export_data = {
            "session_id": session_id,
            "exported_at": datetime.now().isoformat(),
            "metadata": metadata,
            "statistics": stats,
            "messages": messages,
        }
        
        # Determine output path
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"session_{session_id[:8]}_{timestamp}.json"
            output_path = self.output_dir / filename
        
        # Write JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported session to: {output_path}")
        return output_path
    
    def export_session_markdown(
        self,
        session_id: str,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Export session to Markdown file.
        
        Args:
            session_id: Session ID to export
            output_path: Optional output path
        
        Returns:
            Path to exported file
        """
        # Get session data
        messages = self.session_state.get_messages(session_id)
        stats = self.session_state.get_stats(session_id)
        metadata = self.session_state.get_session_metadata(session_id)
        
        # Build markdown
        lines = []
        lines.append(f"# Sentinel AI Session Export")
        lines.append(f"\n**Session ID:** `{session_id}`")
        lines.append(f"**Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Router Model:** {metadata.get('router_model', 'N/A')}")
        lines.append(f"\n## Statistics\n")
        lines.append(f"- **Messages:** {stats.get('message_count', 0)}")
        lines.append(f"- **Total Tokens:** {stats.get('total_tokens', 0)}")
        lines.append(f"- **Models Used:** {', '.join(stats.get('models_used', []))}")
        
        lines.append(f"\n## Conversation\n")
        
        for msg in messages:
            role = msg.get("role", "unknown").title()
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            model = msg.get("model_used", "")
            
            lines.append(f"\n### {role}")
            if timestamp:
                lines.append(f"*{timestamp}*")
            if model and role.lower() == "assistant":
                lines.append(f"*Model: {model}*")
            lines.append(f"\n{content}\n")
            lines.append("---")
        
        markdown_text = "\n".join(lines)
        
        # Determine output path
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"session_{session_id[:8]}_{timestamp}.md"
            output_path = self.output_dir / filename
        
        # Write markdown
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_text)
        
        logger.info(f"Exported session to: {output_path}")
        return output_path
    
    def export_kb_stats(self, output_path: Optional[Path] = None) -> Path:
        """
        Export knowledge base statistics to JSON.
        
        Args:
            output_path: Optional output path
        
        Returns:
            Path to exported file
        """
        from ..tools.local_rag import KBStatsTool
        
        tool = KBStatsTool()
        result_json = tool.execute()
        
        # Determine output path
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"kb_stats_{timestamp}.json"
            output_path = self.output_dir / filename
        
        # Write JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result_json)
        
        logger.info(f"Exported KB stats to: {output_path}")
        return output_path


def export_session(session_id: str, format: str = "json") -> Path:
    """
    Convenience function to export session.
    
    Args:
        session_id: Session ID
        format: Export format ('json' or 'markdown')
    
    Returns:
        Path to exported file
    """
    exporter = SessionExporter()
    
    if format == "json":
        return exporter.export_session_json(session_id)
    elif format == "markdown" or format == "md":
        return exporter.export_session_markdown(session_id)
    else:
        raise ValueError(f"Unsupported format: {format}")
