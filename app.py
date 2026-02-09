#!/usr/bin/env python3
"""
Web application for Copilot CLI streaming demo
"""

import asyncio
import json
import subprocess
import threading
import time
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from streaming_test import StreamingClient, StreamingSession

# ============================================================================
# GLOBAL STATE
# ============================================================================

app = FastAPI()
client: Optional[StreamingClient] = None
startup_lock = asyncio.Lock()


async def get_client() -> StreamingClient:
    """Get or create the global streaming client (lazy initialization)"""
    global client

    async with startup_lock:
        if client is None:
            # Create client with MCP support
            client = StreamingClient()
            await client.start()

    return client


@app.on_event("shutdown")
async def shutdown():
    """Stop client on shutdown"""
    global client
    if client:
        await client.stop()


# ============================================================================
# ROUTES
# ============================================================================

@app.get("/")
async def index():
    """Serve the frontend"""
    return FileResponse("templates/index.html", media_type="text/html")


@app.post("/api/chat")
async def chat(prompt: str, model: str = "gpt-4.1") -> StreamingResponse:
    """
    Chat endpoint that streams responses in real-time

    Query parameters:
    - prompt: The user's message
    - model: The model to use (default: gpt-4.1)
    """

    if not prompt or not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    try:
        client = await get_client()
        session = await client.create_session(model=model, streaming=True)

        return StreamingResponse(
            stream_chat_events(session, prompt.strip()),
            media_type="application/x-ndjson"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def stream_chat_events(session: StreamingSession, prompt: str) -> AsyncGenerator[str, None]:
    """Stream chat events as JSON lines"""

    events_buffer = []
    session_idle = asyncio.Event()

    def on_event(event: dict):
        nonlocal session_idle
        event_type = event.get("type", "")
        event_data = event.get("data", {})

        # Add timestamp
        event["timestamp"] = time.time()

        # Track when session becomes idle
        if event_type == "session.idle":
            session_idle.set()

        events_buffer.append(event)

    # Subscribe to events
    unsubscribe = session.on(on_event)

    try:
        # Send the prompt
        await session.send(prompt)

        # Stream events as they arrive
        last_sent = 0
        while True:
            # Check if we have new events to send
            if len(events_buffer) > last_sent:
                for i in range(last_sent, len(events_buffer)):
                    event = events_buffer[i]
                    yield json.dumps(event) + "\n"
                last_sent = len(events_buffer)

            # If session is idle, we're done
            if session_idle.is_set():
                # Send any remaining events
                if len(events_buffer) > last_sent:
                    for i in range(last_sent, len(events_buffer)):
                        event = events_buffer[i]
                        yield json.dumps(event) + "\n"
                break

            # Wait a bit before checking again
            await asyncio.sleep(0.01)

    finally:
        # Cleanup
        unsubscribe()
        try:
            await session.destroy()
        except Exception:
            pass


@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("[*] Starting web server on http://localhost:8000")
    print("[*] Open your browser and navigate to http://localhost:8000")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
