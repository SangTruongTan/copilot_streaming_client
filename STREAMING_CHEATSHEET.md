# Streaming Cheat Sheet - Quick Reference

## Installation & Setup (30 seconds)

```bash
# Install
pip install -e ".[dev]"

# Verify Copilot CLI is installed
copilot --version
```

---

## Basic Template (Copy & Run)

```python
import asyncio
from copilot import CopilotClient
from copilot.generated.session_events import SessionEventType

async def main():
    # 1. Connect
    client = CopilotClient()
    await client.start()

    # 2. Create session with streaming
    session = await client.create_session({"streaming": True})

    # 3. Define event handler
    def on_event(event):
        if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            print(event.data.delta_content, end="", flush=True)
        elif event.type == SessionEventType.SESSION_IDLE:
            print("\n[Done]")

    # 4. Subscribe
    unsubscribe = session.on(on_event)

    # 5. Send prompt
    await session.send({"prompt": "Your question here"})

    # 6. Wait for response
    await asyncio.sleep(5)

    # 7. Cleanup
    unsubscribe()
    await session.destroy()
    await client.stop()

asyncio.run(main())
```

---

## Event Types Quick Lookup

```python
from copilot.generated.session_events import SessionEventType

# Streaming (real-time chunks)
SessionEventType.ASSISTANT_MESSAGE_DELTA      # Chunk of response
SessionEventType.ASSISTANT_REASONING_DELTA    # Chunk of reasoning

# Completion
SessionEventType.ASSISTANT_MESSAGE            # Full response
SessionEventType.ASSISTANT_REASONING          # Full reasoning

# State
SessionEventType.SESSION_IDLE                 # Processing complete
SessionEventType.SESSION_ERROR                # Error occurred
SessionEventType.TOOL_CALL                    # Tool invoked
SessionEventType.TOOL_RESULT                  # Tool result received

# Advanced
SessionEventType.SESSION_COMPACTION_START     # Context compressing
SessionEventType.SESSION_COMPACTION_COMPLETE  # Context compressed
```

---

## Common Patterns

### Pattern 1: Collect All Chunks
```python
chunks = []

def on_event(event):
    if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
        chunks.append(event.data.content)
    elif event.type == SessionEventType.SESSION_IDLE:
        full_text = "".join(chunks)
        # use full_text
```

### Pattern 2: Count Tokens
```python
token_count = 0

def on_event(event):
    if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
        token_count += 1
```

### Pattern 3: Handle Errors
```python
error_msg = None

def on_event(event):
    if event.type == SessionEventType.SESSION_ERROR:
        error_msg = event.data.message
    elif event.type == SessionEventType.SESSION_IDLE:
        if error_msg:
            print(f"Failed: {error_msg}")
```

### Pattern 4: Wait for Completion
```python
done = asyncio.Event()

def on_event(event):
    if event.type == SessionEventType.SESSION_IDLE:
        done.set()

session.on(on_event)
await session.send({"prompt": "..."})
await asyncio.wait_for(done.wait(), timeout=30)
```

### Pattern 5: Multiple Subscribers
```python
handler1 = lambda e: print("H1:", e.type)
handler2 = lambda e: print("H2:", e.type)

unsub1 = session.on(handler1)
unsub2 = session.on(handler2)

# Both handlers called for each event

unsub1()  # Unsubscribe handler1
unsub2()  # Unsubscribe handler2
```

### Pattern 6: Concurrent Sessions
```python
async def send_prompt(client, prompt):
    session = await client.create_session({"streaming": True})
    # ... handle events ...
    await session.destroy()
    return response

results = await asyncio.gather(
    send_prompt(client, "Q1"),
    send_prompt(client, "Q2"),
    send_prompt(client, "Q3"),
)
```

---

## Session Config Options

```python
# Note: Streaming is per-session, controlled here (not at CLI startup)
session = await client.create_session({
    "model": "gpt-4",           # or "gpt-5", "claude-sonnet-4.5"
    "streaming": True,           # Enable delta events (per-session control)
    "tools": [tool1, tool2],     # Custom tools
    "reasoning_effort": "medium", # "low", "medium", "high", "xhigh"
    "infinite_sessions": {       # Context compaction
        "enabled": True,
        "background_compaction_threshold": 0.5,
        "buffer_exhaustion_threshold": 0.8,
    }
})
```

---

## Message Options

