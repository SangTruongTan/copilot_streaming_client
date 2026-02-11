# Streaming Examples - Ready-to-Use Code Snippets

This document contains practical, copy-paste ready examples for implementing real-time streaming with Copilot CLI.

---

## Example 1: Basic Streaming with Delta Events

A simple example showing how to display streaming responses in real-time.

**File:** `stream_basic.py`

```python
#!/usr/bin/env python3
"""
Basic streaming example - Display real-time responses from Copilot
"""

import asyncio
from copilot import CopilotClient
from copilot.generated.session_events import SessionEventType


async def main():
    # Create and start client
    client = CopilotClient()
    await client.start()
    print("✓ Connected to Copilot CLI")

    # Create session with streaming enabled
    # Note: Streaming is controlled per-session (not at CLI startup)
    session = await client.create_session({
        "model": "gpt-4",
        "streaming": True  # Enable delta events for this session
    })
    print("✓ Created session with streaming")

    # Set up event handler
    def on_event(event):
        if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            # Print streaming chunks in real-time
            # Note: For Python SDK events, use .delta_content (snake_case)
            print(event.data.delta_content, end="", flush=True)

        elif event.type == SessionEventType.ASSISTANT_MESSAGE:
            # Full message received (after all deltas)
            print()  # newline

        elif event.type == SessionEventType.SESSION_ERROR:
            print(f"Error: {event.data.message}")

    # Subscribe to events
    unsubscribe = session.on(on_event)

    # Send a prompt
    prompt = "Explain what machine learning is in 2-3 sentences"
    print(f"\n📝 Prompt: {prompt}\n")

    await session.send({"prompt": prompt})

    # Wait for response
    await asyncio.sleep(5)

    # Cleanup
    unsubscribe()
    await session.destroy()
    await client.stop()
    print("\n✓ Cleanup complete")


if __name__ == "__main__":
    asyncio.run(main())
```

**Run it:**
```bash
python stream_basic.py
```

---

## Example 2: Token Counter with Streaming

Track token counts and streaming speed in real-time.

**File:** `stream_token_counter.py`

```python
#!/usr/bin/env python3
"""
Token counter - Monitor streaming speed and token count
"""

import asyncio
import time
from copilot import CopilotClient
from copilot.generated.session_events import SessionEventType


class TokenCounter:
    def __init__(self):
        self.tokens = 0
        self.start_time = None
        self.last_token_time = None
        self.buffer = ""

    def on_event(self, event):
        """Handle streaming events"""
        if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            if self.start_time is None:
                self.start_time = time.time()

            self.last_token_time = time.time()
            chunk = event.data.delta_content

            self.buffer += chunk
            self.tokens += 1

            # Print every 5 tokens with speed
            if self.tokens % 5 == 0:
                elapsed = time.time() - self.start_time
                tps = self.tokens / elapsed if elapsed > 0 else 0
                print(f"[{self.tokens:3d} tokens | {tps:.1f} tok/s] ", end="")
                print(self.buffer[:50].replace("\n", " "), end="")
                if len(self.buffer) > 50:
                    print("...", end="")
                print()
                self.buffer = ""

        elif event.type == SessionEventType.ASSISTANT_MESSAGE:
            # Final message
            if self.buffer:
                print(f"[Final] {self.buffer}")

        elif event.type == SessionEventType.SESSION_IDLE:
            elapsed = time.time() - self.start_time if self.start_time else 0
            avg_speed = self.tokens / elapsed if elapsed > 0 else 0
            print(f"\n✓ Complete: {self.tokens} tokens in {elapsed:.2f}s ({avg_speed:.1f} tok/s)")


async def main():
    client = CopilotClient()
    await client.start()

    session = await client.create_session({
        "model": "gpt-4",
        "streaming": True
    })

    counter = TokenCounter()
    unsubscribe = session.on(counter.on_event)

    print("📊 Streaming token counter started...\n")

    await session.send({
        "prompt": "Write a short Python function to calculate fibonacci numbers"
    })

    # Wait for completion
    await asyncio.sleep(10)

    unsubscribe()
    await session.destroy()
    await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

**Run it:**
```bash
python stream_token_counter.py
```

---

## Example 3: Streaming with Multiple Subscribers

Demonstrate how multiple handlers can listen to the same stream.

**File:** `stream_multi_subscriber.py`

```python
#!/usr/bin/env python3
"""
Multiple subscribers listening to the same stream
"""

