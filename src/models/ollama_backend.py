"""
Ollama backend adapter for Sentinel AI Workbench.
Handles communication with local Ollama service.
"""

import asyncio
from typing import Any, AsyncIterator, Dict, List, Optional

import ollama
from ollama import AsyncClient

from ..utils.constants import OLLAMA_HOST
from ..utils.logger import get_logger

logger = get_logger(__name__)


class OllamaBackend:
    """
    Ollama backend for local model inference.
    Supports chat, embeddings, and model management.
    """
    
    def __init__(self, host: str = OLLAMA_HOST):
        """Initialize Ollama backend."""
        self.host = host
        self._client: Optional[AsyncClient] = None
        self._loaded_models: set = set()
        logger.info(f"OllamaBackend initialized: {host}")
    
    @property
    def client(self) -> AsyncClient:
        """Lazy initialization of AsyncClient."""
        if self._client is None:
            self._client = AsyncClient(host=self.host)
            logger.debug(f"AsyncClient created for {self.host}")
        return self._client
    
    async def health_check(self) -> bool:
        """Check if Ollama service is accessible."""
        try:
            # Try to list models as health check
            logger.info(f"Running health check on {self.host}...")
            response = await self.client.list()
            models = response.get("models", [])
            logger.info(f"Health check passed! Found {len(models)} models")
            return True
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}", exc_info=True)
            return False
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List all available models."""
        try:
            response = await self.client.list()
            models = response.get("models", [])
            logger.debug(f"Listed {len(models)} models")
            return models
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    async def pull_model(self, model: str, progress_callback=None) -> bool:
        """
        Pull a model from Ollama registry.
        
        Args:
            model: Model tag (e.g., 'qwen3.5:2b')
            progress_callback: Optional callback(status, current, total) for progress updates
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Pulling model: {model} from Ollama registry...")
            
            # If callback provided, use streaming pull to report progress
            if progress_callback:
                def pull_with_progress():
                    for progress in ollama.pull(model, stream=True):
                        status = progress.get('status', '')
                        if progress_callback:
                            progress_callback(status, progress.get('completed', 0), progress.get('total', 0))
                
                await asyncio.to_thread(pull_with_progress)
            else:
                # Simple pull without progress
                await asyncio.to_thread(ollama.pull, model)
            
            logger.info(f"Successfully pulled model: {model}")
            return True
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}", exc_info=True)
            return False
    
    async def model_exists(self, model: str) -> bool:
        """Check if a model is available locally."""
        models = await self.list_models()
        # Check both 'name' and 'model' keys, and handle partial matches
        for m in models:
            model_id = m.get("model") or m.get("name", "")
            # Exact match or prefix match (e.g., qwen2.5:7b matches qwen2.5:7b)
            if model_id == model or model_id.startswith(model + ":"):
                return True
        return False
    
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Run chat completion with a model.
        
        Args:
            model: Model tag
            messages: List of message dicts with 'role' and 'content'
            options: Model parameters (temperature, num_ctx, etc.)
            tools: Optional tool definitions
            stream: Whether to stream response
        
        Returns:
            Response dict with 'message' and usage info
        """
        try:
            # Track loaded model
            self._loaded_models.add(model)
            
            # Prepare request
            request = {
                "model": model,
                "messages": messages,
                "stream": stream,
            }
            
            if options:
                request["options"] = options
            
            if tools:
                request["tools"] = tools
            
            logger.debug(f"Chat request: model={model}, messages={len(messages)}, stream={stream}")
            
            # Make request
            if stream:
                # Return async iterator for streaming
                return self._chat_stream(request)
            else:
                response = await self.client.chat(**request)
                
                # Log token usage if available
                if "usage" in response:
                    usage = response["usage"]
                    logger.debug(
                        f"Chat complete: model={model}, "
                        f"prompt_tokens={usage.get('prompt_tokens', 0)}, "
                        f"completion_tokens={usage.get('completion_tokens', 0)}"
                    )
                
                return response
        
        except Exception as e:
            logger.error(f"Chat request failed for {model}: {e}")
            raise
    
    async def _chat_stream(self, request: Dict) -> AsyncIterator[Dict]:
        """Internal streaming chat handler."""
        async for chunk in await self.client.chat(**request):
            yield chunk
    
    async def embed(
        self,
        model: str,
        input: str,
    ) -> List[float]:
        """
        Generate embeddings for text.
        
        Args:
            model: Embedding model tag (e.g., 'nomic-embed-text')
            input: Text to embed
        
        Returns:
            Embedding vector (list of floats)
        """
        try:
            response = await self.client.embeddings(
                model=model,
                prompt=input,
            )
            
            embedding = response.get("embedding", [])
            logger.debug(f"Generated embedding: model={model}, dim={len(embedding)}")
            return embedding
        
        except Exception as e:
            logger.error(f"Embedding request failed for {model}: {e}")
            raise
    
    async def unload_model(self, model: str):
        """
        Explicitly unload a model from memory.
        Uses Ollama's generate API with keep_alive=0.
        """
        try:
            # Setting keep_alive to 0 unloads the model immediately
            await self.client.generate(
                model=model,
                prompt="",
                keep_alive=0,
            )
            
            if model in self._loaded_models:
                self._loaded_models.remove(model)
            
            logger.info(f"Unloaded model: {model}")
        
        except Exception as e:
            logger.warning(f"Failed to unload model {model}: {e}")
    
    def get_loaded_models(self) -> List[str]:
        """Get list of models tracked as loaded."""
        return list(self._loaded_models)
    
    async def show_model_info(self, model: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a model."""
        try:
            response = await self.client.show(model)
            return response
        except Exception as e:
            logger.error(f"Failed to get info for {model}: {e}")
            return None
    
    async def close(self):
        """Close client connection."""
        # AsyncClient doesn't need explicit closing
        logger.info("OllamaBackend closed")


# Global backend instance
_ollama_backend: Optional[OllamaBackend] = None


def get_ollama_backend() -> OllamaBackend:
    """Get or create global Ollama backend instance."""
    global _ollama_backend
    if _ollama_backend is None:
        _ollama_backend = OllamaBackend()
    return _ollama_backend
