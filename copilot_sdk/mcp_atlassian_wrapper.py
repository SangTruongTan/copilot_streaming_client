#!/usr/bin/env python3
import argparse
import json
import os
import sys


def _load_env(config_path: str) -> dict[str, str]:
    with open(config_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, dict) and isinstance(data.get("env"), dict):
        return {str(k): str(v) for k, v in data["env"].items()}

    if isinstance(data, dict) and isinstance(data.get("mcpServers"), dict):
        servers = data["mcpServers"]
        if "mcp-atlassian" in servers and isinstance(servers["mcp-atlassian"], dict):
            env = servers["mcp-atlassian"].get("env", {})
            if isinstance(env, dict):
                return {str(k): str(v) for k, v in env.items()}
        if len(servers) == 1:
            server = next(iter(servers.values()))
            env = server.get("env", {}) if isinstance(server, dict) else {}
            if isinstance(env, dict):
                return {str(k): str(v) for k, v in env.items()}

    raise ValueError("Config file must contain an 'env' map or a single mcpServers entry with env.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Wrapper to inject env vars before launching mcp-atlassian.")
    parser.add_argument("--config-file", required=True, help="Path to JSON file containing env vars.")
    parser.add_argument("--command", default="uvx", help="Launcher command (default: uvx).")
    parser.add_argument("--package", default="mcp-atlassian", help="Package name to run (default: mcp-atlassian).")
    parser.add_argument("command_args", nargs=argparse.REMAINDER, help="Extra args passed to the server.")
    args = parser.parse_args()

    try:
        env_vars = _load_env(args.config_file)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Failed to load config: {exc}", file=sys.stderr)
        sys.exit(1)

    os.environ.update(env_vars)
    command = [args.command, args.package] + args.command_args
    os.execvp(command[0], command)


if __name__ == "__main__":
    main()