import asyncio
from copilot import CopilotClient
from copilot.generated.session_events import SessionEventType


class ConsoleRenderer:
    """Render tokens to console"""
    def on_event(self, event):
        if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            print(event.data.delta_content, end="", flush=True)


class DataCollector:
    """Collect all tokens for storage"""
    def __init__(self):
        self.full_response = ""

    def on_event(self, event):
        if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            self.full_response += event.data.delta_content
        elif event.type == SessionEventType.SESSION_IDLE:
            # Save to file
            with open("response.txt", "w") as f:
                f.write(self.full_response)
            print(f"\n✓ Saved {len(self.full_response)} characters to response.txt")


class MetricsCollector:
    """Collect metrics"""
    def __init__(self):
        self.token_count = 0
        self.event_types = {}

    def on_event(self, event):
        # Count event types
        event_type = str(event.type)
        self.event_types[event_type] = self.event_types.get(event_type, 0) + 1

        if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            self.token_count += 1

        elif event.type == SessionEventType.SESSION_IDLE:
            print(f"\n📊 Metrics:")
            print(f"  - Total tokens: {self.token_count}")
            print(f"  - Event types: {self.event_types}")


async def main():
    client = CopilotClient()
    await client.start()

    session = await client.create_session({
        "model": "gpt-4",
        "streaming": True
    })

    # Create subscribers
    renderer = ConsoleRenderer()
    collector = DataCollector()
    metrics = MetricsCollector()

    # Subscribe all of them
    unsub1 = session.on(renderer.on_event)
    unsub2 = session.on(collector.on_event)
    unsub3 = session.on(metrics.on_event)

    print("🔗 Connected 3 subscribers\n")

    await session.send({
        "prompt": "What are the top 3 machine learning frameworks and why?"
    })

    # Wait for completion
    await asyncio.sleep(5)

    # Unsubscribe
    unsub1()
    unsub2()
    unsub3()

    await session.destroy()
    await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

**Run it:**
```bash
python stream_multi_subscriber.py
```

---

## Example 4: Streaming with Tool Calls

Demonstrate streaming with tool execution.

**File:** `stream_with_tools.py`

```python
#!/usr/bin/env python3
"""
Streaming with custom tool usage
"""

import asyncio
from pydantic import BaseModel, Field
from copilot import CopilotClient, ToolInvocation, define_tool
from copilot.generated.session_events import SessionEventType


# Define a custom tool
class CalculateParams(BaseModel):
    expression: str = Field(description="Math expression to evaluate")


@define_tool("calculate", description="Evaluate a math expression")
def calculate(params: CalculateParams, invocation: ToolInvocation) -> str:
    """A tool that evaluates math expressions"""
    try:
        result = eval(params.expression)
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {e}"


class EventTracker:
    """Track all event types"""
    def __init__(self):
        self.events = []

    def on_event(self, event):
        event_type = str(event.type)

        if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            print(event.data.delta_content, end="", flush=True)

        elif event.type == SessionEventType.TOOL_CALL:
            print(f"\n🔧 Tool called: {event.data.name}")

        elif event.type == SessionEventType.SESSION_IDLE:
            print("\n✓ Session idle")

        self.events.append(event_type)


async def main():
    client = CopilotClient()
    await client.start()

    # Create session with custom tool
    session = await client.create_session({
        "model": "gpt-4",
        "streaming": True,
        "tools": [calculate]
    })

    tracker = EventTracker()
    unsubscribe = session.on(tracker.on_event)

    print("🛠️  Session created with 'calculate' tool\n")

    await session.send({
        "prompt": "What is 25 * 4 + 10? Use the calculate tool."
    })

    # Wait for response
    await asyncio.sleep(5)

    unsubscribe()
    await session.destroy()
    await client.stop()

    print(f"\n📋 Event log: {tracker.events}")


if __name__ == "__main__":
    asyncio.run(main())
```

