"""
Master Agent with dynamic model routing.
Always-resident router + on-demand specialist loading.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, AsyncIterator

from ..models.ollama_backend import get_ollama_backend
from ..models.registry import get_model_registry
from ..models.manifest import ModelManifest
from ..tools import get_tool_registry, register_default_tools
from ..utils.constants import SPECIALIST_CONTEXT_WINDOW, MAX_TOOL_CALLS_PER_SUBTASK
from ..utils.logger import get_logger
from ..utils.session_state import get_session_state

logger = get_logger(__name__)


class MasterAgent:
    """
    Master agent with dynamic model routing.
    Router model stays loaded, specialists load on-demand.
    """
    
    def __init__(self, session_id: Optional[str] = None, download_progress_callback=None):
        """Initialize master agent with optional download progress callback."""
        self.backend = get_ollama_backend()
        self.registry = get_model_registry()
        self.session_state = get_session_state()
        self.download_progress_callback = download_progress_callback
        
        # Register tools
        self.tool_registry = register_default_tools()
        logger.info(f"Registered {len(self.tool_registry.list_tools())} tools")
        
        # Get router model
        self.router_manifest = self.registry.get_router_model()
        if not self.router_manifest:
            raise RuntimeError("No router model configured in registry")
        
        self.router_model = self.router_manifest.model_id
        
        # Currently loaded specialist (None = only router loaded)
        self.current_specialist: Optional[str] = None
        
        # Create or resume session
        if session_id and self.session_state.session_exists(session_id):
            self.session_id = session_id
            logger.info(f"Resumed session: {session_id}")
        else:
            self.session_id = self.session_state.create_session(
                session_id=session_id,
                router_model=self.router_model,
            )
            logger.info(f"Created session: {self.session_id}")
        
        # System prompts
        self.router_system_prompt = """You are Sentinel's task router. Analyze requests and classify them into task types.

Output JSON in this exact format:
{
  "tasks": [
    {"type": "coding", "input": "description", "depends_on": null},
    {"type": "reasoning", "input": "description", "depends_on": 0}
  ]
}

Task types:
- coding: Code generation, debugging, refactoring
- reasoning: Math, calculations, engineering analysis
- vision: Image analysis, OCR on images (NOT for reading PDF content)
- general: General conversation, simple questions, file reading, PDF content extraction

IMPORTANT: 
- For "read PDF file" or "extract text from PDF" requests, use type "general" NOT "vision"
- Vision tasks are for analyzing image content, not for reading documents
- Simple file operations should be "general" type

For simple questions, use type "general" (you handle it directly).
For multi-step requests, break into ordered sub-tasks."""
        
        self.specialist_system_prompts = {
            "coding": """You are an expert code generation specialist. When users ask for code, provide complete, working code directly in your response.

Format your responses like this:
1. Brief explanation of what the code does
2. The complete code in a code block
3. Usage example if helpful

DO NOT use tools unless specifically asked to execute/test the code. Just provide the code directly.

Example response format:
"Here's a Python function to add 20 numbers:

```python
def add_numbers(numbers):
    \"\"\"Add a list of numbers and return the sum.\"\"\"
    return sum(numbers)

# Example usage
numbers = list(range(1, 21))  # Numbers 1 to 20
result = add_numbers(numbers)
print(f"Sum of 1-20: {result}")
```

This function takes a list of numbers and returns their sum. The example shows adding numbers 1 through 20, which equals 210."

Only use tools (execute_code, file_ops) if the user explicitly asks to run/test the code.""",
            
            "reasoning": """You are a reasoning and mathematics specialist. Solve problems step-by-step, showing your work clearly.

When solving math problems:
1. Explain the approach
2. Show calculations step by step  
3. Provide the final answer clearly

You can use execute_code tool to verify complex calculations, but show the math first.""",
            
            "vision": """You are a vision specialist. Analyze images, technical drawings, P&IDs, and documents.
You have access to tools:
- analyze_image: Analyze images at full resolution with vision model or OCR
- process_pdf: Extract and analyze multi-page PDF documents
- split_pdf: Split PDF into individual page images
- analyze_large_image: Process very large images using tiled approach

Use these tools to extract information from visual content.""",
            
            "general": """You are Sentinel, an air-gapped AI assistant for industrial environments.

Answer questions directly and naturally. Only use tools when specifically needed:
- file_ops: When user asks to read/write text files or list directories
- process_document: Extract content from PDFs, Word docs, Excel sheets, PowerPoint presentations, and images
- execute_code: When user asks to run code  
- spreadsheet_ops: When user asks to analyze data
- generate_document: When user asks to create documents

