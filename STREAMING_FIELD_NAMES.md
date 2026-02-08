# Streaming Field Names - Key Reference

## Critical Finding 🔑

When working with **streaming delta events** in Copilot SDK, the field name **differs by transport**:

### Python SDK (Generated Events)
For `assistant.message_delta` and `assistant.reasoning_delta` events:
```python
# ✅ CORRECT - Use snake_case
event.data.delta_content

# ❌ DO NOT USE
event.data.content
```

### Raw JSON-RPC Protocol (HTTP/Stdio)
When implementing a custom client:
```json
{
  "type": "assistant.message_delta",
  "data": {
    "deltaContent": "chunk text here",
    "messageId": "...",
    "totalResponseSizeBytes": ...
  }
}
```

### .NET SDK
```csharp
// ✅ CORRECT - PascalCase
delta.Data.DeltaContent

// Event types:
AssistantMessageDeltaEvent
AssistantReasoningDeltaEvent
```

### Go SDK
```go
// Streaming chunks available via delta events
```

### Node.js SDK
```typescript
// Check generated types in @github/copilot
```

## Why This Matters

- **Python SDK** auto-generates event classes that convert JSON `deltaContent` → Python `delta_content` (snake_case convention)
- **Custom JSON-RPC clients** work with raw JSON field names (camelCase)
- **.NET SDK** follows PascalCase naming conventions

## Common Mistakes

❌ **Mistake 1:** Using `event.data.content` in Python
```python
# WRONG - this field doesn't exist in delta events
chunk = event.data.content  # AttributeError!
```

✅ **Correct:**
```python
chunk = event.data.delta_content
```

❌ **Mistake 2:** Looking for `content` in JSON-RPC messages
```python
# WRONG - RAW JSON uses camelCase
deltaContent = event.get("data", {}).get("content")  # Returns None!
```

✅ **Correct:**
```python
deltaContent = event.get("data", {}).get("deltaContent")
```

## Event Field Reference

### Delta Events (`assistant.message_delta`, `assistant.reasoning_delta`)
| Language | Streaming Field | Full Response Field |
|----------|-----------------|---------------------|
| Python SDK | `delta_content` | `content` (in `assistant.message`) |
| JSON-RPC | `deltaContent` | `content` (in `assistant.message`) |
| .NET | `DeltaContent` | `Content` (in message event) |

### How to Accumulate Streaming Chunks

```python
# Python SDK
full_response = ""
def on_event(event):
    if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
        full_response += event.data.delta_content  # ← delta_content
    elif event.type == SessionEventType.ASSISTANT_MESSAGE:
        print(full_response)  # Full response in final event
```

```python
# Custom JSON-RPC Client
full_response = ""
def handle_event(event_dict):
    if event_dict.get("type") == "assistant.message_delta":
        full_response += event_dict.get("data", {}).get("deltaContent", "")
    elif event_dict.get("type") == "assistant.message":
        print(full_response)
```

## Testing Your Streaming Implementation

Quick test to verify field names:
```python
import asyncio
from copilot import CopilotClient
from copilot.generated.session_events import SessionEventType

async def test_streaming():
    client = CopilotClient()
    await client.start()

    session = await client.create_session({"streaming": True})

    chunks_received = []

    def on_event(event):
        if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            # This should work:
            chunk = event.data.delta_content
            chunks_received.append(chunk)
            print(f"Chunk #{len(chunks_received)}: {repr(chunk[:30])}")

    session.on(on_event)
    await session.send({"prompt": "Say 'hello world' in one sentence"})

    await asyncio.sleep(5)

    print(f"✓ Received {len(chunks_received)} streaming chunks")
    print(f"Full response: {''.join(chunks_received)}")

    await session.destroy()
    await client.stop()

asyncio.run(test_streaming())
```

## Documentation Updates

All streaming documentation has been updated to use correct field names:
- [STREAMING_EXAMPLES.md](STREAMING_EXAMPLES.md) - 8 working examples
- [STREAMING_IMPLEMENTATION_GUIDE.md](STREAMING_IMPLEMENTATION_GUIDE.md) - Deep technical explanation
- [CUSTOM_CLIENT_IMPLEMENTATION.md](CUSTOM_CLIENT_IMPLEMENTATION.md) - Minimal 300-line implementation
- [README_STREAMING.md](README_STREAMING.md) - Master reference
- [STREAMING_CHEATSHEET.md](STREAMING_CHEATSHEET.md) - Quick lookup table