```python
# Simple prompt
await session.send({"prompt": "What is AI?"})

# With attachments
await session.send({
    "prompt": "Analyze this code",
    "attachments": [
        {"type": "file", "path": "./main.py"}
    ]
})

# With selection (code snippet)
await session.send({
    "prompt": "Optimize this function",
    "attachments": [
        {
            "type": "selection",
            "filePath": "./main.py",
            "displayName": "fibonacci function",
            "selection": {
                "start": {"line": 10, "character": 0},
                "end": {"line": 15, "character": 0}
            }
        }
    ]
})
```

---

## Error Handling Patterns

### Try-Catch Example
```python
try:
    client = CopilotClient()
    await client.start()
    session = await client.create_session()
    await session.send({"prompt": "..."})
    await asyncio.sleep(5)
except asyncio.TimeoutError:
    print("Timeout waiting for response")
except Exception as e:
    print(f"Error: {e}")
finally:
    await client.force_stop()
```

### Timeout with Fallback
```python
try:
    response = await asyncio.wait_for(
        session.send_and_wait({"prompt": "..."}),
        timeout=30
    )
except asyncio.TimeoutError:
    response = None
    print("Using cached/default response")
```

### Handler Error Isolation
```python
def safe_on_event(event):
    try:
        process_event(event)
    except Exception as e:
        print(f"Handler error (won't crash stream): {e}")
        # Don't re-raise - let stream continue
```

---

## Testing Helpers

```python
# Test if streaming works
async def test_streaming():
    client = CopilotClient()
    await client.start()

    session = await client.create_session({"streaming": True})

    chunks = []
    done = asyncio.Event()

    def handler(event):
        if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            chunks.append(event.data.delta_content)
        elif event.type == SessionEventType.SESSION_IDLE:
            done.set()

    session.on(handler)
    await session.send({"prompt": "test"})

    try:
        await asyncio.wait_for(done.wait(), timeout=10)
        assert len(chunks) > 0, "No chunks received"
        print(f"✓ Streaming works ({len(chunks)} chunks)")
    except asyncio.TimeoutError:
        print("✗ Timeout - streaming may not be working")
    finally:
        await client.force_stop()
```

---

## Environment Variables

```bash
# CLI path (if not in PATH)
export COPILOT_CLI_PATH=/usr/local/bin/copilot

# GitHub token
export GITHUB_TOKEN=ghp_xxx...

# Port for TCP mode
export COPILOT_PORT=8000
```

---

## Common Config Patterns

### Production Setup
```python
client = CopilotClient({
    "cli_path": "/usr/bin/copilot",
    "log_level": "error",
    "auto_start": True,
    "auto_restart": True,
})
```

### Development Setup
```python
client = CopilotClient({
    "log_level": "debug",      # More logging
    "use_stdio": True,          # Easier debugging
})
```

### Remote Server
```python
client = CopilotClient({
    "cli_url": "192.168.1.100:8000",  # Connect to remote server
    "log_level": "info"
})
```

### Custom Auth
```python
client = CopilotClient({
    "github_token": "ghp_xxx...",  # Use specific token
    "use_logged_in_user": False     # Don't fall back to local user
})
```

---

## API Reference (Session)

```python
session = await client.create_session(...)

# Send & Stream
message_id = await session.send({"prompt": "..."})

# Send & Wait for Completion
response = await session.send_and_wait(
    {"prompt": "..."},
    timeout=60
)

# Subscribe to Events
unsubscribe = session.on(lambda event: ...)

# Get Session ID
sid = session.session_id

# Get Workspace Path (infinite sessions only)
path = session.workspace_path  # or None

# Destroy Session
await session.destroy()
```

---

## API Reference (Client)

```python
client = CopilotClient(options)

# Connection
await client.start()        # Start CLI server and connect
await client.stop()         # Graceful shutdown
await client.force_stop()   # Force shutdown (no cleanup)

# Sessions
session = await client.create_session(config)
session = await client.resume_session(session_id)

# Status
state = client.get_state()  # "disconnected", "connected", etc.

# Models
models = await client.list_models()
status = await client.get_status()

# Session Management (TUI mode)
session_id = await client.get_foreground_session_id()
await client.set_foreground_session_id(session_id)
```

---

## Event Data Accessors

```python
# Delta event
event.type                          # SessionEventType
event.data.delta_content            # str (the chunk)

# Message event
event.data.content                  # str (full message)
event.data.message_id              # str

# Error event
event.data.message                  # str (error message)
event.data.error_code              # int (optional)

# Tool call event
event.data.name                     # str (tool name)
event.data.arguments                # dict (parameters)
event.data.tool_call_id            # str

# Compaction event
event.data.success                  # bool
event.data.tokens_removed          # int (or None)
```

