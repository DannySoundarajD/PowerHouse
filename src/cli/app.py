"""
Textual TUI application for Sentinel AI Workbench.
Phase 1: Basic REPL with single-model chat.
"""

import asyncio
import sys
from pathlib import Path

from rich.markdown import Markdown
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static
from textual.suggester import Suggester
import time

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agent.master_agent import MasterAgent
from src.models.registry import get_model_registry
from src.utils.constants import APP_NAME, CLI_WELCOME_MESSAGE, DEFAULT_ROUTER_MODEL, VERSION
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ProgressTracker:
    """Track download progress and thinking time."""
    
    def __init__(self, output_widget):
        self.output = output_widget
        self.start_time = None
        self.progress_line = None
    
    def start_thinking(self):
        """Start thinking timer."""
        self.start_time = time.time()
    
    def get_elapsed_time(self) -> str:
        """Get formatted elapsed time."""
        if self.start_time is None:
            return "0.0s"
        elapsed = time.time() - self.start_time
        return f"{elapsed:.1f}s"
    
    def stop_thinking(self):
        """Stop thinking timer and return elapsed time."""
        elapsed = self.get_elapsed_time()
        self.start_time = None
        return elapsed
    
    def show_download_progress(self, status: str, current: int, total: int):
        """Show download progress."""
        if total > 0:
            percent = (current / total) * 100
            bar_length = 30
            filled = int(bar_length * current / total)
            bar = "█" * filled + "░" * (bar_length - filled)
            size_mb = total / (1024 * 1024)
            current_mb = current / (1024 * 1024)
            self.output.write(
                f"[dim]→ {status}: {bar} {percent:.1f}% ({current_mb:.1f}/{size_mb:.1f} MB)[/dim]"
            )
        else:
            self.output.write(f"[dim]→ {status}[/dim]")


class CommandSuggester(Suggester):
    """Suggest slash commands as user types."""
    
    async def get_suggestion(self, value: str) -> str | None:
        """Return a suggestion for the current input value."""
        if not value.startswith("/"):
            return None
        
        commands = [
            "/help",
            "/clear", 
            "/stats",
            "/model",
            "/model list",
            "/model info <name>",
            "/search <query>",
            "/kb",
            "/kb list",
            "/kb add <category> <file>",
            "/kb search <query>",
        ]
        
        # Find commands that start with the current value
        for cmd in commands:
            if cmd.startswith(value.lower()) and cmd != value:
                # Return the rest of the command as suggestion
                return cmd[len(value):]
        
        return None


