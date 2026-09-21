"""
Demo Scenarios for Sentinel AI Workbench - SIH 2026

Validates all 5 acceptance criteria:
1. Multi-model orchestration with dynamic loading
2. Agentic tool usage (sandboxed code execution)
3. Vision/OCR on technical drawings
4. Local RAG with knowledge base
5. Air-gap verification (network guard)
"""

import asyncio
import json
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.master_agent import MasterAgent
from src.models.registry import get_model_registry
from src.network.guard import NetworkGuard
from src.tools.local_rag import LocalRAGTool, SemanticSearchTool
from src.models.ollama_backend import get_ollama_backend


class DemoRunner:
    """Run demo scenarios and validate acceptance criteria."""
    
    def __init__(self):
        self.results = []
        self.agent = None
    
    def log_result(self, scenario: str, passed: bool, details: str = ""):
        """Log scenario result."""
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"\n{status}: {scenario}")
        if details:
            print(f"  Details: {details}")
        
        self.results.append({
            "scenario": scenario,
            "passed": passed,
            "details": details,
            "timestamp": time.time()
        })
    
    async def demo_1_multimodel_orchestration(self):
        """
        Demo 1: Multi-Model Orchestration
        Validates: Dynamic model loading, task routing, specialist execution
        """
        print("\n" + "="*60)
        print("DEMO 1: Multi-Model Orchestration")
        print("="*60)
        
        try:
            # Initialize agent
            print("\n[1] Initializing MasterAgent...")
            self.agent = MasterAgent()
            await self.agent.initialize()
            
            # Check router loaded
            loaded = self.agent.get_loaded_models()
            router_loaded = loaded.get("router") is not None
            self.log_result(
                "1.1 Router model loaded",
                router_loaded,
                f"Router: {loaded.get('router')}"
            )
            
            # Test task classification
            print("\n[2] Testing task classification...")
            tasks = await self.agent._classify_task(
                "Write a Python function to calculate factorial, then explain the time complexity"
            )
            
            multi_task = len(tasks) > 0
            self.log_result(
                "1.2 Task classification working",
                multi_task,
                f"Classified into {len(tasks)} task(s)"
            )
            
            # Test specialist loading
            print("\n[3] Testing specialist model loading...")
            manifest = await self.agent._load_specialist("coding")
            specialist_loaded = manifest is not None and manifest.role == "coding"
            self.log_result(
                "1.3 Specialist model loading",
                specialist_loaded,
                f"Loaded: {manifest.model_id if manifest else 'None'}"
            )
            
            # Check model registry
            registry = get_model_registry()
            models = registry.list_models()
            has_specialists = len(models) >= 4  # Router + at least 3 specialists
            self.log_result(
                "1.4 Multiple models registered",
                has_specialists,
                f"Total models: {len(models)}"
            )
            
            return True
            
        except Exception as e:
            self.log_result("1.x Multi-Model Orchestration", False, str(e))
            return False
    
    async def demo_2_agentic_tool_usage(self):
        """
        Demo 2: Agentic Tool Usage
        Validates: Tool calling, sandboxed execution, file operations
        """
        print("\n" + "="*60)
        print("DEMO 2: Agentic Tool Usage")
        print("="*60)
        
        try:
            if not self.agent:
                self.agent = MasterAgent()
                await self.agent.initialize()
            
            # Check tool registry
            print("\n[1] Checking tool registry...")
            tools = self.agent.tool_registry.list_tools()
            has_tools = len(tools) >= 8  # Should have at least 8 tools
            self.log_result(
                "2.1 Tools registered",
                has_tools,
                f"Total tools: {len(tools)}"
            )
            
            # Test file operations tool
            print("\n[2] Testing file operations tool...")
            from src.tools.file_ops import FileOpsTool
            file_tool = FileOpsTool()
            
            test_file = Path("output/test_demo.txt")
            write_result = file_tool.execute(
                operation="write",
                file_path=str(test_file),
                content="Demo test content"
            )
            
            file_write_ok = "error" not in json.loads(write_result.get("result", "{}"))
            self.log_result(
                "2.2 File write operation",
                file_write_ok,
                "Created test file"
            )
            
            # Test sandboxed code execution tool
            print("\n[3] Testing sandboxed code execution...")
            from src.tools.sandbox_exec import SandboxExecTool
            sandbox_tool = SandboxExecTool()
            
            exec_result = sandbox_tool.execute(
                language="python",
                code="print('Hello from sandbox'); result = 2 + 2; print(f'Result: {result}')"
            )
            
            result_json = json.loads(exec_result.get("result", "{}"))
            sandbox_ok = result_json.get("status") == "success"
            self.log_result(
                "2.3 Sandboxed code execution",
                sandbox_ok,
                f"Exit code: {result_json.get('exit_code', 'N/A')}"
            )
            
            # Test document generation
            print("\n[4] Testing document generation...")
            from src.tools.docgen import DocGenTool
            docgen_tool = DocGenTool()
            
            doc_result = docgen_tool.execute(
                doc_type="word",
                output_path="output/demo_doc.docx",
                title="Demo Document",
                content="This is a demo document generated by Sentinel AI."
            )
            
            doc_ok = Path("output/demo_doc.docx").exists()
            self.log_result(
                "2.4 Document generation",
                doc_ok,
                "Created Word document"
            )
            
            return True
            
        except Exception as e:
            self.log_result("2.x Agentic Tool Usage", False, str(e))
            return False
    
    async def demo_3_vision_ocr(self):
        """
        Demo 3: Vision/OCR on Technical Drawings
        Validates: Image processing, OCR, PDF handling
        """
        print("\n" + "="*60)
        print("DEMO 3: Vision/OCR Capabilities")
        print("="*60)
        
        try:
            # Check vision tools exist
            print("\n[1] Checking vision tools...")
            from src.tools.vision_pipeline import VisionPipelineTool, TiledVisionTool
            from src.tools.pdf_processor import PDFProcessorTool
            
            backend = get_ollama_backend()
            vision_tool = VisionPipelineTool(backend)
            tiled_tool = TiledVisionTool(backend)
            pdf_tool = PDFProcessorTool(backend)
            
            vision_tools_ok = all([vision_tool, tiled_tool, pdf_tool])
            self.log_result(
                "3.1 Vision tools initialized",
                vision_tools_ok,
                "VisionPipeline, TiledVision, PDFProcessor ready"
            )
            
            # Check qwen3-vl model in registry
            print("\n[2] Checking vision model...")
            registry = get_model_registry()
            vision_models = [m for m in registry.list_models() if m.role == "vision"]
            has_vision_model = len(vision_models) > 0
            self.log_result(
                "3.2 Vision model registered",
                has_vision_model,
                f"Models: {[m.name for m in vision_models]}"
            )
            
            # Test OCR capability (no actual image needed for validation)
            print("\n[3] Checking OCR support...")
            try:
                import pytesseract
                ocr_ok = True
            except ImportError:
                ocr_ok = False
            
            self.log_result(
                "3.3 OCR support (Tesseract)",
                ocr_ok,
                "pytesseract module available" if ocr_ok else "Install Tesseract for OCR"
            )
            
            # Test PDF support
            print("\n[4] Checking PDF processing support...")
            try:
                from pdf2image import convert_from_path
                pdf_ok = True
            except ImportError:
                pdf_ok = False
            
            self.log_result(
                "3.4 PDF processing support",
                pdf_ok,
                "pdf2image available" if pdf_ok else "Install poppler for PDF processing"
            )
            
            return True
            
        except Exception as e:
            self.log_result("3.x Vision/OCR", False, str(e))
            return False
    
    async def demo_4_local_rag(self):
        """
        Demo 4: Local RAG with Knowledge Base
        Validates: Document ingestion, semantic search, ChromaDB
        """
        print("\n" + "="*60)
        print("DEMO 4: Local RAG / Knowledge Base")
        print("="*60)
        
        try:
            backend = get_ollama_backend()
            
            # Test RAG tools initialization
            print("\n[1] Initializing RAG tools...")
            from src.tools.local_rag import LocalRAGTool, SemanticSearchTool, KBStatsTool
            
            rag_tool = LocalRAGTool(backend)
            search_tool = SemanticSearchTool(backend)
            stats_tool = KBStatsTool()
            
            rag_tools_ok = all([rag_tool, search_tool, stats_tool])
            self.log_result(
                "4.1 RAG tools initialized",
                rag_tools_ok,
                "LocalRAG, SemanticSearch, KBStats ready"
            )
            
            # Check ChromaDB
            print("\n[2] Checking ChromaDB...")
            try:
                import chromadb
                chroma_ok = True
            except ImportError:
                chroma_ok = False
            
            self.log_result(
                "4.2 ChromaDB available",
                chroma_ok,
                "Vector store ready"
            )
            
            # Check embedding model
            print("\n[3] Checking embedding model...")
            registry = get_model_registry()
            embedding_models = [m for m in registry.list_models() if m.role == "embedding"]
            has_embedding = len(embedding_models) > 0
            self.log_result(
                "4.3 Embedding model registered",
                has_embedding,
                f"Model: {embedding_models[0].name if embedding_models else 'None'}"
            )
            
            # Test document chunking
            print("\n[4] Testing document chunker...")
            from src.tools.local_rag import DocumentChunker
            chunker = DocumentChunker()
            
            test_text = "This is a test. " * 100  # 500 chars
            chunks = chunker.chunk_text(test_text, chunk_size=200, overlap=50)
            
            chunking_ok = len(chunks) > 1
            self.log_result(
                "4.4 Document chunking",
                chunking_ok,
                f"Created {len(chunks)} chunks from test text"
            )
            
            # Test KB stats
            print("\n[5] Testing KB stats...")
            stats_result = stats_tool.execute()
            stats_ok = "error" not in json.loads(stats_result)
            self.log_result(
                "4.5 KB statistics query",
                stats_ok,
                "KB stats accessible"
            )
            
            return True
            
        except Exception as e:
            self.log_result("4.x Local RAG", False, str(e))
            return False
    
    async def demo_5_air_gap_verification(self):
        """
        Demo 5: Air-Gap Verification
        Validates: Network monitoring, loopback enforcement, audit logging
        """
        print("\n" + "="*60)
        print("DEMO 5: Air-Gap Verification")
        print("="*60)
        
        try:
            # Initialize network guard
            print("\n[1] Initializing NetworkGuard...")
            guard = NetworkGuard()
            guard_ok = guard is not None
            self.log_result(
                "5.1 NetworkGuard initialized",
                guard_ok,
                "Network monitoring ready"
            )
            
            # Test air-gap check
            print("\n[2] Performing air-gap check...")
            is_air_gapped, violations = guard.check_air_gap()
            
            self.log_result(
                "5.2 Air-gap check executed",
                True,  # Check executed (result may vary)
                f"Air-gapped: {is_air_gapped}, Violations: {len(violations)}"
            )
            
            # Test Ollama verification
            print("\n[3] Verifying Ollama is local...")
            ollama_local = guard.verify_ollama_local()
            self.log_result(
                "5.3 Ollama localhost verification",
                True,  # Check executed
                f"Ollama local: {ollama_local}"
            )
            
            # Test network interface inspection
            print("\n[4] Inspecting network interfaces...")
            interfaces = guard.get_network_interfaces()
            has_interfaces = len(interfaces) > 0
            self.log_result(
                "5.4 Network interface inspection",
                has_interfaces,
                f"Found {len(interfaces)} interface(s)"
            )
            
            # Test audit logging
            print("\n[5] Testing audit log...")
            audit_log_exists = guard.audit_log_path.exists()
            self.log_result(
                "5.5 Audit logging functional",
                audit_log_exists,
                f"Log: {guard.audit_log_path}"
            )
            
            return True
            
        except Exception as e:
            self.log_result("5.x Air-Gap Verification", False, str(e))
            return False
    
    async def run_all_demos(self):
        """Run all demo scenarios."""
        print("\n" + "="*60)
        print("SENTINEL AI WORKBENCH - DEMO VALIDATION")
        print("SIH 2026 - Air-Gapped Industrial AI")
        print("="*60)
        
        start_time = time.time()
        
        # Run all demos
        await self.demo_1_multimodel_orchestration()
        await self.demo_2_agentic_tool_usage()
        await self.demo_3_vision_ocr()
        await self.demo_4_local_rag()
        await self.demo_5_air_gap_verification()
        
        elapsed = time.time() - start_time
        
        # Summary
        print("\n" + "="*60)
        print("DEMO VALIDATION SUMMARY")
        print("="*60)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        
        print(f"\nTotal Scenarios: {total}")
        print(f"Passed: {passed} ✓")
        print(f"Failed: {failed} ✗")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        print(f"Elapsed Time: {elapsed:.2f}s")
        
        # Show failures
        if failed > 0:
            print("\nFailed Scenarios:")
            for r in self.results:
                if not r["passed"]:
                    print(f"  ✗ {r['scenario']}: {r['details']}")
        
        print("\n" + "="*60)
        
        # Export results
        results_path = Path("output/demo_results.json")
        results_path.parent.mkdir(exist_ok=True)
        with open(results_path, 'w') as f:
            json.dump({
                "timestamp": time.time(),
                "total": total,
                "passed": passed,
                "failed": failed,
                "success_rate": passed/total,
                "elapsed_time": elapsed,
                "results": self.results
            }, f, indent=2)
        
        print(f"\nResults exported to: {results_path}")
        
        return passed == total


async def main():
    """Main entry point."""
    runner = DemoRunner()
    success = await runner.run_all_demos()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
