# Copilot Streaming Web Demo

A modern web application demonstrating real-time streaming responses from GitHub Copilot CLI.

## Features

- 🚀 **Real-time Streaming**: Watch responses appear character-by-character as they're generated
- 📊 **Usage Metrics**: View token counts, costs, and cache statistics
- 💎 **Premium Quota Tracking**: Monitor your premium request quotas
- 🎨 **Beautiful UI**: Modern gradient design with smooth animations
- ⚡ **Fast & Responsive**: Built with FastAPI and vanilla JavaScript

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Web Server

```bash
python app.py
```

The server will start on `http://localhost:8000`

### 3. Open in Browser

Navigate to `http://localhost:8000` and start chatting!

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Browser (Frontend)                    │
│  • Input form for prompts                               │
│  • Real-time streaming display                          │
│  • Usage metrics visualization                          │
└────────────────┬────────────────────────────────────────┘
                 │ HTTP POST /api/chat (streaming)
┌────────────────▼────────────────────────────────────────┐
│                FastAPI Backend (app.py)                 │
│  • Manages Copilot CLI connection                       │
│  • Creates streaming sessions                           │
│  • Streams events as JSON lines                         │
└────────────────┬────────────────────────────────────────┘
                 │ JSON-RPC messages
┌────────────────▼────────────────────────────────────────┐
│            Copilot CLI (streaming_test.py)              │
│  • JSON-RPC client                                      │
│  • Session management                                   │
│  • Event streaming                                      │
└────────────────┬────────────────────────────────────────┘
                 │ stdin/stdout
┌────────────────▼────────────────────────────────────────┐
│          GitHub Copilot CLI (copilot binary)            │
│  • Copilot AI model                                     │
│  • Authentication & API calls                           │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User sends prompt** → HTML form posts to `/api/chat`
2. **Backend creates session** → Calls Copilot CLI via JSON-RPC
3. **Events stream back** → Backend sends events as JSON lines
4. **Frontend displays** → JavaScript renders streaming content in real-time
5. **Metrics displayed** → Usage, quota, and cost info shown after completion

## API Endpoints

### POST /api/chat

Stream a conversation response.

**Query Parameters:**
- `prompt` (string, required): The user's message
- `model` (string, optional): Model to use (default: `gpt-4.1`)

**Response:**
Streaming response with newline-delimited JSON (NDJSON) events:

```json
{"type":"assistant.message_delta","data":{"deltaContent":" Hello"},"timestamp":1707425123.456}
{"type":"assistant.message_delta","data":{"deltaContent":" there"},"timestamp":1707425123.457}
{"type":"session.usage","data":{"inputTokens":15,"outputTokens":2,"cost":0.000015},"timestamp":1707425124.0}
{"type":"session.idle","data":{},"timestamp":1707425124.1}
```

### GET /

Serve the web interface.

### GET /api/health

Health check endpoint.

**Response:**
```json
{"status": "ok"}
```

## Event Types

The streaming response includes these event types:

| Event Type | Description |
|------------|-------------|
| `assistant.message_delta` | Streaming text chunk |
| `assistant.message` | Complete message (end of streaming) |
| `session.usage` | Token and cost metrics |
| `session.idle` | Session finished processing |
| `session.event` | Generic session event |

## Models

The application supports these models:

- `gpt-4.1` (default) - Latest GPT-4 model
- `gpt-4` - GPT-4 model
- `claude-3.5-sonnet` - Claude 3.5 Sonnet model

## Customization

### Styling

Edit `templates/index.html` to customize colors, fonts, or layout. The CSS is all in the `<style>` tag.

### Backend Configuration

Edit `app.py` to:
- Change the default port (default: 8000)
- Adjust streaming timeout (default: 30 seconds)
- Modify event handling logic

## Troubleshooting

### "Failed to connect to server"

Make sure Copilot CLI is installed and authenticated:

```bash
copilot auth login
```

### "Session timeout"

If responses take longer than 30 seconds, the request will timeout. You can adjust the timeout in `streaming_test.py` by modifying the `request` method's `timeout` parameter.

### Empty responses

Check that:
- Copilot CLI is properly authenticated
- You have API credits/quota available
- Network connection is stable

## Files

- `app.py` - FastAPI backend server
- `templates/index.html` - Web interface (HTML/CSS/JavaScript)
- `streaming_test.py` - Copilot CLI streaming client
- `requirements.txt` - Python dependencies

## Performance Tips

- The backend maintains a persistent connection to Copilot CLI for faster responses
- Streaming events are buffered and sent immediately for real-time display
- Multiple concurrent requests are supported (one session per request)
- Frontend auto-scrolls to show latest content

## License

MIT
