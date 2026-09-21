"""
Simple Web Interface for Sentinel AI Workbench Testing

Provides a web UI for Playwright testing of all system components.
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from pathlib import Path
import asyncio
import sys
import json
from functools import wraps

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.models.ollama_backend import get_ollama_backend
from src.agent.simple_agent import SimpleAgent
from src.tools import register_default_tools

app = Flask(__name__)
backend = get_ollama_backend()

# Test results storage
test_results = {
    "tests_run": 0,
    "tests_passed": 0,
    "tests_failed": 0,
    "results": []
}

def async_route(f):
    """Decorator to handle async routes in Flask."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return wrapped

@app.route('/')
def index():
    """Main test interface."""
    return render_template('index.html')

@app.route('/api/health')
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "system": "Sentinel AI Workbench",
        "version": "1.0.0"
    })

@app.route('/api/test/ollama')
@async_route
async def test_ollama():
    """Test Ollama connection."""
    try:
        is_healthy = await backend.health_check()
        return jsonify({
            "test": "Ollama Connection",
            "passed": is_healthy,
            "message": "Ollama is accessible" if is_healthy else "Ollama not accessible"
        })
    except Exception as e:
        return jsonify({
            "test": "Ollama Connection",
            "passed": False,
            "error": str(e)
        })

@app.route('/api/test/models')
@async_route
async def test_models():
    """Test model listing."""
    try:
        models = await backend.list_models()
        return jsonify({
            "test": "Model Listing",
            "passed": len(models) > 0,
            "model_count": len(models),
            "models": [m.get('name', 'unknown') for m in models[:5]]
        })
    except Exception as e:
        return jsonify({
            "test": "Model Listing",
            "passed": False,
            "error": str(e)
        })

@app.route('/api/test/chat', methods=['POST'])
@async_route
async def test_chat():
    """Test chat functionality."""
    try:
        data = request.json
        message = data.get('message', 'Hello, test message')
        
        response = await backend.chat(
            model='qwen2.5:3b',
            messages=[{'role': 'user', 'content': message}],
            stream=False
        )
        
        # Extract content
        if hasattr(response, 'message'):
            content = response.message.content
        elif isinstance(response, dict):
            content = response.get('message', {}).get('content', '')
        else:
            content = str(response)
        
        return jsonify({
            "test": "Chat Functionality",
            "passed": len(content) > 0,
            "query": message,
            "response": content[:200]  # First 200 chars
        })
    except Exception as e:
        return jsonify({
            "test": "Chat Functionality",
            "passed": False,
            "error": str(e)
        })

@app.route('/api/test/tools')
def test_tools():
    """Test tool registration."""
    try:
        registry = register_default_tools()
        tools = registry.list_tools()
        
        return jsonify({
            "test": "Tool Registration",
            "passed": len(tools) >= 17,
            "tool_count": len(tools),
            "tools": tools
        })
    except Exception as e:
        return jsonify({
            "test": "Tool Registration",
            "passed": False,
            "error": str(e)
        })

@app.route('/api/test/all')
@async_route
async def run_all_tests():
    """Run all tests sequentially."""
    results = []
    
    # Test 1: Health
    try:
        is_healthy = await backend.health_check()
        results.append({
            "test": "Ollama Connection",
            "passed": is_healthy,
            "message": "Ollama is accessible" if is_healthy else "Ollama not accessible"
        })
    except Exception as e:
        results.append({
            "test": "Ollama Connection",
            "passed": False,
            "error": str(e)
        })
    
    # Test 2: Models
    try:
        models = await backend.list_models()
        results.append({
            "test": "Model Listing",
            "passed": len(models) > 0,
            "model_count": len(models),
            "models": [m.get('name', 'unknown') for m in models[:5]]
        })
    except Exception as e:
        results.append({
            "test": "Model Listing",
            "passed": False,
            "error": str(e)
        })
    
    # Test 3: Chat
    try:
        response = await backend.chat(
            model='qwen2.5:3b',
            messages=[{'role': 'user', 'content': 'What is 2+2?'}],
            stream=False
        )
        
        if hasattr(response, 'message'):
            content = response.message.content
        elif isinstance(response, dict):
            content = response.get('message', {}).get('content', '')
        else:
            content = str(response)
        
        results.append({
            "test": "Chat Functionality",
            "passed": len(content) > 0,
            "query": "What is 2+2?",
            "response": content[:200]
        })
    except Exception as e:
        results.append({
            "test": "Chat Functionality",
            "passed": False,
            "error": str(e)
        })
    
    # Test 4: Tools
    try:
        registry = register_default_tools()
        tools = registry.list_tools()
        
        results.append({
            "test": "Tool Registration",
            "passed": len(tools) >= 17,
            "tool_count": len(tools),
            "tools": tools
        })
    except Exception as e:
        results.append({
            "test": "Tool Registration",
            "passed": False,
            "error": str(e)
        })
    
    # Calculate summary
    passed = sum(1 for r in results if r.get('passed', False))
    failed = len(results) - passed
    
    return jsonify({
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{(passed/len(results)*100):.1f}%"
        },
        "results": results
    })

