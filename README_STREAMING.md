# Real-Time Streaming with Copilot CLI - Complete Documentation Index

## Quick Navigation

Choose based on your needs:

### 👶 **I want to use streaming NOW** → [STREAMING_EXAMPLES.md](STREAMING_EXAMPLES.md)
8 ready-to-run examples from basic to advanced:
- ✅ Basic streaming with delta events
- ✅ Token counter with real-time metrics
- ✅ Multiple subscribers
- ✅ Streaming with tool calls
- ✅ Error handling & robustness
- ✅ Concurrent sessions
- ✅ WebSocket integration
- ✅ Context compaction

Just copy-paste and run!

### 🔧 **I want to build my OWN client** → [CUSTOM_CLIENT_IMPLEMENTATION.md](CUSTOM_CLIENT_IMPLEMENTATION.md)
Complete minimal implementation (~300 lines) showing:
- JSON-RPC protocol implementation
- Streaming architecture
- Threading + async patterns
- Extension points (tools, permissions, errors)
- Testing and debugging

### 📚 **I want to understand HOW it works** → [STREAMING_IMPLEMENTATION_GUIDE.md](STREAMING_IMPLEMENTATION_GUIDE.md)
Deep dive into Copilot SDK internals:
- Component architecture
- Event flow diagrams
- Thread safety patterns
- Message framing details
- Performance characteristics

---

## Executive Summary

The **Copilot Python SDK** supports real-time streaming through:

1. **JSON-RPC 2.0** protocol with Content-Length framing
2. **Background thread** for non-blocking I/O from CLI
3. **Asyncio event loop** for application logic
4. **Notification routing** to dispatch events to session handlers
5. **Thread-safe callbacks** using `call_soon_threadsafe()`

### Basic Flow
```
Your app sends prompt
    ↓
SDK sends "session.send" request to CLI
    ↓
CLI processes and sends stream of "session.event" notifications
    ↓
Background reader thread receives each notification
    ↓
Scheduled on event loop → passed to session handler
    ↓
Your callback invoked with event (e.g., message_delta chunk)
    ↓
Repeat until "session.idle" event
```

---

## 🚀 Quick Start (2 minutes)

### Important: Streaming Control
⚠️ **Streaming is controlled per-session**, not at CLI startup. There's no need for `--stream on` when starting Copilot. Just enable it in session config:

```python
session = await client.create_session({"streaming": True})  # ← This is all you need
```

### 1. Install
```bash
pip install -e ".[dev]"
```

### 2. Create `main.py`
```python
import asyncio
from copilot import CopilotClient
from copilot.generated.session_events import SessionEventType

async def main():
    client = CopilotClient()
    await client.start()

    session = await client.create_session({"streaming": True})

    def on_event(event):
        if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            print(event.data.delta_content, end="", flush=True)

    session.on(on_event)
    await session.send({"prompt": "Hello!"})
    await asyncio.sleep(5)

    await session.destroy()
    await client.stop()

asyncio.run(main())
```

### 3. Run
```bash
python main.py
```

Done! You now have real-time streaming! 🎉

---

## 📖 Learning Path

**Beginner:**
1. Read this page
2. Run examples from [STREAMING_EXAMPLES.md](STREAMING_EXAMPLES.md)
3. Modify prompts and event handlers

**Intermediate:**
1. Copy basic example and adapt for your use case
2. Read [STREAMING_IMPLEMENTATION_GUIDE.md](STREAMING_IMPLEMENTATION_GUIDE.md) sections 1-3
3. Add tool definitions and error handling

**Advanced:**
1. Build custom client using [CUSTOM_CLIENT_IMPLEMENTATION.md](CUSTOM_CLIENT_IMPLEMENTATION.md)
2. Implement additional JSON-RPC request handlers
3. Optimize for your specific workload

---

## 🎯 Common Use Cases

### Use Case 1: Real-Time Chat UI
**Goal:** Display response chunks as they arrive

**Solution:**
```python
def on_event(event):
    if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
        # Add chunk to UI
        ui.append_text(event.data.delta_content)
```

