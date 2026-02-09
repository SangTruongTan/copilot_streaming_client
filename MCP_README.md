# MCP Tool Support - System Information

This demo now includes **Model Context Protocol (MCP)** tool support with a simple system information server.

## What's Included

### MCP Server (`mcp_server.py`)

A minimal MCP server that provides 4 system information tools:

1. **`get_cpu_info`** - Get CPU usage, core count, frequency, and processor details
2. **`get_memory_info`** - Get RAM usage (total, available, used, percentage)
3. **`get_disk_info`** - Get disk storage usage (total, used, free, percentage)
4. **`get_system_info`** - Get platform info, hostname, and system uptime

### Configuration (`mcp_config.json`)

Simple configuration file that tells Copilot CLI how to start the MCP server:

```json
{
  "mcpServers": {
    "system-info": {
      "command": "python3",
      "args": ["mcp_server.py"],
      "env": {}
    }
  }
}
```

## How It Works

1. **Copilot CLI** starts the MCP server as a subprocess
2. The MCP server registers its tools (get_cpu_info, etc.)
3. When you ask about system information, **Copilot automatically calls the appropriate tools**
4. Tool calls and results are streamed back as events
5. Both the CLI demo and web UI display tool calls in real-time

## Running the Demo

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This includes `psutil` for system information gathering.

### 2. CLI Demo

```bash
python3 streaming_test.py
```

Ask questions like:
- "What's my current CPU usage?"
- "How much memory am I using?"
- "Check my system information and disk space"

You'll see:
```
[🔧 Tool Call] get_cpu_info
[✓ Tool Result] get_cpu_info
   {
     "usage_percent": 15.3,
     "core_count": 8,
     ...
   }
```

### 3. Web Demo

```bash
python3 app.py
```

Open http://localhost:8000 and ask about system information. Tool calls appear as blue boxes, results as green boxes.

## How MCP Tools Are Triggered

The Copilot CLI is started with the `--additional-mcp-config` flag:

```python
subprocess.Popen([
    "copilot", "--headless", "--no-auto-update", "--stdio",
    "--additional-mcp-config", "mcp_config.json"
])
```

When the model decides a tool is needed:
1. `tool.call` event is sent with tool name and arguments
2. MCP server executes the tool
3. `tool.result` event is sent with the output
4. Model uses the result to form its response

## Event Types

New event types for tool calling:

- **`tool.call`** - Tool is being invoked
  ```json
  {
    "type": "tool.call",
    "data": {
      "name": "get_cpu_info",
      "arguments": {}
    }
  }
  ```

- **`tool.result`** - Tool execution completed
  ```json
  {
    "type": "tool.result",
    "data": {
      "name": "get_cpu_info",
      "result": {
        "content": [
          {
            "type": "text",
            "text": "{\"usage_percent\": 15.3, ...}"
          }
        ]
      }
    }
  }
  ```

## Creating Your Own MCP Server

The included server is extremely simple (< 300 lines). To add your own tools:

1. **Define the tool function:**
   ```python
   def my_custom_tool(arg1, arg2):
       # Your logic here
       return {"result": "data"}
   ```

2. **Register in the tools dict:**
   ```python
   self.tools = {
       "my_custom_tool": {
           "name": "my_custom_tool",
           "description": "What this tool does",
           "inputSchema": {
               "type": "object",
               "properties": {
                   "arg1": {"type": "string"},
                   "arg2": {"type": "number"}
               }
           }
       }
   }
   ```

3. **Handle in tools/call:**
   ```python
   elif tool_name == "my_custom_tool":
       result = my_custom_tool(
           params.get("arg1"),
           params.get("arg2")
       )
   ```

That's it! The Copilot model will automatically discover and use your tools when appropriate.

## Testing Tool Calls

Try these prompts:

- "What's my CPU usage right now?"
- "How much RAM do I have?"
- "Show me my disk space"
- "Give me a full system report"
- "Is my system running slow? Check CPU and memory"

The model will intelligently decide which tools to call and combine the results in its response.

## Architecture

```
User → Copilot CLI → MCP Server
         ↓              ↓
      (streaming)   (tool execution)
         ↓              ↓
    Your App ← tool.call + tool.result events
```

All tool calls happen asynchronously through the same streaming event system!