**Run it:**
```bash
python stream_with_tools.py
```

---

## Example 5: Streaming with Error Handling

Handle errors and edge cases gracefully.

**File:** `stream_robust.py`

```python
#!/usr/bin/env python3
"""
Streaming with comprehensive error handling
"""

import asyncio
from copilot import CopilotClient
from copilot.generated.session_events import SessionEventType


class RobustStreamHandler:
    """Handle streaming with errors and timeouts"""

    def __init__(self):
        self.chunks = []
        self.errors = []
        self.complete = asyncio.Event()

    def on_event(self, event):
        try:
            if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
                chunk = event.data.delta_content
                self.chunks.append(chunk)
                print(chunk, end="", flush=True)

            elif event.type == SessionEventType.ASSISTANT_MESSAGE:
                print()  # newline

            elif event.type == SessionEventType.SESSION_ERROR:
                error_msg = getattr(event.data, 'message', 'Unknown error')
                self.errors.append(error_msg)
                print(f"⚠️  Error: {error_msg}")

            elif event.type == SessionEventType.SESSION_IDLE:
                self.complete.set()

        except Exception as e:
            print(f"❌ Handler exception: {e}")
            self.errors.append(str(e))

    async def wait_for_completion(self, timeout=30):
        """Wait for completion with timeout"""
        try:
            await asyncio.wait_for(
                self.complete.wait(),
                timeout=timeout
            )
            return True
        except asyncio.TimeoutError:
            print(f"⏱️  Timeout after {timeout}s")
            return False

    @property
    def full_response(self):
        return "".join(self.chunks)

    @property
    def success(self):
        return len(self.errors) == 0


async def main():
    try:
        # Start client
        client = CopilotClient()
        await client.start()
        print("✓ Client connected\n")

        # Create session
        session = await client.create_session({
            "model": "gpt-4",
            "streaming": True
        })
        print("✓ Session created\n")

        # Set up handler
        handler = RobustStreamHandler()
        unsubscribe = session.on(handler.on_event)

        # Send request
        print("📝 Sending request...\n")
        await session.send({
            "prompt": "Explain API design principles"
        })

        # Wait with timeout
        success = await handler.wait_for_completion(timeout=30)

        # Report results
        print("\n" + "="*50)
        if success:
            print("✅ Success!")
            print(f"Response length: {len(handler.full_response)} chars")
        else:
            print("❌ Failed or timed out")
            if handler.errors:
                print("Errors:")
                for err in handler.errors:
                    print(f"  - {err}")

        # Cleanup
        unsubscribe()
        await session.destroy()
        await client.stop()

    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        await client.force_stop()


if __name__ == "__main__":
    asyncio.run(main())
```

**Run it:**
```bash
python stream_robust.py
```

---

## Example 6: Streaming Responses to Multiple Users (Async)

Demonstrate handling multiple concurrent sessions.

**File:** `stream_concurrent.py`

