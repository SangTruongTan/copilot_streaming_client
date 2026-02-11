# Real-Time Streaming Events in Copilot SDK - Complete Implementation Guide

## Overview

The Copilot Python SDK supports real-time streaming events through a sophisticated architecture that combines **JSON-RPC 2.0 protocol** with **async/await patterns** and **thread-safe event dispatching**. This guide explains how it works and how to replicate it for your personal application.

## Architecture Overview

```
Your Application
       ↓
CopilotClient (connection manager)
       ↓
JsonRpcClient (async JSON-RPC 2.0)
       ↓
Copilot CLI (server)
       ↑ (notifications sent back)
       ↓
Notification Handler
       ↓
CopilotSession (session-specific handler)
       ↓
Event Handlers (your callbacks)
```

## Core Components

### 1. **JsonRpcClient** - Low-Level Communication
**Location:** `python/copilot/jsonrpc.py`

The `JsonRpcClient` is the foundation that handles all communication with the Copilot CLI server using the JSON-RPC 2.0 protocol.

#### Key Features:
- **Stdio Transport**: Uses pipes (stdin/stdout) with Content-Length headers
- **TCP Transport**: Optional TCP socket connection
- **Thread-Safe I/O**: Uses threading for blocking I/O while maintaining async interface
- **Message Reading Loop**: Runs in background thread, reads messages continuously

#### How It Works:

```python
# Runs in a background daemon thread
def _read_loop(self):
    while self._running:
        message = self._read_message()  # Blocking read
        if message:
            self._handle_message(message)

def _read_message(self):
    # Read Content-Length header
    header_line = self.process.stdout.readline()

    # Parse Content-Length
    header = header_line.decode("utf-8").strip()
    content_length = int(header.split(":")[1].strip())

    # Read empty line
    self.process.stdout.readline()

    # Read exact content bytes
    content_bytes = self._read_exact(content_length)
    return json.loads(content_bytes.decode("utf-8"))
```

#### Message Handling:

The `_handle_message()` method routes incoming messages:

```python
def _handle_message(self, message: dict):
    # 1. Response to our request? (has "id")
    if "id" in message:
        future = self.pending_requests.get(message["id"])
        if future:
            loop = future.get_loop()
            if "error" in message:
                loop.call_soon_threadsafe(future.set_exception, error)
            elif "result" in message:
                loop.call_soon_threadsafe(future.set_result, result)
        return

    # 2. Notification from server? (has "method", no "id")
    if "method" in message and "id" not in message:
        method = message["method"]
        params = message.get("params", {})
        # Thread-safe: schedule on event loop
        self._loop.call_soon_threadsafe(
            self.notification_handler,
            method,
            params
        )
        return

    # 3. Incoming request? (has both "method" and "id")
    if "method" in message and "id" in message:
        self._handle_request(message)
```

#### Key Design Notes:
- **Threading Model**: background reader thread + main asyncio thread
- **Thread-Safety**: Uses `call_soon_threadsafe()` to schedule callbacks on event loop
- **Blocking I/O**: Content-Length based framing ensures exact message boundaries

---

### 2. **CopilotClient** - Session Manager & Notification Router
**Location:** `python/copilot/client.py`

`CopilotClient` manages the overall connection, creates sessions, and routes notifications to appropriate sessions.

#### Initialization & Connection:

```python
async def start(self) -> None:
    """Start CLI server and establish connection"""
    if self._state == "connected":
        return

    self._state = "connecting"

    try:
        # Start the CLI process (unless connecting to external server)
        if not self._is_external_server:
            await self._start_cli_server()

        # Connect to the server
        await self._connect_to_server()

        # Verify protocol compatibility
        await self._verify_protocol_version()

        self._state = "connected"
    except Exception:
        self._state = "error"
        raise
```

#### Notification Handler Setup (Critical for Streaming):

