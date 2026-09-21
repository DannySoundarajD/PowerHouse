"""
Live System Test with Actual Ollama Models

Tests the complete Sentinel AI system with locally available models.
Run this to verify end-to-end functionality.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.ollama_backend import OllamaBackend, get_ollama_backend
from src.models.registry import ModelRegistry
from src.models.manifest import ModelManifest
from src.agent.simple_agent import SimpleAgent
from src.agent.master_agent import MasterAgent
from src.tools import register_default_tools
from src.utils.session_state import SessionState

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LiveSystemTester:
    """Test harness for live system validation."""
    
    def __init__(self):
        self.backend = get_ollama_backend()
        self.registry = ModelRegistry()
        self.session = SessionState(Path(":memory:"))  # Pass as Path object
        self.results = {
            "tests_passed": 0,
            "tests_failed": 0,
            "test_results": []
        }
    
    def log_result(self, test_name: str, passed: bool, message: str = ""):
        """Log a test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status} - {test_name}: {message}")
        
        self.results["test_results"].append({
            "test": test_name,
            "passed": passed,
            "message": message
        })
        
        if passed:
            self.results["tests_passed"] += 1
        else:
            self.results["tests_failed"] += 1
    
    async def test_1_ollama_connection(self):
        """Test 1: Verify Ollama is running and accessible."""
        logger.info("\n" + "="*60)
        logger.info("TEST 1: Ollama Connection")
        logger.info("="*60)
        
        try:
            # Try to list models
            result = await self.backend._call_ollama_api("/api/tags", method="GET")
            models = result.get("models", [])
            
            if models:
                self.log_result(
                    "Ollama Connection",
                    True,
                    f"Connected successfully. Found {len(models)} models"
                )
                
                # Print available models
                logger.info("\nAvailable Models:")
                for model in models[:10]:  # Show first 10
                    name = model.get("name", "unknown")
                    size = model.get("size", 0) / (1024**3)  # Convert to GB
                    logger.info(f"  - {name} ({size:.1f} GB)")
                
                return True
            else:
                self.log_result("Ollama Connection", False, "No models found")
                return False
                
        except Exception as e:
            self.log_result("Ollama Connection", False, f"Error: {e}")
            return False
    
    async def test_2_model_loading(self):
        """Test 2: Load and test a simple model."""
        logger.info("\n" + "="*60)
        logger.info("TEST 2: Model Loading")
        logger.info("="*60)
        
        # Try qwen3.5:2b (router model)
        test_model = "qwen3.5:2b"
        
        try:
            logger.info(f"Testing model: {test_model}")
            
            response = await self.backend.chat(
                model=test_model,
                messages=[{"role": "user", "content": "Say 'test successful' if you can read this."}],
                stream=False
            )
            
            # Extract content from response
            if hasattr(response, 'message'):
                content = response.message.content
            elif isinstance(response, dict):
                content = response.get("message", {}).get("content", "")
            else:
                content = str(response)
            
            if content and len(content) > 0:
                self.log_result(
                    "Model Loading",
                    True,
                    f"Model {test_model} responded: {content[:100]}"
                )
                return True
            else:
                self.log_result("Model Loading", False, "Empty response")
                return False
                
        except Exception as e:
            self.log_result("Model Loading", False, f"Error: {e}")
            return False
    
    async def test_3_simple_agent(self):
        """Test 3: Simple agent with single model."""
        logger.info("\n" + "="*60)
        logger.info("TEST 3: Simple Agent")
        logger.info("="*60)
        
        try:
            # Use available model - SimpleAgent constructor changed
            agent = SimpleAgent(
                model_id="qwen3.5:2b",
                session_id="test_session"
            )
            
            await agent.initialize()
            
            query = "What is 2+2? Answer with just the number."
            logger.info(f"Query: {query}")
            
            response = await agent.chat(query)
            
            if response and ("4" in response or "four" in response.lower()):
                self.log_result(
                    "Simple Agent",
                    True,
                    f"Agent responded correctly: {response[:100]}"
                )
                return True
            else:
                self.log_result(
                    "Simple Agent",
                    False,
                    f"Unexpected response: {response[:100] if response else 'None'}"
                )
                return False
                
        except Exception as e:
            self.log_result("Simple Agent", False, f"Error: {e}")
            return False
    
    async def test_4_embeddings(self):
        """Test 4: Embedding generation."""
        logger.info("\n" + "="*60)
        logger.info("TEST 4: Embeddings")
        logger.info("="*60)
        
        try:
            test_text = "This is a test sentence for embedding generation."
            
            embedding = await self.backend.embed(
                model="nomic-embed-text",
                input=test_text
            )
            
            if embedding and len(embedding) > 0:
                self.log_result(
                    "Embeddings",
                    True,
                    f"Generated {len(embedding)}-dimensional embedding"
                )
                return True
            else:
                self.log_result("Embeddings", False, "Empty embedding")
                return False
                
        except Exception as e:
            self.log_result("Embeddings", False, f"Error: {e}")
            return False
    
    async def test_5_tool_registration(self):
        """Test 5: Tool registry."""
        logger.info("\n" + "="*60)
        logger.info("TEST 5: Tool Registration")
        logger.info("="*60)
        
        try:
            registry = register_default_tools()
            tools = registry.list_tools()
            
            if len(tools) >= 16:  # Should have all 16 tools
                self.log_result(
                    "Tool Registration",
                    True,
                    f"Registered {len(tools)} tools"
                )
                
                # List tools by category
                logger.info("\nRegistered Tools:")
                for tool in tools:
                    logger.info(f"  - {tool}")
                
                return True
            else:
                self.log_result(
                    "Tool Registration",
                    False,
                    f"Only {len(tools)} tools registered, expected 16+"
                )
                return False
                
        except Exception as e:
            self.log_result("Tool Registration", False, f"Error: {e}")
            return False
    
    async def test_6_model_registry(self):
        """Test 6: Model registry and manifest loading."""
        logger.info("\n" + "="*60)
        logger.info("TEST 6: Model Registry")
        logger.info("="*60)
        
        try:
            # Scan for model manifests
            manifest_dir = Path("models")
            if not manifest_dir.exists():
                self.log_result("Model Registry", False, "models/ directory not found")
                return False
            
            manifests = list(manifest_dir.glob("*.yaml"))
            
            if len(manifests) >= 5:
                self.log_result(
                    "Model Registry",
                    True,
                    f"Found {len(manifests)} model manifests"
                )
                
                logger.info("\nModel Manifests:")
                for manifest_file in manifests:
                    logger.info(f"  - {manifest_file.name}")
                
                return True
            else:
                self.log_result(
                    "Model Registry",
                    False,
                    f"Only {len(manifests)} manifests found, expected 5+"
                )
                return False
                
        except Exception as e:
            self.log_result("Model Registry", False, f"Error: {e}")
            return False
    
    async def test_7_session_state(self):
        """Test 7: Session state persistence."""
        logger.info("\n" + "="*60)
        logger.info("TEST 7: Session State")
        logger.info("="*60)
        
        try:
            # Create test session
            session_id = self.session.create_session()
            
            # Add test messages
            self.session.add_message(
                session_id=session_id,
                role="user",
                content="Test message 1"
            )
            self.session.add_message(
                session_id=session_id,
                role="assistant",
                content="Test response 1"
            )
            
            # Retrieve history
            history = self.session.get_context_window(session_id)
            
            if len(history) >= 2:
                self.log_result(
                    "Session State",
                    True,
                    f"Session stored {len(history)} messages"
                )
                return True
            else:
                self.log_result("Session State", False, "Failed to store messages")
                return False
                
        except Exception as e:
            self.log_result("Session State", False, f"Error: {e}")
            return False
    
    async def test_8_coding_model(self):
        """Test 8: Coding specialist model."""
        logger.info("\n" + "="*60)
        logger.info("TEST 8: Coding Model (qwen2.5-coder:7b)")
        logger.info("="*60)
        
        # Check if qwen2.5-coder:7b is available
        coding_model = "qwen2.5-coder:7b"
        
        try:
            logger.info(f"Testing coding model: {coding_model}")
            
            response = await self.backend.chat(
                model=coding_model,
                messages=[{
                    "role": "user",
                    "content": "Write a Python function to calculate factorial. Just the code, no explanation."
                }],
                stream=False
            )
            
            # Extract content from response
            if hasattr(response, 'message'):
                content = response.message.content
            elif isinstance(response, dict):
                content = response.get("message", {}).get("content", "")
            else:
                content = str(response)
            
            if content and ("def" in content or "factorial" in content):
                self.log_result(
                    "Coding Model",
                    True,
                    f"Model generated code: {content[:150]}..."
                )
                return True
            else:
                self.log_result("Coding Model", False, "No code generated")
                return False
                
        except Exception as e:
            self.log_result("Coding Model", False, f"Error: {e}")
            return False
    
    async def test_9_general_reasoning(self):
        """Test 9: General reasoning model."""
        logger.info("\n" + "="*60)
        logger.info("TEST 9: General Reasoning (qwen2.5:7b)")
        logger.info("="*60)
        
        reasoning_model = "qwen2.5:7b"
        
        try:
            logger.info(f"Testing reasoning model: {reasoning_model}")
            
            response = await self.backend.chat(
                model=reasoning_model,
                messages=[{
                    "role": "user",
                    "content": "If a train travels 60 km in 30 minutes, what is its speed in km/h?"
                }],
                stream=False
            )
            
            # Extract content from response
            if hasattr(response, 'message'):
                content = response.message.content
            elif isinstance(response, dict):
                content = response.get("message", {}).get("content", "")
            else:
                content = str(response)
            
            if content and ("120" in content):
                self.log_result(
                    "General Reasoning",
                    True,
                    f"Model reasoned correctly: {content[:150]}..."
                )
                return True
            else:
                self.log_result(
                    "General Reasoning",
                    False,
                    f"Incorrect or unclear response: {content[:150] if content else 'None'}"
                )
                return False
                
        except Exception as e:
            self.log_result("General Reasoning", False, f"Error: {e}")
            return False
    
    async def test_10_directory_structure(self):
        """Test 10: Verify project directory structure."""
        logger.info("\n" + "="*60)
        logger.info("TEST 10: Directory Structure")
        logger.info("="*60)
        
        required_dirs = [
            "src", "src/agent", "src/cli", "src/models", "src/tools",
            "src/network", "src/utils", "tests", "scripts", "models",
            "docker", "kb", "data", "logs", "output"
        ]
        
        missing = []
        for dir_path in required_dirs:
            if not Path(dir_path).exists():
                missing.append(dir_path)
        
        if not missing:
            self.log_result(
                "Directory Structure",
                True,
                "All required directories exist"
            )
            return True
        else:
            self.log_result(
                "Directory Structure",
                False,
                f"Missing directories: {', '.join(missing)}"
            )
            return False
    
    async def run_all_tests(self):
        """Run all tests in sequence."""
        logger.info("\n" + "="*60)
        logger.info("🧪 SENTINEL AI WORKBENCH - LIVE SYSTEM TEST")
        logger.info("="*60)
        logger.info("Testing with locally available Ollama models")
        logger.info("")
        
        # Run tests
        await self.test_1_ollama_connection()
        await self.test_2_model_loading()
        await self.test_3_simple_agent()
        await self.test_4_embeddings()
        await self.test_5_tool_registration()
        await self.test_6_model_registry()
        await self.test_7_session_state()
        await self.test_8_coding_model()
        await self.test_9_general_reasoning()
        await self.test_10_directory_structure()
        
        # Print summary
        self.print_summary()
        
        return self.results["tests_failed"] == 0
    
    def print_summary(self):
        """Print test summary."""
        logger.info("\n" + "="*60)
        logger.info("TEST SUMMARY")
        logger.info("="*60)
        
        total = self.results["tests_passed"] + self.results["tests_failed"]
        pass_rate = (self.results["tests_passed"] / total * 100) if total > 0 else 0
        
        logger.info(f"Total Tests: {total}")
        logger.info(f"Passed: {self.results['tests_passed']} ✅")
        logger.info(f"Failed: {self.results['tests_failed']} ❌")
        logger.info(f"Pass Rate: {pass_rate:.1f}%")
        
        if self.results["tests_failed"] == 0:
            logger.info("\n🎉 ALL TESTS PASSED! System is operational.")
        else:
            logger.info("\n⚠️ Some tests failed. Review logs above.")
        
        # Save results to file
        results_file = Path("output/test_results.json")
        results_file.parent.mkdir(parents=True, exist_ok=True)
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"\nDetailed results saved to: {results_file}")


async def main():
    """Main test runner."""
    tester = LiveSystemTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
