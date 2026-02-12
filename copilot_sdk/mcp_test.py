import asyncio
import sys
from pathlib import Path

from copilot import CopilotClient, MCPLocalServerConfig
from copilot.generated.session_events import SessionEventType


async def main():
    base_dir = Path(__file__).resolve().parent
    project_root = base_dir.parent
    server_script = str(base_dir / "server.py")

    mcp_servers: dict[str, MCPLocalServerConfig] = {
        "local-notes-app": {
            "tools": ["*"],
            "type": "stdio",
            "command": sys.executable,
            "args": [server_script],
            "cwd": str(project_root),
        },
        "gerrit-mcp": {
            "type": "local",
            "command": "mcp-server-gerrit",
            "tools": ["*"],
            "cwd": str(project_root),
            "args": [
                "--log-file",
                "./gerrit_mcp.log",
                "--log-level",
                "DEBUG",
                "--config-file",
                "./copilot_sdk/gerrit_mcp_config.json"
            ]
        },
        "mcp-atlassian": {
            "type": "local",
            "command": sys.executable,
            "tools": ["*"],
            "cwd": str(project_root),
            "args": [
                str(base_dir / "mcp_atlassian_wrapper.py"),
                "--config-file",
                str(base_dir / "mcp_atlassian_env.json"),
                "--command",
                "uvx",
                "--package",
                "mcp-atlassian"
            ]
        }
    }

    client = CopilotClient()
    await client.start()

    session = await client.create_session(
        {"model": "gpt-4.1", "streaming": True, "mcp_servers": mcp_servers}
        # {"model": "Claude Sonnet 4.5", "streaming": True, "mcp_servers": mcp_servers}
    )

    # Listen for response chunks
    def handle_event(event):
        if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            sys.stdout.write(event.data.delta_content)
            sys.stdout.flush()
        if event.type == SessionEventType.SESSION_IDLE:
            print()  # New line when done
        if event.type == SessionEventType.TOOL_EXECUTION_START:
            print(f"\n[Tool Execution Started: {event.data.tool_name}]")
        if event.type == SessionEventType.TOOL_EXECUTION_COMPLETE:
            print(f"\n[Tool Execution completed: {event.data.tool_name}]")

    session.on(handle_event)

    await session.send_and_wait(
        {
            "prompt": "Use mcp Atlassian tool to check this ticket: http://jira.lge.com/issue/browse/GRAPHICDV-7691"
        },
        timeout=300
    )

    await client.stop()


asyncio.run(main())
