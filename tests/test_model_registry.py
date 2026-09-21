"""
Unit tests for Model Registry and Manifest system.
"""

import pytest
import tempfile
from pathlib import Path

from src.models.manifest import ModelManifest
from src.models.registry import ModelRegistry


@pytest.fixture
def temp_manifest_dir():
    """Create temporary directory for manifests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_manifest_creation():
    """Test creating a model manifest."""
    manifest = ModelManifest(
        name="test-model",
        role="coding",
        backend="ollama",
        model_id="test:latest",
        context_window=4096,
        num_ctx=2048,
        vram_gb_min=2.0,
        capabilities=["code-generation"],
        prompt_template="chatml",
    )
    
    assert manifest.name == "test-model"
    assert manifest.role == "coding"
    assert manifest.num_ctx == 2048


def test_manifest_yaml_roundtrip(temp_manifest_dir):
    """Test saving and loading manifest from YAML."""
    original = ModelManifest(
        name="test-model",
        role="reasoning",
        backend="ollama",
        model_id="test:7b",
        context_window=8192,
        num_ctx=4096,
        vram_gb_min=4.5,
        capabilities=["reasoning", "math"],
        prompt_template="chatml",
        fallback="fallback-model",
    )
    
    # Save
    yaml_path = temp_manifest_dir / "test-model.yaml"
    original.to_yaml(yaml_path)
    
    assert yaml_path.exists()
    
    # Load
    loaded = ModelManifest.from_yaml(yaml_path)
    
    assert loaded.name == original.name
    assert loaded.role == original.role
    assert loaded.model_id == original.model_id
    assert loaded.fallback == original.fallback


def test_registry_register_model():
    """Test registering models in registry."""
    registry = ModelRegistry(manifest_dir=Path("/tmp/test"))
    
    manifest1 = ModelManifest(
        name="router",
        role="router",
        backend="ollama",
        model_id="qwen3.5:2b",
        context_window=4096,
        num_ctx=2048,
        vram_gb_min=2.7,
        capabilities=["routing"],
        prompt_template="chatml",
    )
    
    registry.register_model(manifest1)
    
    assert registry.model_exists("router")
    assert registry.get_model_by_name("router") == manifest1
    assert registry.get_model_for_role("router") == manifest1


def test_registry_role_map():
    """Test role to model mapping."""
    registry = ModelRegistry(manifest_dir=Path("/tmp/test"))
    
    # Register first coding model
    manifest1 = ModelManifest(
        name="coder-3b",
        role="coding",
        backend="ollama",
        model_id="coder:3b",
        context_window=4096,
        num_ctx=2048,
        vram_gb_min=2.0,
        capabilities=["coding"],
        prompt_template="chatml",
    )
    
    registry.register_model(manifest1)
    
    # Should be default for coding
    assert registry.get_model_for_role("coding") == manifest1
    
    # Register second coding model
    manifest2 = ModelManifest(
        name="coder-7b",
        role="coding",
        backend="ollama",
        model_id="coder:7b",
        context_window=4096,
        num_ctx=2048,
        vram_gb_min=4.0,
        capabilities=["coding"],
        prompt_template="chatml",
    )
    
    registry.register_model(manifest2)
    
    # First should still be default
    assert registry.get_model_for_role("coding") == manifest1
    
    # Can override
    registry.set_default_for_role("coding", "coder-7b")
    assert registry.get_model_for_role("coding") == manifest2


def test_registry_list_by_role():
    """Test listing models by role."""
    registry = ModelRegistry(manifest_dir=Path("/tmp/test"))
    
    # Add multiple models with different roles
    for i in range(3):
        manifest = ModelManifest(
            name=f"coder-{i}",
            role="coding",
            backend="ollama",
            model_id=f"coder:{i}",
            context_window=4096,
            num_ctx=2048,
            vram_gb_min=2.0,
            capabilities=["coding"],
            prompt_template="chatml",
        )
        registry.register_model(manifest)
    
    # Add one reasoning model
    manifest = ModelManifest(
        name="reasoner",
        role="reasoning",
        backend="ollama",
        model_id="reasoner:7b",
        context_window=4096,
        num_ctx=2048,
        vram_gb_min=4.0,
        capabilities=["reasoning"],
        prompt_template="chatml",
    )
    registry.register_model(manifest)
    
    # List by role
    coding_models = registry.list_models_by_role("coding")
    assert len(coding_models) == 3
    
    reasoning_models = registry.list_models_by_role("reasoning")
    assert len(reasoning_models) == 1


def test_manifest_validation():
    """Test manifest validation."""
    # Valid manifest
    manifest = ModelManifest(
        name="test",
        role="coding",
        backend="ollama",
        model_id="test:1b",
        context_window=4096,
        num_ctx=2048,
        vram_gb_min=1.0,
        capabilities=[],
        prompt_template="chatml",
    )
    
    # Invalid role
    with pytest.raises(ValueError, match="Invalid role"):
        ModelManifest(
            name="test",
            role="invalid_role",
            backend="ollama",
            model_id="test:1b",
            context_window=4096,
            num_ctx=2048,
            vram_gb_min=1.0,
            capabilities=[],
            prompt_template="chatml",
        )
    
    # Invalid backend
    with pytest.raises(ValueError, match="Invalid backend"):
        ModelManifest(
            name="test",
            role="coding",
            backend="invalid_backend",
            model_id="test:1b",
            context_window=4096,
            num_ctx=2048,
            vram_gb_min=1.0,
            capabilities=[],
            prompt_template="chatml",
        )