```python
async def _connect_via_stdio(self) -> None:
    """Set up notification handler that routes events to sessions"""

    # Create JSON-RPC client
    self._client = JsonRpcClient(self._process)

    # Define notification handler
    def handle_notification(method: str, params: dict):
        if method == "session.event":
            # STREAMING EVENTS from CLI arrive here as notifications
            session_id = params["sessionId"]
            event_dict = params["event"]

            # Convert dict to strongly-typed SessionEvent object
            event = session_event_from_dict(event_dict)

            # Route event to the appropriate session
            with self._sessions_lock:
                session = self._sessions.get(session_id)

            if session:
                session._dispatch_event(event)

        elif method == "session.lifecycle":
            # Handle session lifecycle events
            lifecycle_event = SessionLifecycleEvent.from_dict(params)
            self._dispatch_lifecycle_event(lifecycle_event)

    # Register the handler
    self._client.set_notification_handler(handle_notification)

    # Also register request handlers for tool calls, permissions, etc.
    self._client.set_request_handler("tool.call", self._handle_tool_call_request)
    self._client.set_request_handler("permission.request", self._handle_permission_request)
    self._client.set_request_handler("userInput.request", self._handle_user_input_request)

    # Start background listener
    loop = asyncio.get_running_loop()
    self._client.start(loop)
```

#### Session Creation with Streaming:

Streaming is controlled **per-session**, not at CLI startup:

```python
async def create_session(self, config: Optional[SessionConfig] = None) -> CopilotSession:
    """Create a new session with optional streaming"""
    cfg = config or {}

    payload: dict[str, Any] = {}

    # Enable streaming if requested
    # Note: This is per-session control, not CLI-level
        payload["streaming"] = streaming  # True = get delta events

    # Send request to CLI
    response = await self._client.request("session.create", payload)

    session_id = response["sessionId"]
    session = CopilotSession(session_id, self._client, workspace_path)

    # Add session to registry (for routing notifications)
    with self._sessions_lock:
        self._sessions[session_id] = session

    return session
```

---

### 3. **CopilotSession** - Event Subscription & Dispatch
**Location:** `python/copilot/session.py`

`CopilotSession` manages event subscriptions and dispatches events to handlers.

#### Event Subscription Mechanism:

```python
def on(self, handler: Callable[[SessionEvent], None]) -> Callable[[], None]:
    """Register a handler for session events"""

    with self._event_handlers_lock:
        self._event_handlers.add(handler)

    def unsubscribe():
        with self._event_handlers_lock:
            self._event_handlers.discard(handler)

    return unsubscribe

def _dispatch_event(self, event: SessionEvent) -> None:
    """Called by CopilotClient when notification arrives"""

    # Get snapshot of handlers (avoid holding lock during calls)
    with self._event_handlers_lock:
        handlers = list(self._event_handlers)

    # Call each handler with the event
    for handler in handlers:
        try:
            handler(event)
        except Exception as e:
            print(f"Error in session event handler: {e}")
```

#### Sending Messages:

```python
async def send(self, options: MessageOptions) -> str:
    """Send a message to the session"""
    response = await self._client.request(
        "session.send",
        {
            "sessionId": self.session_id,
            "prompt": options["prompt"],
            "attachments": options.get("attachments"),
        }
    )
    return response["messageId"]

async def send_and_wait(
    self,
    options: MessageOptions,
    timeout: Optional[float] = None
) -> Optional[SessionEvent]:
    """Send message and wait for session.idle event"""

    idle_event = asyncio.Event()
    last_assistant_message: Optional[SessionEvent] = None

    def handler(event: SessionEvent) -> None:
        nonlocal last_assistant_message

        if event.type == SessionEventType.ASSISTANT_MESSAGE:
            last_assistant_message = event
        elif event.type == SessionEventType.SESSION_IDLE:
            idle_event.set()

    unsubscribe = self.on(handler)
    try:
        await self.send(options)
        await asyncio.wait_for(
            idle_event.wait(),
            timeout=timeout if timeout else 60.0
        )
        return last_assistant_message
    finally:
        unsubscribe()
```

---

## Event Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│ Copilot CLI Server                                           │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ Session Processing                                     │   │
│ │ - Receives "session.send" request from SDK             │   │
│ │ - Generates streaming events as assistant responds     │   │
│ │ - Sends notifications back to SDK                      │   │
│ └────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
         │
         │ Notifications (JSON-RPC)
         │ method: "session.event"
         │ params: { sessionId, event }
         │
         ↓
