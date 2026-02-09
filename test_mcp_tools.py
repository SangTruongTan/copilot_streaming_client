#!/usr/bin/env python3
"""
Quick test to verify MCP server can gather system info
"""

from mcp_server import get_cpu_info, get_memory_info, get_disk_info, get_system_info
import json

print("Testing MCP Server System Info Tools\n")
print("=" * 50)

print("\n1. CPU Info:")
cpu_info = get_cpu_info()
print(json.dumps(cpu_info, indent=2))

print("\n2. Memory Info:")
mem_info = get_memory_info()
print(json.dumps(mem_info, indent=2))

print("\n3. Disk Info:")
disk_info = get_disk_info()
print(json.dumps(disk_info, indent=2))

print("\n4. System Info:")
sys_info = get_system_info()
print(json.dumps(sys_info, indent=2))

print("\n" + "=" * 50)
print("✓ All tools working correctly!")