IMPORTANT - Document Processing:
- When user wants to read a PDF, Word doc (.docx), Excel file (.xlsx), PowerPoint (.pptx), or image file, use the 'process_document' tool
- This tool extracts all text, tables, metadata, and structure from documents
- For PDFs: extracts text from all pages with page-by-page breakdown
- For Word: extracts paragraphs, tables, and formatting
- For Excel: extracts all sheets with data
- For PowerPoint: extracts text from all slides
- For images: provides metadata and dimensions

For general questions, conversations, and information requests, just answer naturally without using tools.""",
        }
    
    async def initialize(self):
        """Initialize agent and load router model."""
        logger.info(f"Initializing MasterAgent with router: {self.router_model}")
        
        # Health check
        if not await self.backend.health_check():
            raise RuntimeError("Ollama backend not accessible")
        
        # Check router model exists, pull if needed
        if not await self.backend.model_exists(self.router_model):
            logger.warning(f"Router model {self.router_model} not found locally")
            logger.info(f"Attempting to pull {self.router_model} from Ollama registry...")
            
            pull_success = await self.backend.pull_model(
                self.router_model, 
                progress_callback=self.download_progress_callback
            )
            
            if not pull_success:
                raise RuntimeError(f"Failed to pull router model {self.router_model}")
            
            logger.info(f"Successfully pulled router model {self.router_model}")
        
        logger.info("MasterAgent initialized successfully")
    
    async def _classify_task(self, user_input: str) -> List[Dict]:
        """
        Classify user request into task types.
        Returns list of sub-tasks with dependencies.
        """
        logger.info("Classifying task...")
        
        try:
            # Call router for classification
            response = await self.backend.chat(
                model=self.router_model,
                messages=[
                    {"role": "system", "content": self.router_system_prompt},
                    {"role": "user", "content": f"Classify this request:\n\n{user_input}"},
                ],
                options=self.router_manifest.get_options(),
            )
            
            # Parse JSON response
            message = response.get("message", {})
            content = message.get("content", "") if isinstance(message, dict) else getattr(message, 'content', '')
            
            # Try to extract JSON from response
            try:
                # Find JSON block
                start = content.find("{")
                end = content.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = content[start:end]
                    classification = json.loads(json_str)
                    tasks = classification.get("tasks", [])
                else:
                    # No JSON found, treat as general task
                    tasks = [{"type": "general", "input": user_input, "depends_on": None}]
            except json.JSONDecodeError:
                logger.warning("Failed to parse classification JSON, defaulting to general")
                tasks = [{"type": "general", "input": user_input, "depends_on": None}]
            
            logger.info(f"Classified into {len(tasks)} task(s): {[t['type'] for t in tasks]}")
            return tasks
        
        except Exception as e:
            logger.error(f"Classification failed: {e}", exc_info=True)
            # Fallback to general task
            return [{"type": "general", "input": user_input, "depends_on": None}]
    
    async def _load_specialist(self, role: str) -> Optional[ModelManifest]:
        """
        Load specialist model for a role.
        Unloads current specialist if different.
        """
        # Check if we need to switch models
        if role == "general":
            # Router handles general tasks
            return self.router_manifest
        
        manifest = self.registry.get_model_for_role(role)
        if not manifest:
            logger.warning(f"No model found for role: {role}, using router")
            return self.router_manifest
        
        specialist_id = manifest.model_id
        
        # If already loaded, no action needed
        if self.current_specialist == specialist_id:
            logger.debug(f"Specialist already loaded: {specialist_id}")
            return manifest
        
        # Unload current specialist if any
        if self.current_specialist and self.current_specialist != self.router_model:
            logger.info(f"Unloading specialist: {self.current_specialist}")
            await self.backend.unload_model(self.current_specialist)
            self.current_specialist = None
        
        # Load new specialist
        if specialist_id != self.router_model:
            logger.info(f"Loading specialist: {specialist_id} for role: {role}")
            
            # Check if model exists, if not try to pull it
            if not await self.backend.model_exists(specialist_id):
                logger.warning(f"Specialist {specialist_id} not found locally")
                logger.info(f"Attempting to pull {specialist_id} from Ollama registry...")
                
                # Try to pull the model with progress callback
                pull_success = await self.backend.pull_model(
                    specialist_id,
                    progress_callback=self.download_progress_callback
                )
                
                if pull_success:
                    logger.info(f"Successfully pulled {specialist_id}")
                else:
                    # Pull failed, try fallback
                    logger.error(f"Failed to pull {specialist_id}, trying fallback")
                    if manifest.fallback:
                        fallback_manifest = self.registry.get_model_by_name(manifest.fallback)
                        if fallback_manifest:
                            return await self._load_specialist(fallback_manifest.role)
                    # No fallback, use router
                    logger.warning(f"No fallback available, using router model")
                    return self.router_manifest
            
            self.current_specialist = specialist_id
        
        return manifest
    
    async def _execute_subtask(
        self,
        subtask: Dict,
        context_history: List[Dict],
    ) -> str:
        """Execute a single sub-task with appropriate model and tools."""
        task_type = subtask.get("type", "general")
        task_input = subtask.get("input", "")
        
        logger.info(f"Executing subtask: type={task_type}")
        
        # Load appropriate model
        manifest = await self._load_specialist(task_type)
        model_id = manifest.model_id
        
        # Build messages
        system_prompt = self.specialist_system_prompts.get(
            task_type,
            self.specialist_system_prompts["general"]
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add limited context history (last few messages)
        if context_history:
            messages.extend(context_history[-3:])
        
        # Add task input
        messages.append({"role": "user", "content": task_input})
        
        # Get tool definitions
        # Only pass tools if task explicitly needs them or for general/reasoning tasks
        # For simple coding tasks (code generation), don't pass tools to avoid confusion
        if task_type == "coding":
            # Coding specialist should generate code directly, not call execute_code
            # Only pass tools if user explicitly asks to run/test
            tools = None
        elif task_type == "vision":
            # Vision tasks need specialized tools
            tools = None  # Vision tools would be specific, not general tools
        else:
            # General and reasoning tasks can use tools when needed
            tools = self.tool_registry.get_tool_schemas()
        
        # Execute with tool calling loop
        max_iterations = MAX_TOOL_CALLS_PER_SUBTASK
        full_response = ""
        
        for iteration in range(max_iterations):
            # Call model
            response = await self.backend.chat(
                model=model_id,
                messages=messages,
                options=manifest.get_options(),
                tools=tools,
            )
            
            message = response.get("message", {})
            content = message.get("content", "") if isinstance(message, dict) else getattr(message, 'content', '')
            tool_calls = message.get("tool_calls", []) if isinstance(message, dict) else getattr(message, 'tool_calls', None) or []
            
            # Accumulate response
            if content:
                full_response += content
            
            # If no tool calls, we're done
            if not tool_calls:
                break
            
            # Execute tool calls
            logger.info(f"Executing {len(tool_calls)} tool call(s)")
            
            for tool_call in tool_calls:
                function = tool_call.get("function", {})
                tool_name = function.get("name")
                tool_args = function.get("arguments", {})
                
                logger.info(f"Tool call: {tool_name}")
                
                # Execute tool
                result = self.tool_registry.execute_tool(tool_name, **tool_args)
                
                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "content": json.dumps(result),
                    "name": tool_name,
                })
            
            # Add assistant's message with tool calls
            messages.append(message)
        
        if iteration >= max_iterations - 1:
            full_response += "\n\n(Note: Maximum tool iterations reached)"
        
        # Log token usage
        usage = response.get("usage", {})
        logger.info(
            f"Subtask complete: model={model_id}, "
            f"tokens={usage.get('prompt_tokens', 0)}+{usage.get('completion_tokens', 0)}, "
            f"tool_calls={len(tool_calls) if tool_calls else 0}"
        )
        
        return full_response or "(No response generated)"
    
    async def _merge_results(
        self,
        subtask_results: List[str],
        original_input: str,
    ) -> str:
        """Merge sub-task results into coherent response using router."""
        if len(subtask_results) == 1:
            # Single result, no merging needed
            return subtask_results[0]
        
        logger.info(f"Merging {len(subtask_results)} results...")
        
        # Build merge prompt
        results_text = "\n\n---\n\n".join(
            [f"Result {i+1}:\n{r}" for i, r in enumerate(subtask_results)]
        )
        
        merge_prompt = f"""The user asked: "{original_input}"

