import asyncio
from copilot import CopilotClient

async def main():
    client = CopilotClient()
    await client.start()

    session = await client.create_session({
        "model": "gpt-5",
        "mcp_servers": {
          "github": {
            "command": "docker",
            "args": [
              "run",
              "-i",
              "--rm",
              "-e",
              "GITHUB_PERSONAL_ACCESS_TOKEN",
              "mcp/github"
            ],
            "env": {
              "GITHUB_PERSONAL_ACCESS_TOKEN": ""
            },
            "tools": ["*"]
          }
        },
    })

    response = await session.send_and_wait({
        "prompt": "List my recent GitHub notifications"
    })
    print(response.data.content)

    await client.stop()

asyncio.run(main())
