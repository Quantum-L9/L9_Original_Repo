#!/usr/bin/env python3
"""
L9 Local Dashboard
==================
A minimal local web UI to chat with L running in Docker on your Mac.
Runs locally so only YOU can access it.

Usage:
    1. Start L9 in Docker:
       docker compose up -d

    2. Run this dashboard:
       cd /Users/ib-mac/Projects/L9/local_dashboard
       python app.py

    3. Open: http://127.0.0.1:5050
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "App",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2025-12-20T15:08:40Z",
    "updated_at": "2026-01-17T23:47:56Z",
    "layer": "operations",
    "domain": "api_gateway",
    "module_name": "app",
    "type": "router",
    "status": "active",
    "integrates_with": {
        "api_endpoints": ["GET /", "POST /api/chat", "GET /api/health"],
        "datasources": ["HTTP API"],
        "memory_layers": ["episodic_memory"],
        "imported_by": [],
    },
}
# ============================================================================

import os
import sys
from datetime import datetime

import structlog

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from core.decorators import must_stay_async

# =============================================================================
# Configuration
# =============================================================================

# L9 API endpoint (local Docker)

logger = structlog.get_logger(__name__)
L9_API_URL = os.getenv("L9_API_URL", "http://localhost:8000")
L9_API_KEY = os.getenv(
    "L9_API_KEY", "9c4753df3b7ee85e2370b0e9a55355e59a9cf3c15f65791de4ab8cdd656b4304"
)

# Local settings
LOCAL_HOST = "127.0.0.1"  # Only accessible from this machine
LOCAL_PORT = 5050

# =============================================================================
# App
# =============================================================================

app = FastAPI(title="L9 Local Dashboard", docs_url=None, redoc_url=None)

# Conversation history (in-memory for this session)
conversation_history: list[dict] = []

# =============================================================================
# HTML Template
# =============================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>L9 — Talk to L</title>
    <style>
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-tertiary: #1a1a25;
            --accent: #00ff88;
            --accent-dim: #00aa5c;
            --text-primary: #e0e0e0;
            --text-secondary: #888;
            --border: #2a2a35;
            --user-bg: #1a2520;
            --l-bg: #15151f;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
            background: var(--bg-primary);
            color: var(--text-primary);
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        /* Header */
        .header {
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border);
            padding: 16px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .logo-icon {
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dim) 100%);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            color: var(--bg-primary);
            font-size: 18px;
        }
        
        .logo-text {
            font-size: 18px;
            font-weight: 600;
            color: var(--text-primary);
        }
        
        .logo-text span {
            color: var(--accent);
        }
        
        .status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: var(--text-secondary);
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--accent);
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        /* Chat Container */
        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        
        .message {
            max-width: 75%;
            padding: 14px 18px;
            border-radius: 12px;
            line-height: 1.5;
            font-size: 14px;
        }
        
        .message.user {
            align-self: flex-end;
            background: var(--user-bg);
            border: 1px solid var(--accent-dim);
            color: var(--accent);
        }
        
        .message.l {
            align-self: flex-start;
            background: var(--l-bg);
            border: 1px solid var(--border);
        }
        
        .message.l .sender {
            color: var(--accent);
            font-weight: 600;
            margin-bottom: 8px;
            font-size: 12px;
        }
        
        .message.error {
            background: #2a1515;
            border-color: #ff4444;
            color: #ff8888;
        }
        
        .message pre {
            background: var(--bg-primary);
            padding: 12px;
            border-radius: 6px;
            overflow-x: auto;
            margin-top: 8px;
            font-size: 13px;
        }
        
        .timestamp {
            font-size: 10px;
            color: var(--text-secondary);
            margin-top: 6px;
        }
        
        /* Input Area */
        .input-area {
            background: var(--bg-secondary);
            border-top: 1px solid var(--border);
            padding: 20px 24px;
        }
        
        .input-container {
            display: flex;
            gap: 12px;
            max-width: 1000px;
            margin: 0 auto;
        }
        
        #message-input {
            flex: 1;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 14px 18px;
            color: var(--text-primary);
            font-family: inherit;
            font-size: 14px;
            resize: none;
            min-height: 50px;
            max-height: 150px;
        }
        
        #message-input:focus {
            outline: none;
            border-color: var(--accent);
        }
        
        #message-input::placeholder {
            color: var(--text-secondary);
        }
        
        #send-btn {
            background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dim) 100%);
            border: none;
            border-radius: 8px;
            padding: 14px 24px;
            color: var(--bg-primary);
            font-family: inherit;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.1s, opacity 0.2s;
        }
        
        #send-btn:hover {
            transform: scale(1.02);
        }
        
        #send-btn:active {
            transform: scale(0.98);
        }
        
        #send-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        /* Loading */
        .loading {
            display: flex;
            gap: 4px;
            padding: 20px;
        }
        
        .loading-dot {
            width: 8px;
            height: 8px;
            background: var(--accent);
            border-radius: 50%;
            animation: bounce 1.4s infinite ease-in-out;
        }
        
        .loading-dot:nth-child(1) { animation-delay: -0.32s; }
        .loading-dot:nth-child(2) { animation-delay: -0.16s; }
        
        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
        
        /* Empty state */
        .empty-state {
            text-align: center;
            color: var(--text-secondary);
            padding: 60px 20px;
        }
        
        .empty-state h2 {
            color: var(--accent);
            margin-bottom: 12px;
            font-size: 24px;
        }
        
        .empty-state p {
            font-size: 14px;
            max-width: 400px;
            margin: 0 auto;
            line-height: 1.6;
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--bg-primary);
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--text-secondary);
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">
            <div class="logo-icon">L</div>
            <div class="logo-text">L9 <span>Dashboard</span></div>
        </div>
        <div class="status">
            <div class="status-dot"></div>
            <span>Connected to L9</span>
        </div>
    </div>
    
    <div class="chat-container" id="chat-container">
        <div class="empty-state" id="empty-state">
            <h2>Talk to L</h2>
            <p>Your CTO is ready. Type a message below to start a conversation with L.</p>
        </div>
    </div>
    
    <div class="input-area">
        <div class="input-container">
            <textarea 
                id="message-input" 
                placeholder="Message L..." 
                rows="1"
                autofocus
            ></textarea>
            <button id="send-btn" onclick="sendMessage()">Send</button>
        </div>
    </div>
    
    <script>
        const chatContainer = document.getElementById('chat-container');
        const messageInput = document.getElementById('message-input');
        const sendBtn = document.getElementById('send-btn');
        const emptyState = document.getElementById('empty-state');
        
        // Auto-resize textarea
        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 150) + 'px';
        });
        
        // Enter to send (Shift+Enter for newline)
        messageInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        function formatTime() {
            return new Date().toLocaleTimeString('en-US', { 
                hour: '2-digit', 
                minute: '2-digit' 
            });
        }
        
        function addMessage(content, isUser, isError = false) {
            if (emptyState) {
                emptyState.remove();
            }
            
            const msg = document.createElement('div');
            msg.className = `message ${isUser ? 'user' : 'l'} ${isError ? 'error' : ''}`;
            
            if (isUser) {
                msg.innerHTML = `
                    <div>${escapeHtml(content)}</div>
                    <div class="timestamp">${formatTime()}</div>
                `;
            } else {
                msg.innerHTML = `
                    <div class="sender">L</div>
                    <div>${formatContent(content)}</div>
                    <div class="timestamp">${formatTime()}</div>
                `;
            }
            
            chatContainer.appendChild(msg);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
        
        function addLoading() {
            const loading = document.createElement('div');
            loading.className = 'loading';
            loading.id = 'loading';
            loading.innerHTML = `
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
                <div class="loading-dot"></div>
            `;
            chatContainer.appendChild(loading);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
        
        function removeLoading() {
            const loading = document.getElementById('loading');
            if (loading) loading.remove();
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function formatContent(content) {
            // Handle code blocks
            let formatted = escapeHtml(content);
            formatted = formatted.replace(/```([\\s\\S]*?)```/g, '<pre>$1</pre>');
            formatted = formatted.replace(/`([^`]+)`/g, '<code style="background:#1a1a25;padding:2px 6px;border-radius:3px;">$1</code>');
            formatted = formatted.replace(/\\n/g, '<br>');
            return formatted;
        }
        
        async function sendMessage() {
            const message = messageInput.value.trim();
            if (!message) return;
            
            // Clear input
            messageInput.value = '';
            messageInput.style.height = 'auto';
            
            // Add user message
            addMessage(message, true);
            
            // Disable input while waiting
            sendBtn.disabled = true;
            messageInput.disabled = true;
            addLoading();
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ message })
                });
                
                removeLoading();
                
                if (!response.ok) {
                    const error = await response.json();
                    addMessage(`Error: ${error.detail || 'Failed to reach L'}`, false, true);
                } else {
                    const data = await response.json();
                    addMessage(data.reply, false);
                }
            } catch (err) {
                removeLoading();
                addMessage(`Connection error: ${err.message}`, false, true);
            } finally {
                sendBtn.disabled = false;
                messageInput.disabled = false;
                messageInput.focus();
            }
        }
    </script>
</body>
</html>
"""

