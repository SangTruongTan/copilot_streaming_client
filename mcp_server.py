#!/usr/bin/env python3
"""
Simple MCP server that provides system information tools.
Keeps it minimal - just CPU, memory, disk, and uptime.
"""

import asyncio
import json
import platform
import psutil
import sys
from datetime import datetime, timedelta


def get_cpu_info():
    """Get CPU usage and information"""
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq()
    
    return {
        "usage_percent": cpu_percent,
        "core_count": cpu_count,
        "frequency_mhz": cpu_freq.current if cpu_freq else None,
        "processor": platform.processor()
    }


def get_memory_info():
    """Get memory usage information"""
    mem = psutil.virtual_memory()
    
    return {
        "total_gb": round(mem.total / (1024**3), 2),
        "available_gb": round(mem.available / (1024**3), 2),
        "used_gb": round(mem.used / (1024**3), 2),
        "percent_used": mem.percent
    }


def get_disk_info():
    """Get disk usage information"""
    disk = psutil.disk_usage('/')
    
    return {
        "total_gb": round(disk.total / (1024**3), 2),
        "used_gb": round(disk.used / (1024**3), 2),
        "free_gb": round(disk.free / (1024**3), 2),
        "percent_used": disk.percent
    }


def get_system_info():
    """Get general system information"""
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    
    return {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "hostname": platform.node(),
        "uptime_seconds": int(uptime.total_seconds()),
        "uptime_readable": str(timedelta(seconds=int(uptime.total_seconds())))
    }


# MCP Server Implementation
class MCPServer:
    """Simple MCP server using stdio transport"""
    
    def __init__(self):
        self.tools = {
            "get_cpu_info": {
                "name": "get_cpu_info",
                "description": "Get current CPU usage and information including usage percentage, core count, and processor details",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "get_memory_info": {
                "name": "get_memory_info",
                "description": "Get current memory (RAM) usage information including total, available, used memory in GB and usage percentage",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "get_disk_info": {
                "name": "get_disk_info",
                "description": "Get disk storage usage information including total, used, free space in GB and usage percentage",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "get_system_info": {
                "name": "get_system_info",
                "description": "Get general system information including platform, architecture, hostname, and system uptime",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    
    async def handle_request(self, request: dict) -> dict:
        """Handle incoming JSON-RPC request"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "system-info-mcp-server",
                            "version": "1.0.0"
                        }
                    }
                }
            
            elif method == "tools/list":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": list(self.tools.values())
                    }
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                
                if tool_name == "get_cpu_info":
                    result = get_cpu_info()
                elif tool_name == "get_memory_info":
                    result = get_memory_info()
                elif tool_name == "get_disk_info":
                    result = get_disk_info()
                elif tool_name == "get_system_info":
                    result = get_system_info()
                else:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Unknown tool: {tool_name}"
                        }
                    }
                
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2)
                            }
                        ]
                    }
                }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
        
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def run(self):
        """Run the MCP server (stdio transport)"""
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(
            lambda: protocol, sys.stdin
        )
        
        while True:
            try:
                # Read Content-Length header
                line = await reader.readline()
                if not line:
                    break
                
                header = line.decode().strip()
                if not header.startswith("Content-Length:"):
                    continue
                
                content_length = int(header.split(":")[1].strip())
                
                # Read blank line
                await reader.readline()
                
                # Read content
                content = await reader.readexactly(content_length)
                request = json.loads(content.decode())
                
                # Handle request
                response = await self.handle_request(request)
                
                # Send response
                response_json = json.dumps(response)
                response_bytes = response_json.encode()
                sys.stdout.write(f"Content-Length: {len(response_bytes)}\r\n\r\n")
                sys.stdout.write(response_json)
                sys.stdout.flush()
                
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                break


async def main():
    server = MCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
