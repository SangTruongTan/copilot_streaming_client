# MCP Tool Support Demo Guide

This demo showcases **real-time streaming with MCP tool support** using the GitHub Copilot CLI.

## What You'll See

When you ask about system information, Copilot will:
1. 🤔 Understand you want system data
2. 🔧 Automatically call MCP tools (get_cpu_info, get_memory_info, etc.)
3. ✅ Receive tool results in real-time
4. 💬 Use that data to form a helpful response

All of this streams back to you in real-time!

## Quick Start

### Option 1: CLI Demo (Terminal)

```bash
# Run the CLI demo
python3 streaming_test.py
```

**Default prompt:** "What's my current system information? Check CPU, memory, and disk usage."

You'll see streaming output like:
```
[🔧 Tool Call] get_cpu_info
[✓ Tool Result] get_cpu_info
   {
     "usage_percent": 15.3,
     "core_count": 8,
     ...
   }

[🔧 Tool Call] get_memory_info
[✓ Tool Result] get_memory_info
   ...

Your system is running well with 15.3% CPU usage...
```

### Option 2: Web Demo (Browser)

```bash
# Start the web server
python3 app.py
```

Then open: **http://localhost:8000**

Try asking:
- "What's my CPU usage?"
- "How much memory am I using?"
- "Show me my disk space"
- "Give me a full system report"

Tool calls appear as **blue boxes** 🟦, results as **green boxes** 🟩.

## Example Prompts to Try

### Basic System Checks
- "What's my current CPU usage?"
- "How much RAM do I have?"
- "Check my disk space"
- "What's my system uptime?"

### Combined Queries
- "Give me a full system report"
- "Is my system running slow? Check CPU and memory"
- "What's taking up space on my disk and how much memory is free?"

### Contextual Questions
- "I'm experiencing lag. Can you check what might be causing it?"
- "Should I worry about my system resources?"
- "Compare my CPU and memory usage"

Copilot will intelligently decide which tools to use!

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Your Application (streaming_test.py or app.py)        │
│  - Subscribes to session events                         │
│  - Displays tool.call and tool.result events            │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────────────┐
│  Copilot CLI (--additional-mcp-config mcp_config.json)  │
│  - Manages MCP server lifecycle                         │
│  - Routes tool requests                                 │
│  - Streams events back to your application              │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ↓
┌─────────────────────────────────────────────────────────┐
│  MCP Server (mcp_server.py)                             │
│  - Registers 4 system info tools                        │
│  - Executes tools when called                           │
│  - Returns results to Copilot CLI                       │
└─────────────────────────────────────────────────────────┘
```

### Event Flow

1. **User:** "What's my CPU usage?"
2. **Copilot:** Analyzes query → Decides to call `get_cpu_info`
3. **Event:** `tool.call` → `{"name": "get_cpu_info"}`
4. **MCP Server:** Executes tool → Gathers CPU data
5. **Event:** `tool.result` → `{"name": "get_cpu_info", "result": {...}}`
6. **Copilot:** Uses result → Generates response
7. **Event:** `assistant.message_delta` → Streams response chunks
8. **Event:** `session.idle` → Response complete

All events stream in **real-time** through the JSON-RPC connection!

## Files Explained

### Core Files

- **`mcp_server.py`** - Simple MCP server with 4 system info tools
- **`mcp_config.json`** - Configuration file pointing to the MCP server
- **`streaming_test.py`** - CLI demo with tool event handling
- **`app.py`** - Web server with tool event support
- **`templates/index.html`** - Web UI with tool visualization

### Documentation

- **`MCP_README.md`** - Detailed MCP integration guide
- **`DEMO_GUIDE.md`** - This file
- **`STREAMING_IMPLEMENTATION_GUIDE.md`** - Deep dive into streaming architecture

## MCP Tools Available

### 1. `get_cpu_info`
Returns CPU usage percentage, core count, frequency, and processor type.

**Example Result:**
```json
{
  "usage_percent": 23.5,
  "core_count": 8,
  "frequency_mhz": 2600.0,
  "processor": "x86_64"
}
```

### 2. `get_memory_info`
Returns memory usage in GB and percentage.

**Example Result:**
```json
{
  "total_gb": 16.0,
  "available_gb": 8.5,
  "used_gb": 7.5,
  "percent_used": 46.9
}
```

### 3. `get_disk_info`
Returns disk usage for root partition.

**Example Result:**
```json
{
  "total_gb": 500.0,
  "used_gb": 350.0,
  "free_gb": 150.0,
  "percent_used": 70.0
}
```

### 4. `get_system_info`
Returns platform info, hostname, and uptime.

**Example Result:**
```json
{
  "platform": "Linux",
  "platform_release": "6.8.0-58-generic",
  "architecture": "x86_64",
  "hostname": "dev-machine",
  "uptime_seconds": 442146,
  "uptime_readable": "5 days, 2:49:06"
}
```

## Customizing the Demo

### Change the Default Prompt

Edit [streaming_test.py](streaming_test.py#L470):

```python
await session.send("YOUR CUSTOM PROMPT HERE")
```

### Add More Tools

1. Add your function in `mcp_server.py`:
   ```python
   def my_tool():
       return {"custom": "data"}
   ```

2. Register in `self.tools` dict

3. Handle in `tools/call` method

4. Copilot automatically discovers and uses it!

### Change Models

The demo defaults to `gpt-4.1`. To use premium models:

**CLI:**
```python
session = await client.create_session(model="claude-sonnet-4.5")
```

**Web UI:**
Use the dropdown to select models.

## Troubleshooting

### "ModuleNotFoundError: No module named 'psutil'"

Install psutil:
```bash
pip install psutil
# or
pip install --break-system-packages psutil
```

### "Failed to connect to Copilot CLI"

Make sure you have:
1. Copilot CLI installed: `copilot --version`
2. Authenticated: `copilot auth`
3. MCP config file in the same directory

### Tools Not Being Called

Try more explicit prompts:
- ❌ "Tell me about my computer"
- ✅ "Check my CPU usage right now"

The model decides when tools are appropriate!

### Web Server Issues

Check if port 8000 is available:
```bash
lsof -i :8000
```

Change port in `app.py` if needed.

## Next Steps

1. **Run the demos** - See streaming + MCP in action
2. **Try different prompts** - Experiment with how the model uses tools
3. **Add custom tools** - Build your own MCP server
4. **Read the guides** - Deep dive into implementation details

## Resources

- **MCP Specification:** https://modelcontextprotocol.io/
- **Copilot CLI Docs:** GitHub Copilot documentation
- **Implementation Guide:** [STREAMING_IMPLEMENTATION_GUIDE.md](STREAMING_IMPLEMENTATION_GUIDE.md)
- **MCP Integration:** [MCP_README.md](MCP_README.md)

## Demo Flow Visualization

```
User: "What's my system info?"
   ↓
[assistant.message_delta] "Let"
[assistant.message_delta] " me"
[assistant.message_delta] " check"
   ↓
[tool.call] get_cpu_info
[tool.result] {"usage_percent": 15.3, ...}
   ↓
[tool.call] get_memory_info
[tool.result] {"total_gb": 16.0, ...}
   ↓
[tool.call] get_system_info
[tool.result] {"platform": "Linux", ...}
   ↓
[assistant.message_delta] "Your"
[assistant.message_delta] " system"
[assistant.message_delta] " is..."
   ↓
[session.idle] Done!
```

Every event streams in real-time! 🚀

---

**Ready to see it in action?** Run `python3 streaming_test.py` or `python3 app.py`!