**See:** [STREAMING_EXAMPLES.md - Example 1](STREAMING_EXAMPLES.md#example-1-basic-streaming-with-delta-events)

---

### Use Case 2: Server Endpoint
**Goal:** Stream response to HTTP client

**Solution:**
```python
@app.get("/stream")
async def stream(prompt: str):
    def event_generator():
        def on_event(event):
            if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
                yield event.data.delta_content

        session.on(on_event)
        await session.send({"prompt": prompt})

    return StreamingResponse(event_generator())
```

**See:** [STREAMING_EXAMPLES.md - Example 7](STREAMING_EXAMPLES.md#example-7-streaming-to-websocket-client)

---

### Use Case 3: Token-Based Pricing
**Goal:** Count tokens for billing

**Solution:**
```python
def on_event(event):
    if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
        token_count += 1
        # Track for billing
```

**See:** [STREAMING_EXAMPLES.md - Example 2](STREAMING_EXAMPLES.md#example-2-token-counter-with-streaming)

---

### Use Case 4: Multi-Agent System
**Goal:** Handle multiple concurrent streams

**Solution:**
```python
tasks = [
    stream_prompt(client, prompt1),
    stream_prompt(client, prompt2),
    stream_prompt(client, prompt3),
]
results = await asyncio.gather(*tasks)
```

**See:** [STREAMING_EXAMPLES.md - Example 6](STREAMING_EXAMPLES.md#example-6-streaming-responses-to-multiple-users-async)

---

## 🔌 Architecture Components

### **JsonRpcClient** (Protocol Layer)
- Handles JSON-RPC 2.0 framing
- Content-Length based message splitting
- Manages request/response correlation
- Background reader thread for non-blocking I/O

**File:** `python/copilot/jsonrpc.py`

### **CopilotClient** (Session Manager)
- Starts/stops CLI server
- Creates and registers sessions
- Routes notifications to session handlers
- Manages tool/permission request callbacks

**File:** `python/copilot/client.py` (lines 1200-1350 for notification setup)

### **CopilotSession** (Event Subscription)
- Holds event handler subscriptions
- Dispatches events from CLI to handlers
- Sends messages to CLI
- Implements `send_and_wait()` convenience

**File:** `python/copilot/session.py` (lines 200-300 for event dispatch)

### **SessionEvent** (Data Layer)
- Auto-generated strongly-typed event classes
- Discriminated unions based on event type
- Type-safe event handling

**File:** `python/copilot/generated/session_events.py`

---

## 📊 Event Types

### Streaming Events (Real-Time)
- `ASSISTANT_MESSAGE_DELTA` - Chunk of assistant's response
- `ASSISTANT_REASONING_DELTA` - Chunk of reasoning (for models that support it)

### Completion Events
- `ASSISTANT_MESSAGE` - Complete assistant message (after all deltas)
- `ASSISTANT_REASONING` - Complete reasoning

### State Events
- `SESSION_IDLE` - No more processing happening
- `SESSION_ERROR` - Error occurred
- `SESSION_COMPACTION_START` - Context compaction started (infinite sessions)
- `SESSION_COMPACTION_COMPLETE` - Context compaction finished

### Tool Events
- `TOOL_CALL` - Tool was invoked
- `TOOL_RESULT` - Tool result available

**See:** [STREAMING_IMPLEMENTATION_GUIDE.md - Event Types](STREAMING_IMPLEMENTATION_GUIDE.md#event-types--streaming-events)

---

## 🎓 Understanding the Architecture

### Request-Response (Blocking Calls)
```python
# Has "id" in message - expects response
response = await session.send({"prompt": "..."})  # waits for response
```

### Notifications (Streaming Events)
```python
# No "id" in message - one-way streaming
# Events arrive as notifications
def on_event(event):
    # called for each event
```

### The Secret: Threading
```python
# Background thread:
while True:
    msg = stdin.read()  # blocking, but in thread!
    event_loop.call_soon_threadsafe(handler, msg)  # thread-safe

# Main event loop:
async def handler(msg):
    # Process msg asynchronously
```

**Why?** Reading from stdin blocks. We can't block asyncio. So we use a thread!

**See:** [STREAMING_IMPLEMENTATION_GUIDE.md - JsonRpcClient](STREAMING_IMPLEMENTATION_GUIDE.md#1-jsonrpcclient---low-level-communication)

---

## 🐛 Debugging Tips

### Enable Debug Logging
```python
client = CopilotClient({"log_level": "debug"})
```

### Trace Message Flow
```python
# In your event handler:
print(f"[{datetime.now().isoformat()}] {event.type}: {event}")
```

### Monitor Thread Status
```python
import threading
print(f"Threads: {threading.enumerate()}")
```

### Check CLI Logs
```bash
# Check if CLI server is accepting connections
netstat -an | grep 8000
```

---

## ⚡ Performance Best Practices

1. **Don't block in handlers**
   ```python
   # ❌ BAD - blocks the event loop
   def on_event(event):
       time.sleep(1)

   # ✅ GOOD - non-blocking
   async def on_event(event):
       await asyncio.sleep(1)
   ```

2. **Unsubscribe when done**
   ```python
   unsubscribe = session.on(handler)
   # ... use session
   unsubscribe()  # prevents memory leak
   ```

3. **Use concurrent sessions**
   ```python
   # ✅ GOOD - multiple sessions concurrently
   results = await asyncio.gather(
       send_and_wait(session1, prompt1),
       send_and_wait(session2, prompt2),
   )
   ```

4. **Set timeouts**
   ```python
   response = await asyncio.wait_for(
       session.send_and_wait(options),
       timeout=30  # Don't wait forever
   )
   ```

---

## ❓ FAQ - Common Questions

**Q: Do I need to pass `--stream on` when starting the CLI?**

A: **No**. Streaming is controlled per-session, not at CLI startup. Just enable it in the session config:

```python
session = await client.create_session({"streaming": True})
```

The `--stream` CLI flag (if available) would be a global default, but the SDK uses per-session control for flexibility.

**Q: What's the difference between `streaming: True` and `streaming: False`?**

A:
- `streaming: True` → Receive `ASSISTANT_MESSAGE_DELTA` events (chunks) in real-time
- `streaming: False` → Only receive `ASSISTANT_MESSAGE` event (full message) after completion

**Q: Can different sessions have different streaming preferences?**

A: Yes! Each session is independent:

```python
session1 = await client.create_session({"streaming": True})   # Get deltas
session2 = await client.create_session({"streaming": False})  # Get full message only
```

**Q: Do I need to restart the CLI to change streaming mode?**

A: No, just create a new session with the desired config.

**Q: What if I don't specify `streaming` in config?**

A: It defaults to `None` (no streaming), meaning you only get the full message event.

---

## 🆘 Troubleshooting

| Problem | Symptom | Solution |
|---------|---------|----------|
| No response | Prompt sent but no events | Check Copilot CLI is running, check logs |
| Timeout | Times out waiting for session.idle | Increase timeout or check network |
| Memory leak | Memory grows over time | Ensure `unsubscribe()` is called |
| Slow streaming | Events come slowly | Normal behavior, check network latency |
| Connection refused | Can't connect to CLI | Ensure Copilot CLI is installed: `copilot --version` |

---

## 📝 Implementation Checklist

- [ ] Read this page
- [ ] Install copilot SDK: `pip install -e ".[dev]"`
- [ ] Run basic example from STREAMING_EXAMPLES.md
- [ ] Customize example for your use case
- [ ] Add error handling
- [ ] Add tool definitions if needed
- [ ] Test with multiple concurrent sessions
- [ ] Deploy to production

---

## 🔗 Key Files Reference

| File | Purpose | Key Functions |
|------|---------|---|
| `client.py` | Session management | `create_session()`, notification routing |
| `session.py` | Event subscriptions | `on()`, `send()`, `send_and_wait()` |
| `jsonrpc.py` | Protocol implementation | Message framing, thread-safe dispatch |
| `generated/session_events.py` | Event types | `SessionEvent`, `SessionEventType` |

---

## 📞 Getting Help

1. **Examples don't work?** → Check [STREAMING_EXAMPLES.md](STREAMING_EXAMPLES.md)
2. **Want to understand internals?** → Read [STREAMING_IMPLEMENTATION_GUIDE.md](STREAMING_IMPLEMENTATION_GUIDE.md)
3. **Building from scratch?** → See [CUSTOM_CLIENT_IMPLEMENTATION.md](CUSTOM_CLIENT_IMPLEMENTATION.md)
4. **Need specific pattern?** → Search example files for use case

---

## 🎉 Summary

You now have everything you need to:

✅ Use streaming in the Copilot SDK today
✅ Build your own streaming client
✅ Debug issues when they arise
✅ Optimize for your use case

**Start with Example 1 in [STREAMING_EXAMPLES.md](STREAMING_EXAMPLES.md) and go from there!**