```python
#!/usr/bin/env python3
"""
Concurrent streaming for multiple sessions
"""

import asyncio
from copilot import CopilotClient
from copilot.generated.session_events import SessionEventType


class SessionHandler:
    """Handler for a single session"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.response = ""
        self.done = asyncio.Event()

    def on_event(self, event):
        if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            self.response += event.data.delta_content
        elif event.type == SessionEventType.SESSION_IDLE:
            self.done.set()


async def stream_prompt(client, prompt, user_id):
    """Stream a single prompt"""

    session = await client.create_session({
        "model": "gpt-4",
        "streaming": True
    })

    handler = SessionHandler(session.session_id)
    unsubscribe = session.on(handler.on_event)

    print(f"👤 User {user_id}: Sending '{prompt[:30]}...'")

    await session.send({"prompt": prompt})

    # Wait for completion
    await handler.done.wait()

    unsubscribe()
    await session.destroy()

    print(f"👤 User {user_id}: Got {len(handler.response)} chars")
    return handler.response


async def main():
    client = CopilotClient()
    await client.start()
    print("✓ Client connected\n")

    # Create concurrent tasks
    tasks = [
        stream_prompt(client, "What are variables in Python?", 1),
        stream_prompt(client, "What are lists in Python?", 2),
        stream_prompt(client, "What are functions in Python?", 3),
    ]

    print("🚀 Starting 3 concurrent streams...\n")

    # Wait for all to complete
    responses = await asyncio.gather(*tasks)

    print("\n" + "="*50)
    print("✅ All streams completed!")
    for i, response in enumerate(responses, 1):
        print(f"User {i}: {len(response)} chars received")

    await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

**Run it:**
```bash
python stream_concurrent.py
```

---

## Example 7: Streaming to WebSocket Client

Stream Copilot responses to a web client via WebSocket.

**File:** `stream_websocket.py`

```python
#!/usr/bin/env python3
"""
Stream Copilot responses to WebSocket clients
"""

import asyncio
import json
import aiohttp
from aiohttp import web
from copilot import CopilotClient
from copilot.generated.session_events import SessionEventType


class WebSocketManager:
    def __init__(self):
        self.clients = set()

    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        for ws in self.clients:
            try:
                await ws.send_json(message)
            except Exception as e:
                print(f"Broadcast error: {e}")


# Global manager
ws_manager = WebSocketManager()


