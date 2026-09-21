"""
Model manifest schema and loader for Sentinel AI Workbench.
Each model is defined by a YAML manifest file.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ModelManifest:
    """
    Model manifest schema.
    Defines all properties needed to load and use a model.
    """
    
    name: str
    role: str  # coding | reasoning | vision | drafting | embedding | general | router
    backend: str  # ollama | hf-transformers
    model_id: str
    context_window: int  # Model's advertised max context
    num_ctx: int  # Enforced context cap for this hardware
    vram_gb_min: float  # Minimum VRAM for full GPU residency
    capabilities: List[str]
    prompt_template: str  # chatml | alpaca | llama3 | custom
    fallback: Optional[str] = None  # Fallback model name if this fails
    temperature: float = 0.7
    top_p: float = 0.9
    description: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate manifest after initialization."""
        valid_roles = ["coding", "reasoning", "vision", "drafting", "embedding", "general", "router"]
        if self.role not in valid_roles:
            raise ValueError(f"Invalid role '{self.role}'. Must be one of: {valid_roles}")
        
        valid_backends = ["ollama", "hf-transformers"]
        if self.backend not in valid_backends:
            raise ValueError(f"Invalid backend '{self.backend}'. Must be one of: {valid_backends}")
        
        if self.num_ctx > self.context_window:
            logger.warning(
                f"Model {self.name}: num_ctx ({self.num_ctx}) > context_window "
                f"({self.context_window}), capping to context_window"
            )
            self.num_ctx = self.context_window
    
    @classmethod
    def from_yaml(cls, path: Path) -> "ModelManifest":
        """Load manifest from YAML file."""
        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
            
            # Extract fields
            manifest = cls(
                name=data["name"],
                role=data["role"],
                backend=data["backend"],
                model_id=data["model_id"],
                context_window=data["context_window"],
                num_ctx=data["num_ctx"],
                vram_gb_min=data["vram_gb_min"],
                capabilities=data.get("capabilities", []),
                prompt_template=data.get("prompt_template", "default-chatml"),
                fallback=data.get("fallback"),
                temperature=data.get("temperature", 0.7),
                top_p=data.get("top_p", 0.9),
                description=data.get("description"),
                metadata=data.get("metadata", {}),
            )
            
            logger.debug(f"Loaded manifest: {manifest.name} from {path}")
            return manifest
        
        except Exception as e:
            logger.error(f"Failed to load manifest from {path}: {e}")
            raise
    
    def to_yaml(self, path: Path):
        """Save manifest to YAML file."""
        data = {
            "name": self.name,
            "role": self.role,
            "backend": self.backend,
            "model_id": self.model_id,
            "context_window": self.context_window,
            "num_ctx": self.num_ctx,
            "vram_gb_min": self.vram_gb_min,
            "capabilities": self.capabilities,
            "prompt_template": self.prompt_template,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }
        
        if self.fallback:
            data["fallback"] = self.fallback
        
        if self.description:
            data["description"] = self.description
        
        if self.metadata:
            data["metadata"] = self.metadata
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            yaml.dump(data, f, sort_keys=False, default_flow_style=False)
        
        logger.info(f"Saved manifest: {self.name} to {path}")
    
    def supports_capability(self, capability: str) -> bool:
        """Check if model supports a specific capability."""
        return capability.lower() in [c.lower() for c in self.capabilities]
    
    def get_options(self) -> Dict:
        """Get Ollama options dict for this model."""
        return {
            "num_ctx": self.num_ctx,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }


def validate_manifest_schema(data: Dict) -> bool:
    """
    Validate manifest data against schema.
    Returns True if valid, raises ValueError if invalid.
    """
    required_fields = [
        "name", "role", "backend", "model_id",
        "context_window", "num_ctx", "vram_gb_min", "capabilities"
    ]
    
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    
    return True