┌──────────────────────────────────────────────────────────────┐
│ SDK - JsonRpcClient (background thread)                      │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ _read_loop()                                           │   │
│ │ - Reads from stdin/socket (blocking)                  │   │
│ │ - Parses Content-Length headers                        │   │
│ │ - Calls _handle_message()                              │   │
│ └────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
         │
         │ call_soon_threadsafe()
         │
         ↓
┌──────────────────────────────────────────────────────────────┐
│ SDK - CopilotClient (event loop)                             │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ handle_notification() callback                         │   │
│ │ - Routes "session.event" to correct session            │   │
│ │ - Converts dict to SessionEvent                        │   │
│ └────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
         │
         │ _dispatch_event()
         │
         ↓
┌──────────────────────────────────────────────────────────────┐
│ SDK - CopilotSession (event loop)                            │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ _dispatch_event() -> calls all registered handlers     │   │
│ └────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
         │
         │ Calls handler(event)
         │
         ↓
┌──────────────────────────────────────────────────────────────┐
│ Your Application                                             │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ def on_event(event):                                   │   │
│ │     if event.type == "assistant.message_delta":       │   │
│ │         print(event.data.delta_content)  # Print chunks    │   │
│ │     elif event.type == "assistant.message":           │   │
│ │         print("Full message received")                │   │
│ │     elif event.type == "session.idle":                │   │
│ │         print("Server done processing")               │   │
│ └────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

## Event Types & Streaming Events

### Session Events (auto-generated from schema)
**Location:** `python/copilot/generated/session_events.py`

The SDK generates strongly-typed event classes from the JSON schema:

```python
# Standard events
ASSISTANT_MESSAGE = "assistant.message"        # Full message completed
ASSISTANT_MESSAGE_DELTA = "assistant.message_delta"  # Streaming chunk
ASSISTANT_REASONING = "assistant.reasoning"    # Full reasoning completed
ASSISTANT_REASONING_DELTA = "assistant.reasoning_delta"  # Streaming chunk
SESSION_IDLE = "session.idle"                  # No more processing
SESSION_ERROR = "session.error"               # Error occurred
SESSION_COMPACTION_START = "session.compaction_start"  # Context compaction
SESSION_COMPACTION_COMPLETE = "session.compaction_complete"
TOOL_CALL = "tool.call"                      # Tool invocation
TOOL_RESULT = "tool.result"                  # Tool result received
```

### Minimal Event Structure

```python
@dataclass
class SessionEvent:
    """Represents a session event with discriminated union based on type"""
    type: SessionEventType  # Enum discriminant
    data: Union[
        AssistantMessageData,
        AssistantMessageDeltaData,
        ToolCallData,
        # ... many more types
    ]
```

---

## Complete Working Example

### Basic Setup with Streaming

```python
import asyncio
from copilot import CopilotClient
from copilot.generated.session_events import SessionEventType

async def main():
    # Create client
    client = CopilotClient()
    await client.start()

    # Create session with streaming enabled
    session = await client.create_session({
        "model": "gpt-4",
        "streaming": True  # Enable message_delta events
    })

    # Subscribe to events
    def on_event(event):
        # Handle different event types
        if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            # Streaming chunk received
            print(event.data.delta_content, end="", flush=True)

        elif event.type == SessionEventType.ASSISTANT_MESSAGE:
            # Full message completed
            print()  # newline
            print(f"Full message: {event.data.content}")

        elif event.type == SessionEventType.SESSION_IDLE:
            # Server done processing
            print("Session idle")

        elif event.type == SessionEventType.SESSION_ERROR:
            print(f"Error: {event.data.message}")

    unsubscribe = session.on(on_event)

    # Send message
    await session.send({"prompt": "Tell me a story about a dragon"})

    # Wait for completion
    await asyncio.sleep(5)

    # Cleanup
    unsubscribe()
    await session.destroy()
    await client.stop()

asyncio.run(main())
```

### Advanced: Real-Time Token Streaming

