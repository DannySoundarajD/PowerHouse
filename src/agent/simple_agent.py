"""
Simple agent implementation for Phase 1.
Uses single router model for all requests (no specialist routing yet).
"""

import asyncio
import time
from typing import Dict, List, Optional

from ..models.ollama_backend import get_ollama_backend
from ..utils.constants import DEFAULT_ROUTER_MODEL, ROUTER_CONTEXT_WINDOW
from ..utils.logger import get_logger
from ..utils.session_state import get_session_state

logger = get_logger(__name__)


class SimpleAgent:
    """
    Simple agent that uses router model for all tasks.
    Phase 1 implementation - no task routing or specialist models yet.
    """
    
    def __init__(
        self,
        model_id: str = DEFAULT_ROUTER_MODEL,
        session_id: Optional[str] = None,
    ):
        """
        Initialize simple agent.
        
        Args:
            model_id: Router model to use (default: qwen3.5:2b)
            session_id: Session ID for state persistence
        """
        self.model_id = model_id
        self.backend = get_ollama_backend()
        self.session_state = get_session_state()
        
        # Create or use existing session
        if session_id and self.session_state.session_exists(session_id):
            self.session_id = session_id
            logger.info(f"Resumed session: {session_id}")
        else:
            self.session_id = self.session_state.create_session(
                session_id=session_id,
                router_model=model_id,
            )
            logger.info(f"Created new session: {self.session_id}")
        
        # System prompt
        self.system_prompt = """You are Sentinel, an air-gapped AI assistant for industrial environments.
You help engineers and technical staff with:
- Document analysis and information extraction
- Engineering calculations and technical reasoning
- Code generation and debugging
- Drafting reports and approval notes

You are running entirely on-premise. All data stays local and secure.
Be concise, accurate, and professional."""
    
    async def initialize(self):
        """Initialize agent (check model availability, etc.)."""
        logger.info(f"Initializing SimpleAgent with model: {self.model_id}")
        
        # Health check
        if not await self.backend.health_check():
            raise RuntimeError("Ollama backend not accessible")
        
        # Check if model exists
        if not await self.backend.model_exists(self.model_id):
            logger.warning(f"Model {self.model_id} not found locally")
            # Could auto-pull here, but for now just warn
        
        logger.info("SimpleAgent initialized successfully")
    
    def _build_messages(self, user_input: str) -> List[Dict[str, str]]:
        """
        Build message list from session history + new user input.
        Uses context window from session state.
        """
        # Get context window (with compression if needed)
        history = self.session_state.get_context_window(self.session_id)
        
        # Build message list
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add history
        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })
        
        # Add new user input
        messages.append({"role": "user", "content": user_input})
        
        return messages
    
    async def chat(self, user_input: str) -> str:
        """
        Process user input and return response.
        
        Args:
            user_input: User's message
        
        Returns:
            Assistant's response
        """
        start_time = time.time()
        
        try:
            # Build messages with context
            messages = self._build_messages(user_input)
            
            logger.info(f"Processing chat: session={self.session_id}, messages={len(messages)}")
            
            # Call Ollama
            response = await self.backend.chat(
                model=self.model_id,
                messages=messages,
                options={
                    "num_ctx": ROUTER_CONTEXT_WINDOW,
                    "temperature": 0.7,
                },
            )
            
            # Extract response content
            message = response.get("message", {})
            assistant_message = message.get("content", "") if isinstance(message, dict) else getattr(message, 'content', '')
            
            # Extract token usage
            usage = response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            
            # Save messages to session state
            self.session_state.add_message(
                session_id=self.session_id,
                role="user",
                content=user_input,
                model_used=self.model_id,
                token_count=prompt_tokens,
            )
            
            self.session_state.add_message(
                session_id=self.session_id,
                role="assistant",
                content=assistant_message,
                model_used=self.model_id,
                token_count=completion_tokens,
            )
            
            elapsed = time.time() - start_time
            logger.info(
                f"Chat complete: session={self.session_id}, "
                f"elapsed={elapsed:.2f}s, "
                f"tokens={prompt_tokens}+{completion_tokens}"
            )
            
            return assistant_message
        
        except Exception as e:
            logger.error(f"Chat failed: {e}", exc_info=True)
            return f"Error: {str(e)}"
    
    async def chat_stream(self, user_input: str):
        """
        Stream chat response token by token.
        
        Args:
            user_input: User's message
        
        Yields:
            Response chunks
        """
        start_time = time.time()
        full_response = ""
        
        try:
            # Build messages
            messages = self._build_messages(user_input)
            
            logger.info(f"Processing streaming chat: session={self.session_id}")
            
            # Call Ollama with streaming
            stream = await self.backend.chat(
                model=self.model_id,
                messages=messages,
                options={
                    "num_ctx": ROUTER_CONTEXT_WINDOW,
                    "temperature": 0.7,
                },
                stream=True,
            )
            
            # Stream chunks
            async for chunk in stream:
                message = chunk.get("message", {})
                content = message.get("content", "") if isinstance(message, dict) else getattr(message, 'content', '')
                if content:
                    full_response += content
                    yield content
            
            # Save to session state after streaming complete
            self.session_state.add_message(
                session_id=self.session_id,
                role="user",
                content=user_input,
                model_used=self.model_id,
            )
            
            self.session_state.add_message(
                session_id=self.session_id,
                role="assistant",
                content=full_response,
                model_used=self.model_id,
            )
            
            elapsed = time.time() - start_time
            logger.info(
                f"Streaming chat complete: session={self.session_id}, "
                f"elapsed={elapsed:.2f}s, "
                f"length={len(full_response)}"
            )
        
        except Exception as e:
            logger.error(f"Streaming chat failed: {e}", exc_info=True)
            yield f"\n\nError: {str(e)}"
    
    def get_session_stats(self) -> Dict:
        """Get statistics for current session."""
        return self.session_state.get_session_stats(self.session_id)
    
    def search_history(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search conversation history."""
        return self.session_state.search_messages(self.session_id, query, top_k)