# Create templates directory and HTML
templates_dir = Path('templates')
templates_dir.mkdir(exist_ok=True)

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sentinel AI Workbench - Test Interface</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .subtitle {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .content {
            padding: 40px;
        }
        
        .test-section {
            margin-bottom: 30px;
        }
        
        .test-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 16px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            margin-right: 10px;
            margin-bottom: 10px;
        }
        
        .test-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        .test-button:active {
            transform: translateY(0);
        }
        
        #results {
            margin-top: 30px;
        }
        
        .result-card {
            background: #f8f9fa;
            border-left: 4px solid #28a745;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 8px;
            animation: slideIn 0.3s ease-out;
        }
        
        .result-card.failed {
            border-left-color: #dc3545;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateX(-20px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .result-title {
            font-weight: bold;
            font-size: 1.2em;
        }
        
        .result-badge {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }
        
        .result-badge.passed {
            background: #28a745;
            color: white;
        }
        
        .result-badge.failed {
            background: #dc3545;
            color: white;
        }
        
        .result-details {
            color: #666;
            font-size: 0.95em;
            line-height: 1.6;
        }
        
        .summary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        
        .summary-item {
            text-align: center;
        }
        
        .summary-value {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .summary-label {
            font-size: 1em;
            opacity: 0.9;
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 40px;
        }
        
        .loading.active {
            display: block;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        code {
            background: #e9ecef;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🛰️ Sentinel AI Workbench</h1>
            <p class="subtitle">Comprehensive System Testing Interface</p>
        </header>
        
        <div class="content">
            <div class="test-section">
                <h2>Run Tests</h2>
                <button class="test-button" onclick="runTest('health')">🔧 Test Ollama Connection</button>
                <button class="test-button" onclick="runTest('models')">📦 Test Model Listing</button>
                <button class="test-button" onclick="runTest('chat')">💬 Test Chat Functionality</button>
                <button class="test-button" onclick="runTest('tools')">🛠️ Test Tool Registration</button>
                <button class="test-button" onclick="runAllTests()" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">🚀 Run All Tests</button>
            </div>
            
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>Running tests...</p>
            </div>
            
            <div id="results"></div>
        </div>
    </div>
    
    <script>
        async function runTest(testName) {
            showLoading();
            
            try {
                let response;
                if (testName === 'chat') {
                    response = await fetch(`/api/test/${testName}`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({message: 'What is 2+2?'})
                    });
                } else {
                    response = await fetch(`/api/test/${testName}`);
                }
                
                const result = await response.json();
                displayResult(result);
            } catch (error) {
                displayResult({
                    test: testName,
                    passed: false,
                    error: error.message
                });
            }
            
            hideLoading();
        }
        
        async function runAllTests() {
            showLoading();
            
            try {
                const response = await fetch('/api/test/all');
                const data = await response.json();
                
                // Display summary
                displaySummary(data.summary);
                
                // Display individual results
                data.results.forEach(result => {
                    displayResult(result, false);
                });
            } catch (error) {
                displayResult({
                    test: 'All Tests',
                    passed: false,
                    error: error.message
                });
            }
            
            hideLoading();
        }
        
        function displaySummary(summary) {
            const resultsDiv = document.getElementById('results');
            const summaryHTML = `
                <div class="summary">
                    <div class="summary-item">
                        <div class="summary-value">${summary.total}</div>
                        <div class="summary-label">Total Tests</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-value">${summary.passed}</div>
                        <div class="summary-label">Passed</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-value">${summary.failed}</div>
                        <div class="summary-label">Failed</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-value">${summary.pass_rate}</div>
                        <div class="summary-label">Pass Rate</div>
                    </div>
                </div>
            `;
            resultsDiv.innerHTML = summaryHTML + resultsDiv.innerHTML;
        }
        
        function displayResult(result, clear = true) {
            const resultsDiv = document.getElementById('results');
            
            if (clear) {
                resultsDiv.innerHTML = '';
            }
            
            const statusClass = result.passed ? 'passed' : 'failed';
            const statusText = result.passed ? 'PASSED ✓' : 'FAILED ✗';
            
            let details = '';
            if (result.message) {
                details += `<p>${result.message}</p>`;
            }
            if (result.model_count !== undefined) {
                details += `<p>Models found: <code>${result.model_count}</code></p>`;
                if (result.models) {
                    details += `<p>Sample models: ${result.models.map(m => `<code>${m}</code>`).join(', ')}</p>`;
                }
            }
            if (result.tool_count !== undefined) {
                details += `<p>Tools registered: <code>${result.tool_count}</code></p>`;
                if (result.tools) {
                    details += `<p>Tools: ${result.tools.slice(0, 5).map(t => `<code>${t}</code>`).join(', ')}...</p>`;
                }
            }
            if (result.query) {
                details += `<p>Query: <code>${result.query}</code></p>`;
            }
            if (result.response) {
                details += `<p>Response: ${result.response}</p>`;
            }
            if (result.error) {
                details += `<p style="color: #dc3545;">Error: ${result.error}</p>`;
            }
            
            const cardHTML = `
                <div class="result-card ${statusClass}">
                    <div class="result-header">
                        <span class="result-title">${result.test}</span>
                        <span class="result-badge ${statusClass}">${statusText}</span>
                    </div>
                    <div class="result-details">
                        ${details}
                    </div>
                </div>
            `;
            
            resultsDiv.innerHTML += cardHTML;
        }
        
        function showLoading() {
            document.getElementById('loading').classList.add('active');
        }
        
        function hideLoading() {
            document.getElementById('loading').classList.remove('active');
        }
        
        // Auto-run health check on load
        window.addEventListener('load', () => {
            setTimeout(() => runTest('health'), 500);
        });
    </script>
</body>
</html>"""

with open(templates_dir / 'index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

if __name__ == '__main__':
    print("🚀 Starting Sentinel AI Workbench Web Test Interface...")
    print("📍 Open browser at: http://localhost:5000")
    print("🧪 Ready for Playwright testing!")
    app.run(host='0.0.0.0', port=5000, debug=True)