```python
import asyncio
from copilot import CopilotClient
from copilot.generated.session_events import SessionEventType

class TokenStreamer:
    def __init__(self, session):
        self.session = session
        self.token_buffer = ""
        self.total_tokens = 0
        self.completion_event = asyncio.Event()

    def on_event(self, event):
        if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            # Streaming chunks
            chunk = event.data.delta_content
            self.token_buffer += chunk
            self.total_tokens += 1

            # Process every 5 tokens
            if self.total_tokens % 5 == 0:
                print(f"[{self.total_tokens}] {self.token_buffer}")
                self.token_buffer = ""

        elif event.type == SessionEventType.ASSISTANT_MESSAGE:
            # Full message available
            if self.token_buffer:
                print(f"[Final] {self.token_buffer}")

        elif event.type == SessionEventType.SESSION_IDLE:
            print(f"[Complete] Received {self.total_tokens} tokens")
            self.completion_event.set()

    async def wait_for_completion(self, timeout=60):
        try:
            await asyncio.wait_for(
                self.completion_event.wait(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            print("Timeout waiting for completion")

async def stream_response():
    client = CopilotClient()
    await client.start()

    session = await client.create_session({
        "model": "gpt-4",
        "streaming": True
    })

    streamer = TokenStreamer(session)
    unsubscribe = session.on(streamer.on_event)

    await session.send({"prompt": "Explain quantum computing"})
    await streamer.wait_for_completion()

    unsubscribe()
    await session.destroy()
    await client.stop()

asyncio.run(stream_response())
```

---

## Replicating for Your Personal Application

### Step 1: Protocol Understanding

The Copilot SDK uses **JSON-RPC 2.0** with:
- **Request/Response**: For blocking calls (with `id`)
- **Notifications**: For asynchronous events (no `id`)
- **Content-Length framing**: For stdio transport

### Step 2: Minimal Implementation

If you want to replicate this for your own application:

```python
# 1. Create JSON-RPC connection to Copilot CLI
class RpcConnection:
    def __init__(self, cli_process):
        self.process = cli_process
        self.pending_requests = {}  # id -> Future
        self.notification_handler = None
        self._running = False
        self._loop = None
        self._read_thread = None

    async def start(self):
        """Start background reader thread"""
        self._loop = asyncio.get_running_loop()
        self._running = True
        self._read_thread = threading.Thread(
            target=self._read_loop,
            daemon=True
        )
        self._read_thread.start()

    def _read_loop(self):
        """Background thread: read messages continuously"""
        while self._running:
            msg = self._read_message()  # Blocking read
            if msg:
                self._handle_message(msg)

    def _read_message(self):
        """Read single JSON-RPC message with Content-Length header"""
        # 1. Read Content-Length header
        header = self.process.stdout.readline().decode().strip()
        content_length = int(header.split(":")[1].strip())

        # 2. Read empty line
        self.process.stdout.readline()

        # 3. Read exact content bytes
        data = self.process.stdout.read(content_length)
        return json.loads(data.decode())

    def _handle_message(self, msg):
        """Route message to handler or pending request"""
        if "id" in msg:
            # Response to our request
            future = self.pending_requests.pop(msg["id"], None)
            if future:
                self._loop.call_soon_threadsafe(
                    future.set_result,
                    msg.get("result")
                )
        elif "method" in msg:
            # Notification (streaming event)
            method = msg["method"]
            params = msg.get("params", {})
            self._loop.call_soon_threadsafe(
                self.notification_handler,
                method,
                params
            )

    async def request(self, method, params=None):
        """Send request and wait for response"""
        request_id = str(uuid.uuid4())
        future = self._loop.create_future()
        self.pending_requests[request_id] = future

        await self._send({
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        })

        return await future

    async def _send(self, msg):
        """Send JSON-RPC message with Content-Length header"""
        content = json.dumps(msg).encode()
        header = f"Content-Length: {len(content)}\r\n\r\n".encode()

        self.process.stdin.write(header + content)
        self.process.stdin.flush()


# 2. Create session manager
class MySession:
    def __init__(self, session_id, rpc):
        self.session_id = session_id
        self.rpc = rpc
        self.event_handlers = []

    def on(self, handler):
        """Register event handler"""
        self.event_handlers.append(handler)
        return lambda: self.event_handlers.remove(handler)

    def dispatch_event(self, event):
        """Called when event arrives from CLI"""
        for handler in self.event_handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"Handler error: {e}")

    async def send(self, prompt):
        """Send message to CLI"""
        response = await self.rpc.request(
            "session.send",
            {
                "sessionId": self.session_id,
                "prompt": prompt
            }
        )
        return response["messageId"]


# 3. Create application
class MyApp:
    def __init__(self):
        self.rpc = None
        self.sessions = {}

    async def start(self):
        """Start CLI and connect"""
        process = subprocess.Popen(
            ["copilot", "run"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        self.rpc = RpcConnection(process)

        # Set up notification router
        def route_notification(method, params):
            if method == "session.event":
                session_id = params["sessionId"]
                event = params["event"]
                session = self.sessions.get(session_id)
                if session:
                    session.dispatch_event(event)

        self.rpc.notification_handler = route_notification
        await self.rpc.start()

    async def create_session(self):
        """Create new session"""
        response = await self.rpc.request("session.create", {
            "streaming": True
        })

        session = MySession(response["sessionId"], self.rpc)
        self.sessions[session.session_id] = session
        return session

    async def run(self):
        """Example usage"""
        await self.start()

        session = await self.create_session()

        # Subscribe to events
        def on_event(event):
            if event.get("type") == "assistant.message_delta":
                print(event.get("data", {}).get("content"), end="", flush=True)

        session.on(on_event)

        # Send message
        await session.send("Hello, world!")

        # Wait a bit for events
        await asyncio.sleep(5)

# Run it
async def main():
    app = MyApp()
    await app.run()

asyncio.run(main())
```

