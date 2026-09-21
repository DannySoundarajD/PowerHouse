# Sentinel AI Workbench — Quick Start Guide

## Phase 1 Status: Core Orchestrator + Router + CLI ✅

This guide will get you running with Sentinel in under 10 minutes.

---

## Prerequisites

Before starting, ensure you have:

1. **Windows 10/11** (64-bit)
2. **Python 3.11+** installed
3. **Ollama** installed and running
4. **Docker Desktop** installed (for sandbox features in later phases)
5. **4GB+ GPU RAM** (NVIDIA RTX 2050 or better)

---

## Installation Steps

### 1. Verify Hardware

```powershell
# Clone the repository (or navigate to project directory)
cd "D:\SIH2026\PS1\New folder"

# Run hardware detection
python scripts/detect_hardware.py
```

**Expected output:**
```
✓ GPU: NVIDIA GeForce RTX 2050
✓ VRAM: 4.0 GB
✓ Total RAM: 15.2 GB
✓ Ollama installed
✓ Docker installed
```

If any checks fail, install the missing components before continuing.

### 2. Install Dependencies

```powershell
# Create virtual environment (recommended)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```powershell
# Copy example environment file
copy .env.example .env

# Edit .env if needed (defaults should work)
notepad .env
```

**Key settings:**
- `OLLAMA_HOST=http://127.0.0.1:11434` ← Ensure Ollama is at this address
- `OLLAMA_MAX_LOADED_MODELS=2` ← Router + one specialist
- `SENTINEL_ROUTER_MODEL=qwen3.5:2b` ← Default router model

### 4. Start Ollama

```powershell
# Check if Ollama is running
ollama list

# If not running, start it (usually auto-starts after installation)
# Open Ollama Desktop app or run:
ollama serve
```

### 5. Pull Models

**Option A: Automated (Recommended)**

```powershell
python scripts/pull_models.py
```

This will download ~12GB of models (15-20 minutes depending on internet speed):
- qwen3.5:2b (router, 2.7GB)
- qwen2.5-coder:3b (coding, 1.9GB)
- deepseek-r1:7b (reasoning, 4.7GB)
- qwen3-vl:4b (vision, 3.3GB)
- nomic-embed-text (embeddings, 0.3GB)

**Option B: Manual**

```powershell
ollama pull qwen3.5:2b
ollama pull qwen2.5-coder:3b
ollama pull deepseek-r1:7b
ollama pull qwen3-vl:4b
ollama pull nomic-embed-text
```

### 6. Launch Sentinel

```powershell
python -m src.cli.app
```

---

## First Steps in Sentinel

Once launched, you'll see:

```
Sentinel AI Workbench v1.0
Sovereign On-Premise AI — Air-Gapped & Secure
Type /help for commands

Session ID: abc12345

>
```

### Try These Commands:

**1. Basic chat:**
```
> Hello, introduce yourself
```

**2. Simple calculation:**
```
> Calculate the compound interest for $10,000 at 5% annually for 3 years
```

**3. Show statistics:**
```
> /stats
```

**4. Search history:**
```
> /search interest
```

**5. Get help:**
```
> /help
```

---

## What's Working (Phase 1)

✅ **Core Features:**
- Single router model (qwen3.5:2b) handles all requests
- SQLite-backed session persistence with FTS5 search
- Textual TUI with streaming responses
- Conversation history with context management
- Basic slash commands (/help, /stats, /search, /clear)

✅ **Session Management:**
- Automatic session creation
- Full conversation history
- Full-text search across all messages
- Token usage tracking

✅ **Status Bar:**
- Shows current session ID
- Active model indicator
- Real-time status updates

---

## What's Coming Next

🚧 **Phase 2: Model Registry** (Next)
- Dynamic model loading/unloading
- Task-based routing (coding → coder model, etc.)
- Specialist model support

🚧 **Phase 3: Tool Layer**
- Sandboxed code execution (Docker)
- File operations
- Document generation (Word/Excel/PowerPoint)
- Spreadsheet read/write

🚧 **Phase 4: Vision/OCR**
- Full-resolution image processing
- PDF document extraction
- Technical drawing analysis

🚧 **Phase 5: RAG/Knowledge Base**
- Local vector database (ChromaDB)
- Document ingestion
- Retrieval-augmented generation

---

## Troubleshooting

### Ollama not responding

**Symptom:** `Agent initialization failed: Ollama backend not accessible`

**Fix:**
1. Check if Ollama is running: `ollama list`
2. Try accessing: http://127.0.0.1:11434 in browser
3. Restart Ollama service
4. Check firewall isn't blocking localhost connections

### Model not found

**Symptom:** `Model qwen3.5:2b not found locally`

**Fix:**
```powershell
ollama pull qwen3.5:2b
```

### Out of memory errors

**Symptom:** Ollama crashes or model fails to load

**Fix:**
1. Close other GPU-intensive applications
2. Use smaller router model: `qwen3.5:2b` instead of `qwen3.5:4b`
3. Restart Ollama to clear memory

### Database locked

**Symptom:** `database is locked` error

**Fix:**
- Close any other Sentinel instances
- Delete `data/sessions.db-shm` and `data/sessions.db-wal` if they exist
- Restart application

---

## Testing

Run unit tests to verify installation:

```powershell
# Install dev dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/ -v
```

**Expected:**
```
test_session_state.py::test_create_session PASSED
test_session_state.py::test_add_message PASSED
test_session_state.py::test_context_window PASSED
test_session_state.py::test_fts_search PASSED
test_session_state.py::test_session_stats PASSED
test_session_state.py::test_list_sessions PASSED
```

---

## Performance Benchmarks (RTX 2050 4GB)

| Operation | Time | Notes |
|-----------|------|-------|
| Model load (qwen3.5:2b) | ~3s | First time per session |
| Simple query | ~2-5s | "Hello, how are you?" |
| Complex reasoning | ~10-30s | Multi-step calculations |
| Streaming first token | ~1-2s | Faster perceived response |

---

## Next Steps

Once you're comfortable with basic chat:

1. **Explore session management:**
   - Try `/stats` after a few messages
   - Use `/search <keyword>` to find past conversations

2. **Test context retention:**
   - Ask follow-up questions
   - Reference previous messages
   - Check if context is maintained

3. **Monitor resources:**
   - Watch Task Manager → GPU usage
   - Check `data/sessions.db` size growth
   - Review `logs/sentinel-<date>.log`

4. **Prepare for Phase 2:**
   - Pull additional models if you have 8GB+ VRAM
   - Read `design.md` for architecture details
   - Check `tasks.md` for upcoming features

---

## Useful Commands

```powershell
# Check Ollama models
ollama list

# Check running models
ollama ps

# View Sentinel logs
Get-Content logs\sentinel-*.log -Tail 50

# Check database size
Get-Item data\sessions.db | Select-Object Name, Length

# Clear old sessions (manual cleanup)
# Just delete data/sessions.db to start fresh
```

---

## Getting Help

- **Documentation:** See `docs/` folder
- **Architecture:** `design.md`
- **Tasks:** `tasks.md` for development roadmap
- **Issues:** Check logs in `logs/` directory

---

**Ready to build the future of sovereign AI!** 🚀
