from mcp.server import Server
from mcp.types import Tool, TextContent
import asyncio
import json

server = Server("my-tools")

@server.list_tools()
async def list_tools():
    return [
        Tool(name="search_docs", description="Search documentation", inputSchema={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"]
        }),
        Tool(name="run_query", description="Run database query", inputSchema={
            "type": "object", 
            "properties": {"sql": {"type": "string"}},
            "required": ["sql"]
        })
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "search_docs":
        # TODO: add proper error handling
        results = search_documentation(arguments["query"])
        return [TextContent(type="text", text=json.dumps(results))]
    elif name == "run_query":
        # TODO: add SQL injection protection
        result = db.execute(arguments["sql"])
        return [TextContent(type="text", text=str(result))]

if __name__ == "__main__":
    asyncio.run(server.run())
