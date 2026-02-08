#!/usr/bin/env python3
"""
Minimal Copilot CLI streaming client - everything you need to get started
"""

import asyncio
import json
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional


# ============================================================================
# 1. JSON-RPC CLIENT (handles protocol-level communication)
# ============================================================================

@dataclass
class JsonRpcError(Exception):
    code: int
    message: str
    data: Optional[Any] = None


class JsonRpcClient:
    """
    Minimal JSON-RPC 2.0 client for Copilot CLI.

    Uses threading for blocking I/O + asyncio for application logic.
    """

    def __init__(self, process: subprocess.Popen):
        self.process = process
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.notification_handler: Optional[Callable[[str, dict], None]] = None
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._read_thread: Optional[threading.Thread] = None

    async def start(self):
        """Start background reader thread"""
        self._loop = asyncio.get_running_loop()
        self._running = True
        self._read_thread = threading.Thread(
            target=self._read_loop,
            daemon=True
        )
        self._read_thread.start()

    async def stop(self):
        """Stop reader and wait for thread"""
        self._running = False
        if self._read_thread:
            self._read_thread.join(timeout=1.0)

    async def request(self, method: str, params: dict = None) -> Any:
        """Send request and wait for response"""
        request_id = str(uuid.uuid4())

        # Create future for response
        future = self._loop.create_future()
        self.pending_requests[request_id] = future

        # Send message
        message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }

        await self._send_message(message)

        try:
            return await asyncio.wait_for(future, timeout=30.0)
        finally:
            self.pending_requests.pop(request_id, None)

    def _read_loop(self):
        """Background thread: continuously read messages"""
        try:
            while self._running:
                message = self._read_message()
                if message:
                    self._handle_message(message)
        except Exception as e:
            if self._running:
                print(f"Reader error: {e}")

    def _read_message(self) -> Optional[dict]:
        """Read single JSON-RPC message with Content-Length header"""
        try:
            # Read header line (e.g., "Content-Length: 123\r\n")
            header_bytes = self.process.stdout.readline()
            if not header_bytes:
                return None

            header = header_bytes.decode("utf-8").strip()
            if not header.startswith("Content-Length:"):
                return None

            # Parse content length
            content_length = int(header.split(":")[1].strip())

            # Read blank line
            self.process.stdout.readline()

            # Read exact content bytes
            content_bytes = self.process.stdout.read(content_length)
            return json.loads(content_bytes.decode("utf-8"))

        except Exception as e:
            print(f"Message read error: {e}")
            return None

    def _handle_message(self, message: dict):
        """Route message to handler or pending request"""
        # Silent - don't print debug output

        # Is this a response to our request?
        if "id" in message:
            future = self.pending_requests.get(message["id"])
            if future and not future.done():
                if "error" in message:
                    error = message["error"]
                    exc = JsonRpcError(
                        error.get("code", -1),
                        error.get("message", "Unknown"),
                        error.get("data")
                    )
                    self._loop.call_soon_threadsafe(future.set_exception, exc)
                elif "result" in message:
                    self._loop.call_soon_threadsafe(future.set_result, message["result"])
            return

        # Is this a notification (streaming event)?
        if "method" in message and "id" not in message:
            if self.notification_handler and self._loop:
                method = message["method"]
                params = message.get("params", {})
                self._loop.call_soon_threadsafe(
                    self.notification_handler,
                    method,
                    params
                )
            return

        # Is this a request from server (tool.call, permission.request, etc)?
        if "method" in message and "id" in message:
            # For now, just send successful empty response to unblock
            method = message["method"]
            msg_id = message["id"]
            # Auto-respond to requests to unblock processing
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {}
            }
            if self._loop:
                import json as json_module
                content = json_module.dumps(response, separators=(",", ":"))
                content_bytes = content.encode("utf-8")
                header = f"Content-Length: {len(content_bytes)}\r\n\r\n"

                def write_response():
                    self.process.stdin.write(header.encode("utf-8"))
                    self.process.stdin.write(content_bytes)
                    self.process.stdin.flush()

                self._loop.run_in_executor(None, write_response)
            return

    async def _send_message(self, message: dict):
        """Send message with Content-Length framing"""
        loop = asyncio.get_running_loop()

        def write():
            content = json.dumps(message, separators=(",", ":"))
            content_bytes = content.encode("utf-8")
            header = f"Content-Length: {len(content_bytes)}\r\n\r\n"

            self.process.stdin.write(header.encode("utf-8"))
            self.process.stdin.write(content_bytes)
            self.process.stdin.flush()

        # Don't block event loop
        await loop.run_in_executor(None, write)


