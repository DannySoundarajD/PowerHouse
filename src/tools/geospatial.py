"""
Geospatial and Facility Mapping Tools

For refinery layouts, P&ID overlays, GPS coordinates, and facility mapping.
Designed for industrial environments (refineries, PSUs, manufacturing plants).
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.tools.base import Tool
from src.utils.constants import OUTPUT_DIR, KB_DIR

logger = logging.getLogger(__name__)


class GeospatialCoordinateTool(Tool):
    """Tool for handling GPS coordinates and conversions."""
    
    def __init__(self):
        super().__init__(
            name="coordinate_operations",
            description=(
                "Perform geospatial coordinate operations including conversion between "
                "coordinate systems (lat/lon, UTM, local grid), distance calculations, "
                "and boundary checking for facility locations. "
                "Input: operation (convert|distance|validate|bounds), coordinates, parameters."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["convert", "distance", "validate", "bounds", "center"],
                        "description": "Type of operation: convert coordinates, calculate distance, validate location, check bounds, find center"
                    },
                    "coordinates": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "lat": {"type": "number"},
                                "lon": {"type": "number"},
                                "label": {"type": "string"}
                            }
                        },
                        "description": "List of coordinate points with lat, lon, and optional label"
                    },
                    "from_system": {
                        "type": "string",
                        "description": "Source coordinate system (latlon, utm, local)"
                    },
                    "to_system": {
                        "type": "string",
                        "description": "Target coordinate system (latlon, utm, local)"
                    },
                    "bounds": {
                        "type": "object",
                        "description": "Boundary box {min_lat, max_lat, min_lon, max_lon}"
                    }
                },
                "required": ["operation"]
            }
        )
    
    def _haversine_distance(self, coord1: Dict, coord2: Dict) -> float:
        """
        Calculate distance between two lat/lon points using Haversine formula.
        Returns distance in meters.
        """
        from math import radians, cos, sin, asin, sqrt
        
        lat1, lon1 = radians(coord1["lat"]), radians(coord1["lon"])
        lat2, lon2 = radians(coord2["lat"]), radians(coord2["lon"])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # Earth radius in meters
        r = 6371000
        
        return c * r
    
    def _validate_coordinates(self, coord: Dict) -> bool:
        """Validate lat/lon coordinates."""
        lat = coord.get("lat")
        lon = coord.get("lon")
        
        if lat is None or lon is None:
            return False
        
        # Latitude: -90 to 90, Longitude: -180 to 180
        return -90 <= lat <= 90 and -180 <= lon <= 180
    
    def _check_bounds(self, coord: Dict, bounds: Dict) -> bool:
        """Check if coordinate is within boundary box."""
        return (
            bounds["min_lat"] <= coord["lat"] <= bounds["max_lat"] and
            bounds["min_lon"] <= coord["lon"] <= bounds["max_lon"]
        )
    
    def _calculate_center(self, coordinates: List[Dict]) -> Dict:
        """Calculate centroid of coordinate points."""
        if not coordinates:
            return {"lat": 0, "lon": 0}
        
        avg_lat = sum(c["lat"] for c in coordinates) / len(coordinates)
        avg_lon = sum(c["lon"] for c in coordinates) / len(coordinates)
        
        return {"lat": avg_lat, "lon": avg_lon}
    
    def _execute_impl(self, **kwargs) -> str:
        """Execute geospatial coordinate operations."""
        operation = kwargs.get("operation")
        coordinates = kwargs.get("coordinates", [])
        
        try:
            result = {"operation": operation}
            
            if operation == "distance":
                if len(coordinates) < 2:
                    return json.dumps({"error": "Distance requires at least 2 coordinates"})
                
                distances = []
                for i in range(len(coordinates) - 1):
                    dist = self._haversine_distance(coordinates[i], coordinates[i+1])
                    distances.append({
                        "from": coordinates[i].get("label", f"Point {i}"),
                        "to": coordinates[i+1].get("label", f"Point {i+1}"),
                        "distance_meters": round(dist, 2),
                        "distance_km": round(dist / 1000, 3)
                    })
                
                # Total distance
                total = sum(d["distance_meters"] for d in distances)
                result["distances"] = distances
                result["total_distance_meters"] = round(total, 2)
                result["total_distance_km"] = round(total / 1000, 3)
            
            elif operation == "validate":
                validations = []
                for coord in coordinates:
                    is_valid = self._validate_coordinates(coord)
                    validations.append({
                        "label": coord.get("label", "Unknown"),
                        "lat": coord.get("lat"),
                        "lon": coord.get("lon"),
                        "valid": is_valid
                    })
                
                result["validations"] = validations
                result["all_valid"] = all(v["valid"] for v in validations)
            
            elif operation == "bounds":
                bounds = kwargs.get("bounds")
                if not bounds:
                    return json.dumps({"error": "Bounds parameter required"})
                
                checks = []
                for coord in coordinates:
                    in_bounds = self._check_bounds(coord, bounds)
                    checks.append({
                        "label": coord.get("label", "Unknown"),
                        "lat": coord.get("lat"),
                        "lon": coord.get("lon"),
                        "in_bounds": in_bounds
                    })
                
                result["bounds"] = bounds
                result["checks"] = checks
                result["all_in_bounds"] = all(c["in_bounds"] for c in checks)
            
            elif operation == "center":
                center = self._calculate_center(coordinates)
                result["center"] = center
                result["num_points"] = len(coordinates)
            
            elif operation == "convert":
                # Placeholder for coordinate system conversion
                result["message"] = "Coordinate conversion - UTM/local grid conversion requires additional libraries"
                result["coordinates"] = coordinates
            
            else:
                return json.dumps({"error": f"Unknown operation: {operation}"})
            
            return json.dumps(result, indent=2)
        
        except Exception as e:
            logger.error(f"Coordinate operation failed: {e}")
            return json.dumps({"error": str(e)})


class FacilityMapTool(Tool):
    """Tool for managing facility maps and layouts."""
    
    def __init__(self):
        super().__init__(
            name="facility_mapping",
            description=(
                "Create and manage facility maps for industrial sites (refineries, plants). "
                "Define zones, buildings, equipment locations, and safety areas. "
                "Input: operation (create|update|query|export), facility_id, data."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["create", "update", "query", "export", "list"],
                        "description": "Operation: create new map, update existing, query locations, export data, list facilities"
                    },
                    "facility_id": {
                        "type": "string",
                        "description": "Unique facility identifier"
                    },
                    "facility_name": {
                        "type": "string",
                        "description": "Facility name"
                    },
                    "zones": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "zone_id": {"type": "string"},
                                "name": {"type": "string"},
                                "type": {"type": "string"},
                                "coordinates": {"type": "array"},
                                "equipment": {"type": "array"}
                            }
                        },
                        "description": "Facility zones with coordinates and equipment"
                    },
                    "query_type": {
                        "type": "string",
                        "description": "Type of query: equipment, zone, safety, all"
                    }
                },
                "required": ["operation"]
            }
        )
        
        # Facility data storage
        self.facility_dir = Path(KB_DIR) / "facilities"
        self.facility_dir.mkdir(parents=True, exist_ok=True)
    
    def _save_facility(self, facility_id: str, data: Dict):
        """Save facility data to JSON file."""
        file_path = self.facility_dir / f"{facility_id}.json"
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_facility(self, facility_id: str) -> Optional[Dict]:
        """Load facility data from JSON file."""
        file_path = self.facility_dir / f"{facility_id}.json"
        if not file_path.exists():
            return None
        
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def _list_facilities(self) -> List[str]:
        """List all facility IDs."""
        return [f.stem for f in self.facility_dir.glob("*.json")]
    
    def _execute_impl(self, **kwargs) -> str:
        """Execute facility mapping operations."""
        operation = kwargs.get("operation")
        facility_id = kwargs.get("facility_id")
        
        try:
            result = {"operation": operation}
            
            if operation == "create":
                if not facility_id:
                    return json.dumps({"error": "facility_id required"})
                
                facility_data = {
                    "facility_id": facility_id,
                    "facility_name": kwargs.get("facility_name", facility_id),
                    "zones": kwargs.get("zones", []),
                    "created_at": Path(__file__).stat().st_mtime,
                    "metadata": {}
                }
                
                self._save_facility(facility_id, facility_data)
                result["status"] = "created"
                result["facility"] = facility_data
            
            elif operation == "update":
                if not facility_id:
                    return json.dumps({"error": "facility_id required"})
                
                existing = self._load_facility(facility_id)
                if not existing:
                    return json.dumps({"error": f"Facility {facility_id} not found"})
                
                # Update zones if provided
                if "zones" in kwargs:
                    existing["zones"] = kwargs["zones"]
                
                # Update name if provided
                if "facility_name" in kwargs:
                    existing["facility_name"] = kwargs["facility_name"]
                
                self._save_facility(facility_id, existing)
                result["status"] = "updated"
                result["facility"] = existing
            
            elif operation == "query":
                if not facility_id:
                    return json.dumps({"error": "facility_id required"})
                
                facility = self._load_facility(facility_id)
                if not facility:
                    return json.dumps({"error": f"Facility {facility_id} not found"})
                
                query_type = kwargs.get("query_type", "all")
                
                if query_type == "all":
                    result["facility"] = facility
                elif query_type == "zones":
                    result["zones"] = facility.get("zones", [])
                elif query_type == "equipment":
                    equipment = []
                    for zone in facility.get("zones", []):
                        equipment.extend(zone.get("equipment", []))
                    result["equipment"] = equipment
            
            elif operation == "list":
                facilities = self._list_facilities()
                result["facilities"] = facilities
                result["count"] = len(facilities)
            
            elif operation == "export":
                if not facility_id:
                    return json.dumps({"error": "facility_id required"})
                
                facility = self._load_facility(facility_id)
                if not facility:
                    return json.dumps({"error": f"Facility {facility_id} not found"})
                
                # Export to output directory
                export_path = Path(OUTPUT_DIR) / f"facility_{facility_id}_export.json"
                with open(export_path, 'w') as f:
                    json.dump(facility, f, indent=2)
                
                result["status"] = "exported"
                result["export_path"] = str(export_path)
            
            else:
                return json.dumps({"error": f"Unknown operation: {operation}"})
            
            return json.dumps(result, indent=2)
        
        except Exception as e:
            logger.error(f"Facility mapping failed: {e}")
            return json.dumps({"error": str(e)})


class PIDOverlayTool(Tool):
    """Tool for P&ID (Piping and Instrumentation Diagram) overlay and analysis."""
    
    def __init__(self):
        super().__init__(
            name="pid_overlay",
            description=(
                "Overlay P&ID (Piping and Instrumentation Diagrams) on facility maps. "
                "Extract equipment tags, pipe routes, valve locations from P&IDs. "
                "Input: operation (extract|overlay|query), pid_image_path, facility_id."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["extract", "overlay", "query", "annotate"],
                        "description": "Operation: extract data from P&ID, overlay on map, query equipment, add annotations"
                    },
                    "pid_image_path": {
                        "type": "string",
                        "description": "Path to P&ID image file"
                    },
                    "facility_id": {
                        "type": "string",
                        "description": "Facility ID to associate with P&ID"
                    },
                    "equipment_tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of equipment tag numbers to extract"
                    },
                    "annotations": {
                        "type": "array",
                        "description": "Annotations to add to P&ID"
                    }
                },
                "required": ["operation"]
            }
        )
        
        self.pid_dir = Path(KB_DIR) / "pids"
        self.pid_dir.mkdir(parents=True, exist_ok=True)
    
    def _extract_equipment_tags(self, pid_path: Path) -> List[Dict]:
        """
        Extract equipment tags from P&ID using OCR.
        This is a simplified version - full implementation would use
        specialized P&ID parsing libraries or trained models.
        """
        # Placeholder for equipment tag extraction
        # In production, this would use:
        # - OCR to find text patterns (e.g., "P-101", "V-205")
        # - Symbol recognition for equipment types
        # - Line following for piping routes
        
        return [
            {
                "tag": "P-101",
                "type": "pump",
                "location": {"x": 100, "y": 150},
                "status": "extracted"
            },
            {
                "tag": "V-201",
                "type": "valve",
                "location": {"x": 250, "y": 180},
                "status": "extracted"
            }
        ]
    
    def _execute_impl(self, **kwargs) -> str:
        """Execute P&ID overlay operations."""
        operation = kwargs.get("operation")
        
        try:
            result = {"operation": operation}
            
            if operation == "extract":
                pid_image_path = kwargs.get("pid_image_path")
                if not pid_image_path:
                    return json.dumps({"error": "pid_image_path required"})
                
                pid_path = Path(pid_image_path)
                if not pid_path.exists():
                    return json.dumps({"error": f"P&ID image not found: {pid_image_path}"})
                
                # Extract equipment tags
                equipment = self._extract_equipment_tags(pid_path)
                
                result["pid_image"] = str(pid_path)
                result["equipment_found"] = len(equipment)
                result["equipment"] = equipment
                result["note"] = "Full P&ID parsing requires specialized vision model or OCR library"
            
            elif operation == "overlay":
                facility_id = kwargs.get("facility_id")
                pid_image_path = kwargs.get("pid_image_path")
                
                if not facility_id or not pid_image_path:
                    return json.dumps({"error": "facility_id and pid_image_path required"})
                
                # Store P&ID association with facility
                overlay_data = {
                    "facility_id": facility_id,
                    "pid_image": pid_image_path,
                    "timestamp": Path(__file__).stat().st_mtime
                }
                
                overlay_path = self.pid_dir / f"{facility_id}_overlay.json"
                with open(overlay_path, 'w') as f:
                    json.dump(overlay_data, f, indent=2)
                
                result["status"] = "overlaid"
                result["overlay_file"] = str(overlay_path)
            
            elif operation == "query":
                facility_id = kwargs.get("facility_id")
                if not facility_id:
                    return json.dumps({"error": "facility_id required"})
                
                overlay_path = self.pid_dir / f"{facility_id}_overlay.json"
                if not overlay_path.exists():
                    return json.dumps({"error": f"No P&ID overlay found for facility {facility_id}"})
                
                with open(overlay_path, 'r') as f:
                    overlay_data = json.load(f)
                
                result["overlay"] = overlay_data
            
            elif operation == "annotate":
                annotations = kwargs.get("annotations", [])
                result["annotations"] = annotations
                result["note"] = "Annotations can be added to P&ID overlays for reference"
            
            else:
                return json.dumps({"error": f"Unknown operation: {operation}"})
            
            return json.dumps(result, indent=2)
        
        except Exception as e:
            logger.error(f"P&ID overlay failed: {e}")
            return json.dumps({"error": str(e)})


class SafetyZoneTool(Tool):
    """Tool for managing safety zones and restricted areas."""
    
    def __init__(self):
        super().__init__(
            name="safety_zones",
            description=(
                "Define and manage safety zones, restricted areas, and hazard zones "
                "for industrial facilities. Check if coordinates fall within safety zones. "
                "Input: operation (define|check|list), zone_data, coordinates."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["define", "check", "list", "export"],
                        "description": "Operation: define new zone, check location, list zones, export data"
                    },
                    "zone_id": {
                        "type": "string",
                        "description": "Zone identifier"
                    },
                    "zone_type": {
                        "type": "string",
                        "enum": ["safe", "restricted", "hazard", "emergency_assembly"],
                        "description": "Type of safety zone"
                    },
                    "boundary": {
                        "type": "array",
                        "description": "Boundary coordinates defining the zone"
                    },
                    "check_location": {
                        "type": "object",
                        "description": "Location to check {lat, lon}"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional zone metadata (hazard type, access level, etc.)"
                    }
                },
                "required": ["operation"]
            }
        )
        
        self.safety_dir = Path(KB_DIR) / "safety_zones"
        self.safety_dir.mkdir(parents=True, exist_ok=True)
    
    def _point_in_polygon(self, point: Dict, polygon: List[Dict]) -> bool:
        """
        Check if a point is inside a polygon using ray casting algorithm.
        Point and polygon vertices are {lat, lon} dicts.
        """
        x, y = point["lon"], point["lat"]
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]["lon"], polygon[0]["lat"]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]["lon"], polygon[i % n]["lat"]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    def _execute_impl(self, **kwargs) -> str:
        """Execute safety zone operations."""
        operation = kwargs.get("operation")
        
        try:
            result = {"operation": operation}
            
            if operation == "define":
                zone_id = kwargs.get("zone_id")
                if not zone_id:
                    return json.dumps({"error": "zone_id required"})
                
                zone_data = {
                    "zone_id": zone_id,
                    "zone_type": kwargs.get("zone_type", "safe"),
                    "boundary": kwargs.get("boundary", []),
                    "metadata": kwargs.get("metadata", {}),
                    "created_at": Path(__file__).stat().st_mtime
                }
                
                zone_path = self.safety_dir / f"{zone_id}.json"
                with open(zone_path, 'w') as f:
                    json.dump(zone_data, f, indent=2)
                
                result["status"] = "defined"
                result["zone"] = zone_data
            
            elif operation == "check":
                check_location = kwargs.get("check_location")
                if not check_location:
                    return json.dumps({"error": "check_location required"})
                
                # Check against all zones
                zones_checked = []
                for zone_file in self.safety_dir.glob("*.json"):
                    with open(zone_file, 'r') as f:
                        zone = json.load(f)
                    
                    boundary = zone.get("boundary", [])
                    if boundary:
                        is_inside = self._point_in_polygon(check_location, boundary)
                        zones_checked.append({
                            "zone_id": zone["zone_id"],
                            "zone_type": zone["zone_type"],
                            "is_inside": is_inside
                        })
                
                result["location"] = check_location
                result["zones_checked"] = zones_checked
                
                # Determine overall status
                in_hazard = any(z["is_inside"] and z["zone_type"] == "hazard" for z in zones_checked)
                in_restricted = any(z["is_inside"] and z["zone_type"] == "restricted" for z in zones_checked)
                
                result["status"] = "hazard" if in_hazard else ("restricted" if in_restricted else "safe")
            
            elif operation == "list":
                zones = []
                for zone_file in self.safety_dir.glob("*.json"):
                    with open(zone_file, 'r') as f:
                        zone = json.load(f)
                    zones.append({
                        "zone_id": zone["zone_id"],
                        "zone_type": zone["zone_type"],
                        "boundary_points": len(zone.get("boundary", []))
                    })
                
                result["zones"] = zones
                result["count"] = len(zones)
            
            elif operation == "export":
                # Export all zones
                all_zones = []
                for zone_file in self.safety_dir.glob("*.json"):
                    with open(zone_file, 'r') as f:
                        all_zones.append(json.load(f))
                
                export_path = Path(OUTPUT_DIR) / "safety_zones_export.json"
                with open(export_path, 'w') as f:
                    json.dump(all_zones, f, indent=2)
                
                result["status"] = "exported"
                result["export_path"] = str(export_path)
                result["zones_exported"] = len(all_zones)
            
            else:
                return json.dumps({"error": f"Unknown operation: {operation}"})
            
            return json.dumps(result, indent=2)
        
        except Exception as e:
            logger.error(f"Safety zone operation failed: {e}")
            return json.dumps({"error": str(e)})