class SentinelCLI(App):
    """Sentinel AI Workbench TUI Application."""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #header {
        dock: top;
        height: 3;
        background: $primary;
        color: $text;
        content-align: center middle;
    }
    
    #chat-container {
        height: 1fr;
        padding: 1;
    }
    
    #output {
        height: 1fr;
        border: solid $primary;
        background: $surface;
    }
    
    #status {
        dock: bottom;
        height: 3;
        background: $panel;
        padding: 0 1;
    }
    
    #input {
        dock: bottom;
        margin: 0 1 1 1;
    }
    """
    
    TITLE = f"{APP_NAME} v{VERSION}"
    SUB_TITLE = "Air-Gapped Industrial AI — Type /help for commands"
    
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+l", "clear", "Clear"),
    ]
    
    def __init__(self):
        super().__init__()
        self.agent: MasterAgent = None
        self.registry = get_model_registry()
        self.initializing = False
        self.progress_tracker = None  # Will be initialized after output widget is available
    
    def compose(self) -> ComposeResult:
        """Create UI layout."""
        yield Header()
        
        with Container(id="chat-container"):
            yield RichLog(
                id="output",
                auto_scroll=True,
                highlight=True,
                markup=True,
                wrap=True,
            )
        
        yield Static(id="status")
        yield Input(
            placeholder="⏳ Loading system... Please wait...",
            id="input",
            disabled=True,
            suggester=CommandSuggester(use_cache=False, case_sensitive=False),
        )
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when app is mounted."""
        self.output = self.query_one("#output", RichLog)
        self.status_bar = self.query_one("#status", Static)
        self.input_widget = self.query_one("#input", Input)
        
        # Initialize progress tracker
        self.progress_tracker = ProgressTracker(self.output)
        
        # Disable input until agent is ready
        self.input_widget.disabled = True
        
        # Show welcome message
        self.output.write(Text(CLI_WELCOME_MESSAGE, style="bold cyan"))
        
        # Initialize agent in background
        asyncio.create_task(self._initialize_agent())
    
    async def _initialize_agent(self):
        """Initialize agent asynchronously and pre-load router model."""
        if self.initializing:
            return
        
        self.initializing = True
        self.update_status("🔄 Initializing system...", "yellow")
        
        try:
            # Load model registry first
            self.output.write("[bold]Loading model registry...[/bold]")
            router_model = self.registry.get_router_model()
            
            if not router_model:
                raise RuntimeError("No router model found in registry")
            
            self.output.write(f"Router: [cyan]{router_model.name}[/cyan] ([dim]{router_model.model_id}[/dim])")
            
            # Initialize master agent
            self.update_status("🔄 Initializing AI agent...", "yellow")
            
            # Create progress callback for model pulling
            def download_progress(status: str, current: int, total: int):
                self.progress_tracker.show_download_progress(status, current, total)
            
            self.agent = MasterAgent(download_progress_callback=download_progress)
            
            # Start thinking timer for initialization
            self.progress_tracker.start_thinking()
            await self.agent.initialize()
            elapsed = self.progress_tracker.stop_thinking()
            
            session_id = self.agent.session_id[:8]
            self.output.write(f"Session ID: [dim]{self.agent.session_id}[/dim]")
            self.output.write(f"[dim]Initialization took {elapsed}[/dim]")
            
            # Show model summary
            summary = self.registry.get_summary()
            self.output.write(f"Available models: [cyan]{summary['total_models']}[/cyan]")
            
            # PRE-LOAD ROUTER MODEL - This is the key step!
            self.update_status(f"🔄 Pre-loading router model ({router_model.model_id})...", "yellow")
            self.output.write(f"\n[bold yellow]⏳ Loading {router_model.model_id} into memory...[/bold yellow]")
            
            try:
                # Send a dummy message to load the model
                from src.models.ollama_backend import get_ollama_backend
                backend = get_ollama_backend()
                
                self.progress_tracker.start_thinking()
                test_response = await backend.chat(
                    model=router_model.model_id,
                    messages=[{"role": "user", "content": "hi"}],
                    options={"num_predict": 1},  # Generate only 1 token to be fast
                )
                elapsed = self.progress_tracker.stop_thinking()
                
                self.output.write(f"[bold green]✓ Model loaded and ready! (took {elapsed})[/bold green]\n")
                
            except Exception as e:
                logger.warning(f"Model pre-load warning: {e}")
                self.output.write(f"[yellow]⚠ Model pre-load completed with warning[/yellow]\n")
            
            # Enable input now that everything is ready
            self.input_widget.disabled = False
            self.input_widget.placeholder = "✅ Type your message or /help for commands..."
            self.input_widget.focus()
            
            loaded = self.agent.get_loaded_models()
            self.update_status(
                f"✅ Ready | Session: {session_id} | Models: {summary['total_models']}",
                "green bold"
            )
            
            self.output.write("[bold green]═══════════════════════════════════════[/bold green]")
            self.output.write("[bold green]✓ System Ready - You can start chatting![/bold green]")
            self.output.write("[bold green]═══════════════════════════════════════[/bold green]\n")
            
        except Exception as e:
            error_msg = f"Failed to initialize: {e}"
            self.output.write(f"[red bold]✗ {error_msg}[/red bold]")
            self.update_status(f"❌ Error: {error_msg}", "red")
            logger.error(f"Agent initialization failed: {e}", exc_info=True)
            
            # Enable input even on error so user can try commands
            self.input_widget.disabled = False
    
    def update_status(self, message: str, style: str = "white"):
        """Update status bar."""
        self.status_bar.update(Text(message, style=style))
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        user_input = event.value.strip()
        
        if not user_input:
            return
        
        # Clear input
        self.input_widget.value = ""
        
        # Show user input
        self.output.write(f"[bold cyan]User:[/bold cyan] {user_input}")
        
        # Check if agent is ready
        if not self.agent:
            self.output.write("[yellow]⚠ Agent not initialized yet. Please wait...[/yellow]")
            return
        
        # Handle slash commands
        if user_input.startswith("/"):
            await self.handle_command(user_input)
            return
        
        # Process chat
        await self.handle_chat(user_input)
    
    async def handle_command(self, command: str):
        """Handle slash commands."""
        # If user types just "/", show all available commands
        if command == "/":
            self.show_all_commands()
            return
        
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd == "/help":
            self.show_help()
        
        elif cmd == "/clear":
            self.output.clear()
            self.output.write(Text("Chat cleared", style="dim"))
        
        elif cmd == "/stats":
            self.show_stats()
        
        elif cmd == "/model":
            await self.handle_model_command(args)
        
        elif cmd == "/search":
            if not args:
                self.output.write("[yellow]Usage: /search <query>[/yellow]")
            else:
                await self.search_history(args)
        
        elif cmd == "/kb":
            await self.handle_kb_command(args)
        
        elif cmd == "/netcheck":
            await self.handle_netcheck(args)
        
        elif cmd == "/export":
            await self.handle_export(args)
        
        elif cmd == "/exit" or cmd == "/quit":
            self.exit()
        
        else:
            self.output.write(f"[yellow]Unknown command: {cmd}[/yellow]")
            self.output.write("[dim]Type /help for available commands[/dim]")
    
    async def handle_model_command(self, args: str):
        """Handle /model subcommands."""
        if not args:
            # Show loaded models
            loaded = self.agent.get_loaded_models() if self.agent else {}
            self.output.write("\n[bold]Loaded Models:[/bold]")
            self.output.write(f"  Router: {loaded.get('router', 'N/A')}")
            self.output.write(f"  Specialist: {loaded.get('specialist') or '(none)'}\n")
            return
        
        parts = args.split(maxsplit=1)
        subcmd = parts[0].lower()
        subcmd_args = parts[1] if len(parts) > 1 else ""
        
        if subcmd == "list":
            self.list_models()
        elif subcmd == "use":
            self.output.write("[yellow]/model use not yet implemented[/yellow]")
        else:
            self.output.write(f"[yellow]Unknown /model subcommand: {subcmd}[/yellow]")
    
    async def handle_kb_command(self, args: str):
        """Handle /kb knowledge base subcommands."""
        if not args:
            self.output.write("[yellow]Usage: /kb <ingest|search|stats|delete> [args][/yellow]")
            return
        
        parts = args.split(maxsplit=1)
        subcmd = parts[0].lower()
        subcmd_args = parts[1] if len(parts) > 1 else ""
        
        if subcmd == "ingest":
            if not subcmd_args:
                self.output.write("[yellow]Usage: /kb ingest <file_path>[/yellow]")
                return
            await self.kb_ingest(subcmd_args)
        
        elif subcmd == "search":
            if not subcmd_args:
                self.output.write("[yellow]Usage: /kb search <query>[/yellow]")
                return
            await self.kb_search(subcmd_args)
        
        elif subcmd == "stats":
            await self.kb_stats()
        
        elif subcmd == "delete":
            if not subcmd_args:
                self.output.write("[yellow]Usage: /kb delete <doc_id_or_source>[/yellow]")
                return
            await self.kb_delete(subcmd_args)
        
        else:
            self.output.write(f"[yellow]Unknown /kb subcommand: {subcmd}[/yellow]")
    
    async def kb_ingest(self, file_path: str):
        """Ingest document into knowledge base."""
        self.update_status("Ingesting document...", "yellow")
        self.output.write(f"[dim]Ingesting: {file_path}[/dim]")
        
        try:
            # Use agent to call ingest_document tool
            result_json = await self.agent._call_tool_async(
                "ingest_document",
                file_path=file_path
            )
            
            import json
            result = json.loads(result_json)
            
            if "error" in result:
                self.output.write(f"[red]✗ Error: {result['error']}[/red]")
            else:
                self.output.write(f"[green]✓ Successfully ingested document[/green]")
                self.output.write(f"  Chunks created: {result.get('chunks_created', 'N/A')}")
                self.output.write(f"  Document ID: {result.get('doc_id', 'N/A')}")
            
            self.update_status("Ready", "green")
            
        except Exception as e:
            self.output.write(f"[red]✗ Ingestion failed: {e}[/red]")
            self.update_status("Ready", "green")
    
    async def kb_search(self, query: str):
        """Search knowledge base."""
        self.update_status("Searching knowledge base...", "yellow")
        self.output.write(f"[dim]Searching for: {query}[/dim]\n")
        
        try:
            # Use agent to call search_knowledge_base tool
            result_json = await self.agent._call_tool_async(
                "search_knowledge_base",
                query=query,
                top_k=5
            )
            
            import json
            result = json.loads(result_json)
            
            if "error" in result:
                self.output.write(f"[red]✗ Error: {result['error']}[/red]")
            elif result.get("results_count", 0) == 0:
                self.output.write("[yellow]No results found[/yellow]")
            else:
                self.output.write(f"[bold]Found {result['results_count']} results:[/bold]\n")
                
                for item in result["results"]:
                    rank = item.get("rank", "?")
                    text = item.get("text", "")
                    metadata = item.get("metadata", {})
                    source = metadata.get("source", "Unknown")
                    
                    self.output.write(f"[cyan]#{rank}[/cyan] [dim]{source}[/dim]")
                    # Show first 200 chars of text
                    preview = text[:200] + "..." if len(text) > 200 else text
                    self.output.write(f"  {preview}\n")
            
            self.update_status("Ready", "green")
            
        except Exception as e:
            self.output.write(f"[red]✗ Search failed: {e}[/red]")
            self.update_status("Ready", "green")
    
    async def kb_stats(self):
        """Show knowledge base statistics."""
        self.update_status("Loading KB stats...", "yellow")
        
        try:
            # Use agent to call kb_stats tool
            result_json = await self.agent._call_tool_async("kb_stats")
            
            import json
            result = json.loads(result_json)
            
            if result.get("status") == "empty":
                self.output.write("[yellow]Knowledge base is empty[/yellow]")
            elif "error" in result:
                self.output.write(f"[red]✗ Error: {result['error']}[/red]")
            else:
                self.output.write("\n[bold]Knowledge Base Statistics:[/bold]")
                self.output.write(f"  Total chunks: {result.get('total_chunks', 'N/A')}")
                self.output.write(f"  Unique documents: {result.get('unique_documents', 'N/A')}")
                self.output.write(f"  Unique sources: {result.get('unique_sources', 'N/A')}")
                
                if result.get("sources"):
                    self.output.write("\n[bold]Sources:[/bold]")
                    for source in result["sources"]:
                        self.output.write(f"  • {source}")
                
                self.output.write(f"\n[dim]Storage: {result.get('chroma_path', 'N/A')}[/dim]\n")
            
            self.update_status("Ready", "green")
            
        except Exception as e:
            self.output.write(f"[red]✗ Stats query failed: {e}[/red]")
            self.update_status("Ready", "green")
    
    async def kb_delete(self, identifier: str):
        """Delete document from knowledge base."""
        self.update_status("Deleting from KB...", "yellow")
        
        try:
            # Determine if it's a doc_id or source path
            if "/" in identifier or "\\" in identifier:
                # Looks like a path
                result_json = await self.agent._call_tool_async(
                    "kb_delete",
                    source=identifier
                )
            else:
                # Looks like a doc_id
                result_json = await self.agent._call_tool_async(
                    "kb_delete",
                    doc_id=identifier
                )
            
            import json
            result = json.loads(result_json)
            
            if "error" in result:
                self.output.write(f"[red]✗ Error: {result['error']}[/red]")
            elif result.get("status") == "not_found":
                self.output.write(f"[yellow]⚠ {result.get('message', 'Not found')}[/yellow]")
            else:
                self.output.write(f"[green]✓ Deleted {result.get('deleted_chunks', 0)} chunks[/green]")
            
            self.update_status("Ready", "green")
            
        except Exception as e:
            self.output.write(f"[red]✗ Deletion failed: {e}[/red]")
            self.update_status("Ready", "green")
    
    async def handle_netcheck(self, args: str):
        """Handle /netcheck command."""
        from ..network.guard import NetworkGuard
        
        guard = NetworkGuard()
        
        if args and args.startswith("monitor"):
            # Continuous monitoring
            parts = args.split()
            duration = int(parts[1]) if len(parts) > 1 else 10
            
            self.update_status(f"Monitoring network for {duration}s...", "yellow")
            self.output.write(f"[dim]Starting {duration}-second network monitor...[/dim]\n")
            
            try:
                summary = guard.continuous_monitor(duration)
                
                self.output.write("\n[bold]Network Monitoring Summary:[/bold]")
                self.output.write(f"  Duration: {summary['duration']}s")
                self.output.write(f"  Total checks: {summary['total_checks']}")
                self.output.write(f"  Violations: {summary['violations_detected']}")
                
                if summary['is_air_gapped']:
                    self.output.write("\n[green]✓ System is air-gapped (no external connections)[/green]")
                else:
                    self.output.write(f"\n[red]✗ Air-gap violations detected![/red]")
                
                self.update_status("Ready", "green")
                
            except Exception as e:
                self.output.write(f"[red]✗ Monitoring failed: {e}[/red]")
                self.update_status("Ready", "green")
        
        else:
            # Quick check
            self.update_status("Checking network...", "yellow")
            self.output.write("[dim]Performing air-gap verification...[/dim]\n")
            
            try:
                is_air_gapped, violations = guard.check_air_gap()
                ollama_local = guard.verify_ollama_local()
                interfaces = guard.get_network_interfaces()
                
                self.output.write("[bold]Network Status:[/bold]\n")
                
                if is_air_gapped:
                    self.output.write("[green]✓ Air-gapped: No external connections detected[/green]")
                else:
                    self.output.write(f"[red]✗ Air-gap violation: {len(violations)} external connection(s)[/red]\n")
                    for v in violations[:5]:  # Show first 5
                        self.output.write(f"  • {v.get('process', 'Unknown')}: {v.get('remote_addr')}:{v.get('remote_port')}")
                
                if ollama_local:
                    self.output.write("[green]✓ Ollama: Running on localhost[/green]")
                else:
                    self.output.write("[yellow]⚠ Ollama: Not verified as localhost-only[/yellow]")
                
                # Show active interfaces
                self.output.write("\n[bold]Network Interfaces:[/bold]")
                for name, info in interfaces.items():
                    status = "UP" if info.get("is_up") else "DOWN"
                    self.output.write(f"  • {name}: {status}")
                    for addr in info.get("addresses", []):
                        self.output.write(f"    {addr['type']}: {addr['address']}")
                
                self.output.write("")
                self.update_status("Ready", "green")
                
            except Exception as e:
                self.output.write(f"[red]✗ Network check failed: {e}[/red]")
                self.update_status("Ready", "green")
    
    async def handle_export(self, args: str):
        """Handle /export command."""
        if not args:
            self.output.write("[yellow]Usage: /export <session|audit>[/yellow]")
            return
        
        parts = args.split()
        export_type = parts[0].lower()
        
        if export_type == "session":
            # Export current session
            from ..cli.export import SessionExporter
            
            self.update_status("Exporting session...", "yellow")
            
            try:
                exporter = SessionExporter()
                json_path = exporter.export_session_json(self.agent.session_id)
                md_path = exporter.export_session_markdown(self.agent.session_id)
                
                self.output.write("[green]✓ Session exported:[/green]")
                self.output.write(f"  JSON: {json_path}")
                self.output.write(f"  Markdown: {md_path}")
                
                self.update_status("Ready", "green")
                
            except Exception as e:
                self.output.write(f"[red]✗ Export failed: {e}[/red]")
                self.update_status("Ready", "green")
        
        elif export_type == "audit":
            # Export network audit log
            from ..network.guard import NetworkGuard
            
            self.update_status("Exporting audit log...", "yellow")
            
            try:
                guard = NetworkGuard()
                audit_path = guard.export_audit_log()
                
                self.output.write(f"[green]✓ Audit log exported to: {audit_path}[/green]")
                
                self.update_status("Ready", "green")
                
            except Exception as e:
                self.output.write(f"[red]✗ Export failed: {e}[/red]")
                self.update_status("Ready", "green")
        
        else:
            self.output.write(f"[yellow]Unknown export type: {export_type}[/yellow]")
            self.output.write("[dim]Use: /export session or /export audit[/dim]")
    
    def list_models(self):
        """List available models from registry."""
        models = self.registry.list_models()
        
        if not models:
            self.output.write("[yellow]No models registered[/yellow]")
            return
        
        self.output.write("\n[bold]Registered Models:[/bold]\n")
        
        # Group by role
        by_role = {}
        for model in models:
            if model.role not in by_role:
                by_role[model.role] = []
            by_role[model.role].append(model)
        
        for role, role_models in sorted(by_role.items()):
            self.output.write(f"[cyan]{role.upper()}:[/cyan]")
            for model in role_models:
                default = " [green](default)[/green]" if self.registry.role_map.get(role) == model.name else ""
                self.output.write(f"  • {model.name}{default}")
                self.output.write(f"    Model ID: {model.model_id}")
                self.output.write(f"    VRAM: {model.vram_gb_min}GB, Context: {model.num_ctx} tokens")
            self.output.write("")
    
    def show_all_commands(self):
        """Show a quick list of all available commands."""
        commands_text = """
**📋 Available Commands:**

Type any command to use it, or `/help` for detailed information.

**Basic:**
• `/help` — Detailed help
• `/clear` — Clear chat
• `/exit`, `/quit` — Exit app

**Session:**
• `/stats` — Session statistics
• `/search <query>` — Search history

**Models:**
• `/model` — Show loaded models
• `/model list` — List all models
• `/model info <name>` — Model details

**Knowledge Base:**
• `/kb` — KB commands
• `/kb list` — List documents
• `/kb add <category> <file>` — Add document
• `/kb search <query>` — Search KB

**Network & Security:**
• `/netcheck` — Verify air-gap
• `/netcheck monitor <seconds>` — Monitor network
• `/export session` — Export session
• `/export audit` — Export audit log

---
💡 **Tip:** As you type `/`, suggestions will appear automatically!
"""
        self.output.write(Markdown(commands_text))
    
    def show_help(self):
        """Show help message."""
        help_text = """
**Available Commands:**

**Basic:**
- `/help` — Show this help message
- `/clear` — Clear the chat display
- `/exit` or `/quit` — Exit the application

**Session:**
- `/stats` — Show session statistics
- `/search <query>` — Search conversation history

**Models:**
- `/model` — Show currently loaded models
- `/model list` — List all registered models

**Knowledge Base:**
- `/kb ingest <path>` — Ingest document into knowledge base
- `/kb search <query>` — Search knowledge base semantically
- `/kb stats` — Show knowledge base statistics
- `/kb delete <doc_id>` — Delete document from knowledge base

**Network & Security:**
- `/netcheck` — Verify air-gap (no external network connections)
- `/netcheck monitor <seconds>` — Continuous monitoring
- `/export session` — Export current session to JSON/Markdown
- `/export audit` — Export network audit log

**Coming Soon:**

**Phase 2 Features Now Active:**
- Automatic task routing to specialist models
- Dynamic model loading/unloading
- Multi-task orchestration

**Tips:**
- Just type your question naturally
- Router automatically selects the right specialist
- All data stays local — nothing leaves this machine
"""
        self.output.write(Markdown(help_text))
    
    def show_stats(self):
        """Show session statistics."""
        if not self.agent:
            self.output.write("[yellow]Agent not initialized[/yellow]")
            return
        
        stats = self.agent.get_session_stats()
        
        if stats:
            self.output.write("\n[bold]Session Statistics:[/bold]")
            self.output.write(f"  Session ID: {self.agent.session_id}")
            self.output.write(f"  Messages: {stats.get('message_count', 0)}")
            self.output.write(f"  User messages: {stats.get('user_messages', 0)}")
            self.output.write(f"  Assistant messages: {stats.get('assistant_messages', 0)}")
            self.output.write(f"  Total tokens: {stats.get('total_tokens', 0)}")
            self.output.write(f"  Router model: {stats.get('router_model', 'N/A')}\n")
        else:
            self.output.write("[dim]No statistics available[/dim]")
    
    async def search_history(self, query: str):
        """Search conversation history."""
        if not self.agent:
            self.output.write("[yellow]Agent not initialized[/yellow]")
            return
        
        self.output.write(f"[dim]Searching for: '{query}'...[/dim]")
        
        results = self.agent.search_history(query)
        
        if results:
            self.output.write(f"\n[bold]Found {len(results)} results:[/bold]")
            for i, result in enumerate(results, 1):
                role = result['role']
                snippet = result['snippet']
                self.output.write(f"\n{i}. [{role}] {snippet}")
        else:
            self.output.write("[dim]No results found[/dim]")
    
    async def handle_chat(self, user_input: str):
        """Handle chat interaction with streaming status and thinking timer."""
        self.update_status("💭 Thinking...", "yellow")
        
        # Start thinking timer
        self.progress_tracker.start_thinking()
        thinking_line = None
        
        try:
            # Use streaming with status updates
            response_started = False
            full_response = ""
            
            async for chunk in self.agent.chat_stream(user_input):
                chunk_type = chunk.get("type")
                
                if chunk_type == "status":
                    # Show status update with elapsed time
                    elapsed = self.progress_tracker.get_elapsed_time()
                    status_msg = chunk['message']
                    self.output.write(f"[dim]→ {status_msg} ({elapsed})[/dim]")
                    self.update_status(f"💭 {status_msg} ({elapsed})", "yellow")
                
                elif chunk_type == "classification":
                    # Show task breakdown
                    tasks = chunk.get("tasks", [])
                    elapsed = self.progress_tracker.get_elapsed_time()
                    self.output.write(f"[dim]→ Tasks: {', '.join(tasks)} ({elapsed})[/dim]")
                
                elif chunk_type == "model_loaded":
                    # Show which model is being used
                    elapsed = self.progress_tracker.get_elapsed_time()
                    self.output.write(f"[dim]→ Using: {chunk['message']} ({elapsed})[/dim]")
                
                elif chunk_type == "subtask_complete":
                    # Show progress
                    elapsed = self.progress_tracker.get_elapsed_time()
                    self.output.write(f"[dim]→ {chunk['message']} ({elapsed})[/dim]")
                
                elif chunk_type == "response":
                    # Final response - stop thinking timer
                    total_elapsed = self.progress_tracker.stop_thinking()
                    
                    if not response_started:
                        self.output.write(f"\n[bold green]Assistant:[/bold green] [dim](completed in {total_elapsed})[/dim]")
                        response_started = True
                    
                    content = chunk.get("content", "")
                    self.output.write(content)
                    full_response = content
                
                elif chunk_type == "error":
                    self.progress_tracker.stop_thinking()
                    self.output.write(f"\n[red]✗ Error: {chunk['message']}[/red]")
                    return
            
            # Update status bar
            session_id = self.agent.session_id[:8]
            loaded = self.agent.get_loaded_models()
            self.update_status(
                f"Ready | Session: {session_id} | Router: {loaded['router']}" +
                (f" | Active: {loaded['specialist']}" if loaded['specialist'] else ""),
                "green"
            )
        
        except Exception as e:
            self.progress_tracker.stop_thinking()
            self.output.write(f"\n[red]✗ Error: {e}[/red]")
            self.update_status(f"Error: {e}", "red")
            logger.error(f"Chat error: {e}", exc_info=True)
    
    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
    
    def action_clear(self) -> None:
        """Clear the output."""
        self.output.clear()
        self.output.write(Text("Chat cleared", style="dim"))


def main():
    """Main entry point."""
    app = SentinelCLI()
    app.run()


if __name__ == "__main__":
    main()
