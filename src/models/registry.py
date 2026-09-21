"""
Model registry for Sentinel AI Workbench.
Central registry for all available models with hot-reload support.
"""

from pathlib import Path
from typing import Dict, List, Optional

from .manifest import ModelManifest
from ..utils.constants import MODELS_DIR, DEFAULT_ROUTER_MODEL
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ModelRegistry:
    """
    Central registry for model manifests.
    Supports hot-reload and role-based lookup.
    """
    
    def __init__(self, manifest_dir: Path = MODELS_DIR):
        """Initialize registry."""
        self.manifest_dir = manifest_dir
        self.models: Dict[str, ModelManifest] = {}  # name -> manifest
        self.role_map: Dict[str, str] = {}  # role -> default model name
        
        logger.info(f"ModelRegistry initialized: {manifest_dir}")
    
    def load_manifests(self, directory: Optional[Path] = None):
        """
        Scan directory for YAML manifests and load them.
        
        Args:
            directory: Directory to scan (defaults to self.manifest_dir)
        """
        scan_dir = directory or self.manifest_dir
        
        if not scan_dir.exists():
            logger.warning(f"Manifest directory not found: {scan_dir}")
            scan_dir.mkdir(parents=True, exist_ok=True)
            return
        
        yaml_files = list(scan_dir.glob("*.yaml")) + list(scan_dir.glob("*.yml"))
        
        logger.info(f"Scanning {scan_dir} for manifests...")
        loaded_count = 0
        
        for yaml_file in yaml_files:
            try:
                manifest = ModelManifest.from_yaml(yaml_file)
                self.register_model(manifest)
                loaded_count += 1
            except Exception as e:
                logger.error(f"Failed to load {yaml_file}: {e}")
        
        logger.info(f"Loaded {loaded_count} model manifests")
    
    def register_model(self, manifest: ModelManifest):
        """
        Register a model manifest.
        
        Args:
            manifest: ModelManifest to register
        """
        # Store by name
        self.models[manifest.name] = manifest
        
        # Update role map (first registered model for role becomes default)
        if manifest.role not in self.role_map:
            self.role_map[manifest.role] = manifest.name
            logger.info(f"Registered {manifest.name} as default for role: {manifest.role}")
        else:
            logger.debug(f"Registered {manifest.name} for role: {manifest.role} (not default)")
    
    def get_model_by_name(self, name: str) -> Optional[ModelManifest]:
        """Get model by name."""
        return self.models.get(name)
    
    def get_model_for_role(self, role: str) -> Optional[ModelManifest]:
        """
        Get default model for a role.
        
        Args:
            role: Role name (coding, reasoning, vision, etc.)
        
        Returns:
            ModelManifest for that role, or None if not found
        """
        model_name = self.role_map.get(role)
        if not model_name:
            logger.warning(f"No model registered for role: {role}")
            return None
        
        return self.get_model_by_name(model_name)
    
    def set_default_for_role(self, role: str, model_name: str):
        """
        Override default model for a role.
        
        Args:
            role: Role name
            model_name: Model name to set as default
        
        Raises:
            ValueError: If model doesn't exist or role mismatch
        """
        manifest = self.get_model_by_name(model_name)
        
        if not manifest:
            raise ValueError(f"Model not found: {model_name}")
        
        if manifest.role != role:
            raise ValueError(
                f"Model {model_name} has role '{manifest.role}', "
                f"cannot assign to role '{role}'"
            )
        
        self.role_map[role] = model_name
        logger.info(f"Set {model_name} as default for role: {role}")
    
    def list_models(self) -> List[ModelManifest]:
        """Get list of all registered models."""
        return list(self.models.values())
    
    def list_models_by_role(self, role: str) -> List[ModelManifest]:
        """Get all models for a specific role."""
        return [m for m in self.models.values() if m.role == role]
    
    def get_router_model(self) -> Optional[ModelManifest]:
        """Get the router model."""
        # Try role-based lookup first
        router = self.get_model_for_role("router")
        if router:
            return router
        
        # Fallback: look for default router model by name
        router = self.get_model_by_name(DEFAULT_ROUTER_MODEL.replace(":", "-"))
        if router:
            return router
        
        # Last resort: any general model
        return self.get_model_for_role("general")
    
    def model_exists(self, name: str) -> bool:
        """Check if model is registered."""
        return name in self.models
    
    def reload_manifest(self, path: Path):
        """
        Reload a specific manifest file.
        Supports hot-reload.
        
        Args:
            path: Path to YAML manifest
        """
        try:
            manifest = ModelManifest.from_yaml(path)
            
            # If model was already registered, update it
            if manifest.name in self.models:
                old_role = self.models[manifest.name].role
                self.register_model(manifest)
                logger.info(f"Reloaded manifest: {manifest.name}")
                
                # If role changed and was default, update role map
                if old_role != manifest.role and self.role_map.get(old_role) == manifest.name:
                    del self.role_map[old_role]
                    if manifest.role not in self.role_map:
                        self.role_map[manifest.role] = manifest.name
            else:
                self.register_model(manifest)
                logger.info(f"Loaded new manifest: {manifest.name}")
        
        except Exception as e:
            logger.error(f"Failed to reload manifest {path}: {e}")
            raise
    
    def get_role_assignments(self) -> Dict[str, str]:
        """Get current role -> model assignments."""
        return self.role_map.copy()
    
    def get_summary(self) -> Dict:
        """Get summary of registry state."""
        return {
            "total_models": len(self.models),
            "models_by_role": {
                role: len(self.list_models_by_role(role))
                for role in set(m.role for m in self.models.values())
            },
            "role_assignments": self.role_map.copy(),
            "manifest_directory": str(self.manifest_dir),
        }


# Global registry instance
_model_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    """Get or create global model registry instance."""
    global _model_registry
    if _model_registry is None:
        _model_registry = ModelRegistry()
        # Auto-load manifests on first access
        _model_registry.load_manifests()
    return _model_registry