---

## Debugging Commands

```bash
# Check CLI version
copilot --version

# Start CLI in server mode (stdio - auto-selected by SDK)
copilot --headless --no-auto-update --stdio

# Start CLI in TCP mode (port 8000)
copilot --headless --no-auto-update --port 8000

# Connect to specific server
cli_url=localhost:8000

# Check network connectivity
curl http://localhost:8000/health

# Monitor process
ps aux | grep copilot
```

---

## Performance Metrics

| Metric | Typical Value |
|--------|---------------|
| Message latency | 10-50ms |
| Token throughput | 20-100 tokens/sec |
| Session creation time | 100-500ms |
| Connection setup time | 1-2 sec |
| Memory per session | ~50KB |
| Concurrent sessions | 10-100 (depends on rate limits) |

---

## Gotchas & Caveats

⚠️ **Always unsubscribe**
```python
# ❌ BAD - memory leak
session.on(my_handler)

# ✅ GOOD - clean up
unsubscribe = session.on(my_handler)
unsubscribe()  # or: unsubscribe = None
```

⚠️ **Don't block in handlers**
```python
# ❌ BAD - blocks event loop
def on_event(event):
    time.sleep(1)  # BLOCKS!

# ✅ GOOD - non-blocking
def on_event(event):
    asyncio.create_task(async_work())
```

⚠️ **Session config is immutable after creation**
```python
# ❌ BAD - can't change after creation
session = await client.create_session({"model": "gpt-4"})
# Later... no way to change to "gpt-5"

# ✅ GOOD - create new session if needed
new_session = await client.create_session({"model": "gpt-5"})
```

⚠️ **Streaming requires explicit opt-in**
```python
# ❌ BAD - no delta events
session = await client.create_session()

# ✅ GOOD - get delta events
session = await client.create_session({"streaming": True})
```

⚠️ **Don't add `--stream` CLI flag at startup**
- Streaming is controlled per-session, not at CLI level
- Just enable it in session config: `await client.create_session({"streaming": True})`
- Different sessions can have different streaming preferences

⚠️ **Content-Length framing is strict**
- SDK only works with Content-Length (not JSON Lines)
- Message boundaries are exact byte counts
- Keep-alive required for long streams

---

## Quick Troubleshooting

**No events received?**
```python
# Check 1: Streaming enabled?
session = await client.create_session({"streaming": True})

# Check 2: Handler registered?
unsubscribe = session.on(my_handler)

# Check 3: Handler called?
def my_handler(event):
    print(f"Event received: {event.type}")  # Add this
```

**Connection refused?**
```bash
# Check if CLI is installed
which copilot
copilot --version

# Check if port is open (TCP mode)
netstat -an | grep 8000
```

**Timeout waiting for response?**
```python
# Check 1: Longer timeout?
await asyncio.wait_for(done.wait(), timeout=60)

# Check 2: Event loop blocking?
# Make sure no blocking code in handlers

# Check 3: Wrong session ID?
# Check session.session_id is correct
```

---

## Minimal vs Full SDKs

### Minimal Client (for study)
- ~300 lines total
- Only essentials: JSON-RPC, threading, routing
- Good for learning
- **File:** [CUSTOM_CLIENT_IMPLEMENTATION.md](CUSTOM_CLIENT_IMPLEMENTATION.md)

### Production SDK (this repo)
- 1500+ lines with full features
- Tools, permissions, hooks, compaction
- Type safety and error handling
- Infinite sessions support

---

## Next Steps

1. Copy the basic template above
2. Run it with your own prompt
3. Check [STREAMING_EXAMPLES.md](STREAMING_EXAMPLES.md) for your use case
4. Read [STREAMING_IMPLEMENTATION_GUIDE.md](STREAMING_IMPLEMENTATION_GUIDE.md) if needed

---

## Useful Links

- **Examples:** [STREAMING_EXAMPLES.md](STREAMING_EXAMPLES.md)
- **Deep Dive:** [STREAMING_IMPLEMENTATION_GUIDE.md](STREAMING_IMPLEMENTATION_GUIDE.md)
- **Build Custom:** [CUSTOM_CLIENT_IMPLEMENTATION.md](CUSTOM_CLIENT_IMPLEMENTATION.md)
- **Master Index:** [README_STREAMING.md](README_STREAMING.md)