# =============================================================================
# Routes
# =============================================================================


@app.get("/", response_class=HTMLResponse)
@must_stay_async("FastAPI/ASGI route handler")
async def index():
    """Serve the dashboard."""
    return HTML_TEMPLATE


@app.post("/api/chat")
async def chat(request: Request):
    """Send message to L9 Agent Executor in Docker."""
    try:
        body = await request.json()
        message = body.get("message", "")

        if not message:
            raise HTTPException(status_code=400, detail="Message is required")

        # Call L9 Agent Execute API in Docker
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{L9_API_URL}/agent/execute",
                headers={
                    "Authorization": f"Bearer {L9_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "message": message,
                    "kind": "query",
                    "source_id": "local_dashboard",
                },
            )

            if response.status_code != 200:
                error_detail = response.text
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"L9 API error: {error_detail}",
                )

            data = response.json()

            # Extract reply from executor response
            reply = data.get("result", "") or data.get("error", "No response from L")

            # Store in local history
            conversation_history.append(
                {
                    "role": "user",
                    "content": message,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            conversation_history.append(
                {
                    "role": "assistant",
                    "content": reply,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            return {"reply": reply}

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503, detail="Cannot connect to L9 API. Is Docker running?"
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="L9 API request timed out")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
@must_stay_async("FastAPI/ASGI route handler")
async def health():
    """Local health check."""
    return {
        "status": "ok",
        "l9_url": L9_API_URL,
        "conversation_count": len(conversation_history) // 2,
    }


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    logger.info(f"""

╔══════════════════════════════════════════════════════════════╗
╔══════════════════════════════════════════════════════════════╗

║                    L9 LOCAL DASHBOARD                        ║
║                    L9 LOCAL DASHBOARD                        ║

╠══════════════════════════════════════════════════════════════╣
╠══════════════════════════════════════════════════════════════╣

║  Dashboard:   http://{LOCAL_HOST}:{LOCAL_PORT}                        ║
║  Dashboard:   http://{LOCAL_HOST}:{LOCAL_PORT}                        ║

║  L9 API:      {L9_API_URL:<43} ║
║  L9 API:      {L9_API_URL:<43} ║

║                                                              ║
║                                                              ║

║  Press Ctrl+C to stop                                        ║
║  Press Ctrl+C to stop                                        ║

╚══════════════════════════════════════════════════════════════╝
╚══════════════════════════════════════════════════════════════╝

""")

    uvicorn.run(app, host=LOCAL_HOST, port=LOCAL_PORT, log_level="warning")

# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "LOC-OPER-001",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": ["core.decorators"],
    "tags": [
        "api",
        "api-gateway",
        "async",
        "auth",
        "endpoint",
        "event-driven",
        "http-client",
        "logging",
        "messaging",
        "operations",
    ],
    "keywords": ["app", "chat", "health", "index"],
    "business_value": "cd /Users/ib-mac/Projects/L9/local_dashboard python app.py 3. Open: http://127.0.0.1:5050",
    "last_modified": "2026-01-17T23:47:56Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