### Step 3: Key Design Points for Your Implementation

1. **Threading Model**
   - Background reader thread (blocking I/O)
   - Main asyncio event loop (async application code)
   - Thread-safe communication via `call_soon_threadsafe()`

2. **Message Framing**
   - Content-Length headers (not JSON Lines)
   - Format: `Content-Length: N\r\n\r\n{JSON}`

3. **Request-Response vs Notifications**
   - Requests have `"id"` field (get responses)
   - Notifications have no `"id"` (one-way)
   - Use notifications for streaming events

4. **Event Routing**
   - Central notification handler (CopilotClient)
   - Route to session-specific handlers
   - Session dispatches to subscriber callbacks

5. **Error Handling**
   - Wrap handler calls in try-catch
   - Don't let one handler crash others
   - Handle disconnections gracefully

---

## Performance Characteristics

- **Latency**: < 100ms per event (depends on system load)
- **Throughput**: Multiple events per second (typical: 10-100 events/sec)
- **Memory**: Minimal overhead (event objects are small)
- **Threading**: Single reader thread + main event loop

---

## Common Patterns

### Buffering Chunks
```python
chunks = []
def on_event(event):
    if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
        chunks.append(event.data.delta_content)
    elif event.type == SessionEventType.ASSISTANT_MESSAGE:
        full_message = "".join(chunks)
        # Use full_message
```

### Cancellation
```python
task = asyncio.create_task(session.send(options))
await asyncio.sleep(5)
task.cancel()  # CLI keeps processing, but we stop listening
```

### Timeout with Fallback
```python
try:
    result = await asyncio.wait_for(session.send_and_wait(options), timeout=30)
except asyncio.TimeoutError:
    print("Use cached response or default")
```

---

## Debugging

Enable detailed logging:
```python
client = CopilotClient({
    "log_level": "debug"
})
```

Add tracing to your handlers:
```python
def on_event(event):
    print(f"[{datetime.now().isoformat()}] {event.type}")
    # ... handle event
```

Monitor message traffic:
```python
# In JsonRpcClient._handle_message():
print(f"Message: {json.dumps(message, indent=2)}")
```

---

## Conclusion

The Copilot SDK's streaming implementation combines:
- **JSON-RPC 2.0** for protocol
- **Threading** for non-blocking I/O
- **Async/await** for intuitive application code
- **Event-driven** architecture for real-time updates

You can replicate this pattern for any CLI tool that provides a JSON-RPC interface!