This request was split into multiple sub-tasks. Here are the results:

{results_text}

Synthesize these results into one coherent, well-formatted response."""
        
        # Use router for merging
        response = await self.backend.chat(
            model=self.router_model,
            messages=[
                {"role": "system", "content": "You are Sentinel. Merge sub-task results into a coherent response."},
                {"role": "user", "content": merge_prompt},
            ],
            options=self.router_manifest.get_options(),
        )
        
        message = response.get("message", {})
        merged = message.get("content", "") if isinstance(message, dict) else getattr(message, 'content', '')
        logger.info("Results merged successfully")
        
        return merged
    
    async def chat(self, user_input: str) -> str:
        """
        Process user input through routing and specialist execution.
        
        Args:
            user_input: User's message
        
        Returns:
            Final response
        """
        start_time = time.time()
        
        try:
            # Step 1: Classify task
            tasks = await self._classify_task(user_input)
            
            # Step 2: Execute each sub-task
            context_history = self.session_state.get_context_window(self.session_id)[-6:]
            subtask_results = []
            
            for i, subtask in enumerate(tasks):
                result = await self._execute_subtask(subtask, context_history)
                subtask_results.append(result)
                
                # Add to context for dependent tasks
                context_history.append({"role": "assistant", "content": result})
            
            # Step 3: Merge results if multiple tasks
            final_response = await self._merge_results(subtask_results, user_input)
            
            # Step 4: Save to session
            self.session_state.add_message(
                session_id=self.session_id,
                role="user",
                content=user_input,
                model_used=self.router_model,
            )
            
            self.session_state.add_message(
                session_id=self.session_id,
                role="assistant",
                content=final_response,
                model_used=self.current_specialist or self.router_model,
                metadata={"subtasks": len(tasks)},
            )
            
            elapsed = time.time() - start_time
            logger.info(f"Chat complete: {elapsed:.2f}s, subtasks={len(tasks)}")
            
            return final_response
        
        except Exception as e:
            logger.error(f"Chat failed: {e}", exc_info=True)
            return f"Error: {str(e)}"
    
    async def chat_stream(self, user_input: str) -> AsyncIterator[Dict]:
        """
        Stream chat with status updates.
        
        Yields:
            Status dicts with type, message, model info
        """
        try:
            # Classify
            yield {"type": "status", "message": "Classifying task...", "model": self.router_model}
            tasks = await self._classify_task(user_input)
            
            yield {
                "type": "classification",
                "message": f"Identified {len(tasks)} task(s)",
                "tasks": [t["type"] for t in tasks],
            }
            
            # Execute tasks
            context_history = self.session_state.get_context_window(self.session_id)[-6:]
            subtask_results = []
            
            for i, subtask in enumerate(tasks):
                task_type = subtask["type"]
                
                # Load model
                yield {"type": "status", "message": f"Loading {task_type} model...", "model": None}
                manifest = await self._load_specialist(task_type)
                
                yield {
                    "type": "model_loaded",
                    "message": f"Using {manifest.name}",
                    "model": manifest.model_id,
                }
                
                # Execute
                yield {"type": "status", "message": f"Processing {task_type} task...", "model": manifest.model_id}
                result = await self._execute_subtask(subtask, context_history)
                subtask_results.append(result)
                context_history.append({"role": "assistant", "content": result})
                
                yield {"type": "subtask_complete", "message": f"Task {i+1}/{len(tasks)} complete"}
            
            # Merge
            if len(tasks) > 1:
                yield {"type": "status", "message": "Merging results...", "model": self.router_model}
            
            final_response = await self._merge_results(subtask_results, user_input)
            
            # Save
            self.session_state.add_message(self.session_id, "user", user_input, self.router_model)
            self.session_state.add_message(
                self.session_id,
                "assistant",
                final_response,
                self.current_specialist or self.router_model,
                metadata={"subtasks": len(tasks)},
            )
            
            # Final response
            yield {"type": "response", "content": final_response}
        
        except Exception as e:
            logger.error(f"Streaming chat failed: {e}", exc_info=True)
            yield {"type": "error", "message": str(e)}
    
    def get_loaded_models(self) -> Dict:
        """Get currently loaded models."""
        return {
            "router": self.router_model,
            "specialist": self.current_specialist,
        }
    
    def get_session_stats(self) -> Dict:
        """Get session statistics."""
        return self.session_state.get_session_stats(self.session_id)

    async def _call_tool_async(self, tool_name: str, **kwargs) -> str:
        """
        Direct tool call helper for CLI commands.
        
        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool parameters
        
        Returns:
            Tool result as JSON string
        """
        result = self.tool_registry.execute_tool(tool_name, **kwargs)
        
        if isinstance(result, dict) and "result" in result:
            return result["result"]
        elif isinstance(result, dict):
            return json.dumps(result)
        else:
            return str(result)
    
    def get_loaded_models(self) -> Dict[str, str]:
        """Get currently loaded models."""
        return {
            "router": self.router_model,
            "specialist": self.current_specialist,
        }