# ============================================================================
# 2. SESSION (represents a conversation)
# ============================================================================

class StreamingSession:
    """A Copilot conversation session with event subscriptions"""

    def __init__(self, session_id: str, rpc: JsonRpcClient):
        self.session_id = session_id
        self.rpc = rpc
        self.event_handlers: list[Callable] = []

    def on(self, handler: Callable) -> Callable:
        """Subscribe to events"""
        self.event_handlers.append(handler)
        return lambda: self.event_handlers.remove(handler)

    def dispatch_event(self, event: dict):
        """Dispatch event to all handlers"""
        for handler in self.event_handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"Handler error: {e}")

    async def send(self, prompt: str) -> str:
        """Send a message and return message ID"""
        response = await self.rpc.request(
            "session.send",
            {
                "sessionId": self.session_id,
                "prompt": prompt
            }
        )
        return response["messageId"]

    async def destroy(self):
        """Destroy the session"""
        await self.rpc.request("session.destroy", {"sessionId": self.session_id})


# ============================================================================
# 3. CLIENT (manages connection and sessions)
# ============================================================================

class StreamingClient:
    """Main client for Copilot CLI with streaming support"""

    def __init__(self, cli_path: str = "copilot"):
        self.cli_path = cli_path
        self.process: Optional[subprocess.Popen] = None
        self.rpc: Optional[JsonRpcClient] = None
        self.sessions: Dict[str, StreamingSession] = {}
        self._stderr_thread: Optional[threading.Thread] = None

    async def start(self):
        """Start Copilot CLI server"""
        print("[*] Starting Copilot CLI...")

        # Start Copilot CLI in server mode (streaming is controlled per-session, not here)
        self.process = subprocess.Popen(
            [self.cli_path, "--headless", "--no-auto-update", "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False  # Binary mode
        )

        # Start thread to read stderr (for debugging)
        self._stderr_thread = threading.Thread(
            target=self._read_stderr,
            daemon=True
        )
        self._stderr_thread.start()

        # Create RPC client
        self.rpc = JsonRpcClient(self.process)

        # Set up notification handler that routes to sessions
        def handle_notification(method: str, params: dict):
            if method == "session.event":
                session_id = params["sessionId"]
                event = params["event"]
                session = self.sessions.get(session_id)
                if session:
                    session.dispatch_event(event)

        self.rpc.notification_handler = handle_notification

        # Start reader thread
        await self.rpc.start()

        print("[✓] Copilot CLI started")

    def _read_stderr(self):
        """Read stderr from CLI (for debugging)"""
        if not self.process:
            return
        try:
            for line in iter(self.process.stderr.readline, b''):
                if line:
                    print(f"[CLI STDERR] {line.decode('utf-8', errors='ignore').strip()}")
        except Exception as e:
            print(f"[!] Error reading stderr: {e}")

    async def create_session(self, model: str = "gpt-4.1", streaming: bool = True) -> StreamingSession:
        """Create a new conversation session"""
        if not self.rpc:
            raise RuntimeError("Not connected. Call start() first.")

        print(f"[*] Creating session (model={model}, streaming={streaming})")

        response = await self.rpc.request(
            "session.create",
            {
                "model": model,
                "streaming": streaming
            }
        )

        session_id = response["sessionId"]
        session = StreamingSession(session_id, self.rpc)
        self.sessions[session_id] = session

        print(f"[✓] Session created: {session_id}")
        return session

    async def stop(self):
        """Stop the client and cleanup"""
        print("[*] Stopping...")

        # Destroy all sessions
        for session in list(self.sessions.values()):
            try:
                await session.destroy()
            except Exception as e:
                print(f"[!] Failed to destroy session: {e}")

        # Stop RPC
        if self.rpc:
            await self.rpc.stop()

        # Kill process
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

        print("[✓] Stopped")


# ============================================================================
# 4. USAGE EXAMPLE
# ============================================================================

async def main():
    """Complete example: stream a response in real-time"""

    # Create client
    client = StreamingClient()
    await client.start()

    # Create session with streaming
    session = await client.create_session(streaming=True)

    # Set up event handler with timing and usage tracking
    event_count = {"delta": 0}
    start_time = time.time()
    end_time = None
    usage_info = {}
    quota_info = {}
    request_info = {}
    session_idle = asyncio.Event()

    def on_event(event: dict):
        nonlocal end_time
        event_type = event.get("type")
        event_data = event.get("data", {})

        if event_type == "assistant.message_delta":
            # Real-time streaming chunk!
            event_count["delta"] += 1
            delta_content = event_data.get("deltaContent", "")
            print(delta_content, end="", flush=True)

        elif event_type == "assistant.message":
            # Full message received (all deltas complete)
            print()

        elif event_type == "session.usage" or event_type == "assistant.usage":
            # Capture usage metrics (tokens, cost, etc.)
            usage_info.update(event_data)

            # Check for quota snapshots (premium request limits)
            if "quotaSnapshots" in event_data:
                quota_info.update(event_data.get("quotaSnapshots", {}))

            # Check for requests info (API request counts)
            if "requests" in event_data:
                request_info.update(event_data.get("requests", {}))

        elif event_type == "session.idle":
            # Session is idle (finished processing)
            end_time = time.time()
            elapsed = end_time - start_time

            # Format output
            print(f"\n[✓] Done ({event_count['delta']} streaming chunks)")
            print(f"⏱️  Generation time: {elapsed:.2f}s")

            # Print usage metrics if available
            if usage_info:
                print("\n📊 Usage Metrics:")
                if "inputTokens" in usage_info:
                    print(f"  • Input tokens: {usage_info.get('inputTokens', 'N/A')}")
                if "outputTokens" in usage_info:
                    print(f"  • Output tokens: {usage_info.get('outputTokens', 'N/A')}")
                if "cacheReadTokens" in usage_info and usage_info.get('cacheReadTokens', 0) > 0:
                    print(f"  • Cache read tokens: {usage_info.get('cacheReadTokens', 'N/A')}")
                if "cacheWriteTokens" in usage_info and usage_info.get('cacheWriteTokens', 0) > 0:
                    print(f"  • Cache write tokens: {usage_info.get('cacheWriteTokens', 'N/A')}")
                if "cost" in usage_info:
                    print(f"  • Cost: ${usage_info.get('cost', 'N/A'):.6f}")
                if "model" in usage_info:
                    print(f"  • Model: {usage_info.get('model', 'N/A')}")

            # Print premium request info if available
            if quota_info:
                print("\n💎 Premium Request Quota:")
                for model, quota_data in quota_info.items():
                    if isinstance(quota_data, dict):
                        entitlement = quota_data.get("entitlementRequests", "N/A")
                        used = quota_data.get("usedRequests", "N/A")
                        remaining_pct = quota_data.get("remainingPercentage", "N/A")
                        is_unlimited = quota_data.get("isUnlimitedEntitlement", False)

                        print(f"  • Model: {model}")
                        if is_unlimited:
                            print(f"    Entitlement: Unlimited")
                        else:
                            print(f"    Entitlement: {entitlement} requests")
                        print(f"    Used: {used} requests")
                        print(f"    Remaining: {remaining_pct}%")

            # Print request counts if available
            if request_info:
                print("\n📈 Request Statistics:")
                for model, req_data in request_info.items():
                    if isinstance(req_data, dict):
                        count = req_data.get("count", "N/A")
                        cost = req_data.get("cost", "N/A")
                        print(f"  • {model}: {count} requests (${cost:.6f})")

            # Signal that session is idle
            session_idle.set()

    # Subscribe to events
    unsubscribe = session.on(on_event)

    # Send a prompt
    print("\n[>>] Sending prompt...\n")
    # await session.send("Explain what APIs are in 2-3 sentences")
    await session.send("Could you please write a 200 words paragraph to describe the New York city?")

    # Wait for session to become idle (or timeout after 15 seconds)
    try:
        await asyncio.wait_for(session_idle.wait(), timeout=15)
    except asyncio.TimeoutError:
        print("\n⚠️ Timeout waiting for response to complete")

    # Cleanup
    unsubscribe()
    await session.destroy()
    await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
