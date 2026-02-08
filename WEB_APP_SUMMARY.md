# Copilot Streaming Web Application

I've created a complete web application that demonstrates the Copilot CLI streaming functionality. Here's what was built:

## 📁 New Files Created

### Backend
- **[app.py](app.py)** - FastAPI web server that:
  - Maintains a persistent connection to Copilot CLI
  - Exposes `/api/chat` endpoint for streaming responses
  - Handles real-time event streaming to the frontend
  - Manages session lifecycle

### Frontend
- **[templates/index.html](templates/index.html)** - Complete web UI featuring:
  - Beautiful gradient-based design
  - Real-time streaming response display
  - Model selection dropdown
  - Usage metrics dashboard
  - Premium quota visualization
  - Responsive layout for desktop and mobile

### Configuration & Scripts
- **[requirements.txt](requirements.txt)** - Python dependencies (FastAPI, Uvicorn)
- **[run.sh](run.sh)** - Easy startup script (just run `./run.sh`)
- **[WEB_APP_README.md](WEB_APP_README.md)** - Comprehensive documentation

## 🚀 Quick Start

```bash
# Option 1: Using the run script
./run.sh

# Option 2: Manual setup
pip install -r requirements.txt
python app.py
```

Then open your browser to **http://localhost:8000**

## 🎨 Features

✨ **Real-time Streaming**
- Watch responses appear character-by-character as they're generated
- Smooth scrolling to latest content

📊 **Usage Metrics Dashboard**
- Token counts (input/output)
- Cache statistics
- Generation cost
- Model information

💎 **Premium Quota Tracking**
- View your premium request entitlements
- Monitor used/remaining requests
- Percentage-based quota display

🎯 **Responsive Design**
- Works on desktop, tablet, and mobile
- Beautiful gradient UI
- Accessible controls

## 🔧 How It Works

1. **User enters a prompt** in the web interface
2. **Backend receives request** and creates a Copilot CLI session
3. **Events stream back** as JSON lines in real-time
4. **Frontend displays** streaming text and metrics
5. **Session completes** and shows final statistics

### Architecture Diagram

```
Browser (HTML/CSS/JS)
       ↓ POST /api/chat
FastAPI Backend (app.py)
       ↓ JSON-RPC
Copilot CLI (streaming_test.py)
       ↓ stdin/stdout
GitHub Copilot
```

## 📡 API Endpoints

### POST /api/chat?prompt=...&model=...
Streams a real-time response as newline-delimited JSON

### GET /api/health
Server health check

## 🎛️ Customization

- **Colors & Styling**: Edit CSS in `templates/index.html`
- **Port**: Modify `uvicorn.run()` in `app.py` (default: 8000)
- **Models**: Add models to the dropdown in `templates/index.html`
- **Timeout**: Adjust in `streaming_test.py`

## 📝 Files Structure

```
copilot_streaming_client/
├── app.py                  # FastAPI backend
├── streaming_test.py       # Copilot CLI client (reused)
├── templates/
│   └── index.html         # Web UI
├── requirements.txt        # Python dependencies
├── run.sh                 # Quick start script
└── WEB_APP_README.md      # Full documentation
```

## 🐛 Usage Tips

- The backend keeps one persistent Copilot CLI connection alive for fast responses
- Each user request creates a temporary session
- Responses timeout after 30 seconds (configurable)
- All streaming events are displayed in real-time

## ✅ What You Can Do

- Type any prompt and send it
- Watch the response stream in real-time
- See token counts and costs updated
- View premium quota information
- Switch between different models
- Use on any device with a browser

Enjoy exploring Copilot's streaming capabilities! 🚀