async def websocket_handler(request):
    """Handle WebSocket connections"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    ws_manager.clients.add(ws)
    print(f"✓ Client connected (total: {len(ws_manager.clients)})")

    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                # Receive prompt from client
                prompt = msg.data

                # Stream response
                await stream_to_clients(prompt)

            elif msg.type == aiohttp.WSMsgType.ERROR:
                print(f"WebSocket error: {ws.exception()}")

    finally:
        ws_manager.clients.remove(ws)
        print(f"✓ Client disconnected (total: {len(ws_manager.clients)})")

    return ws


async def stream_to_clients(prompt: str):
    """Stream a response to all connected clients"""

    client = CopilotClient()
    await client.start()

    session = await client.create_session({
        "model": "gpt-4",
        "streaming": True
    })

    def on_event(event):
        if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            asyncio.create_task(
                ws_manager.broadcast({
                    "type": "chunk",
                    "content": event.data.delta_content
                })
            )
        elif event.type == SessionEventType.SESSION_IDLE:
            asyncio.create_task(
                ws_manager.broadcast({
                    "type": "complete"
                })
            )

    unsubscribe = session.on(on_event)

    await session.send({"prompt": prompt})

    # Wait for completion
    await asyncio.sleep(5)

    unsubscribe()
    await session.destroy()
    await client.stop()


async def main():
    app = web.Application()
    app.router.add_get("/ws", websocket_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 8080)
    await site.start()

    print("✓ WebSocket server on ws://localhost:8080/ws")

    try:
        await asyncio.sleep(3600)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
```

**Client HTML:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Copilot Streaming</title>
    <style>
        body { font-family: monospace; padding: 20px; }
        input { width: 100%; padding: 10px; }
        #response { border: 1px solid #ccc; padding: 10px; min-height: 100px; margin-top: 10px; }
    </style>
</head>
<body>
    <h1>Copilot Streaming</h1>
    <input type="text" id="prompt" placeholder="Enter your prompt...">
    <button onclick="send()">Send</button>
    <div id="response"></div>

    <script>
        const ws = new WebSocket("ws://localhost:8080/ws");
        const responseDiv = document.getElementById("response");

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === "chunk") {
                responseDiv.innerHTML += data.content.replace(/</g, "&lt;").replace(/>/g, "&gt;");
            } else if (data.type === "complete") {
                responseDiv.innerHTML += "<br><strong>✓ Complete</strong>";
            }
        };

        function send() {
            const prompt = document.getElementById("prompt").value;
            responseDiv.innerHTML = "";
            ws.send(prompt);
        }
    </script>
</body>
</html>
```

---

## Example 8: Streaming with Infinite Sessions (Context Compaction)

Stream with automatic context compaction enabled.

**File:** `stream_infinite_session.py`

```python
#!/usr/bin/env python3
"""
Streaming with infinite sessions and context compaction
"""

import asyncio
from copilot import CopilotClient
from copilot.generated.session_events import SessionEventType


async def main():
    client = CopilotClient()
    await client.start()

    # Create session with infinite sessions enabled
    session = await client.create_session({
        "model": "gpt-4",
        "streaming": True,
        "infinite_sessions": {
            "enabled": True,
            # Trigger background compaction at 50% context usage
            "background_compaction_threshold": 0.5,
            # Block at 80% usage
            "buffer_exhaustion_threshold": 0.8,
        }
    })

    print(f"✓ Session created (workspace: {session.workspace_path})\n")

    compaction_count = 0

    def on_event(event):
        nonlocal compaction_count

        if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            print(event.data.delta_content, end="", flush=True)

        elif event.type == SessionEventType.SESSION_COMPACTION_START:
            compaction_count += 1
            print(f"\n⚙️  Compaction #{compaction_count} started...")

        elif event.type == SessionEventType.SESSION_COMPACTION_COMPLETE:
            success = event.data.success
            tokens_removed = event.data.tokens_removed
            status = "✓" if success else "✗"
            print(f"{status} Compaction complete (removed {tokens_removed} tokens)\n")

        elif event.type == SessionEventType.SESSION_IDLE:
            print("\n✓ Session idle")

    unsubscribe = session.on(on_event)

    # Send multiple messages to trigger compaction
    prompts = [
        "Tell me about machine learning",
        "Now explain deep learning",
        "What's the difference between them?",
        "Tell me about transformers",
        "What is BERT?",
    ]

    for i, prompt in enumerate(prompts, 1):
        print(f"\n📝 Prompt {i}: {prompt}\n")
        await session.send({"prompt": prompt})
        await asyncio.sleep(3)

    unsubscribe()
    await session.destroy()
    await client.stop()

    print(f"\n📊 Total compactions: {compaction_count}")


if __name__ == "__main__":
    asyncio.run(main())
```

**Run it:**
```bash
python stream_infinite_session.py
```

---

## How to Use These Examples

1. **Install dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

2. **Ensure Copilot CLI is installed:**
   ```bash
   copilot --version
   ```

3. **Run any example:**
   ```bash
   python stream_basic.py
   ```

4. **Customize:**
   - Change prompts
   - Modify event handling logic
   - Add your own event types

---

## Key Takeaways

1. **Enable streaming:** Set `"streaming": True` in session config
2. **Listen to deltas:** Handle `ASSISTANT_MESSAGE_DELTA` events for chunks
3. **Use `SESSION_IDLE`:** Know when the response is complete
4. **Multiple subscribers:** Many handlers can listen to the same session
5. **Error handling:** Always wrap handlers in try-catch
6. **Async/await:** Use asyncio for concurrent streaming
7. **Concurrency:** Run multiple sessions simultaneously

---

## Common Errors & Solutions

| Error | Solution |
|-------|----------|
| `asyncio.TimeoutError` | Increase timeout or check Copilot CLI |
| `Connection refused` | Ensure Copilot CLI is installed and running |
| `SessionEventType not found` | Import from `copilot.generated.session_events` |
| `Handler crashes entire stream` | Wrap handler in try-catch |
| `Memory leak with long streams` | Unsubscribe handlers, destroy sessions |

