"""
test_mcp_client.py
=============================================================================
PG Cert in AI - Stage 2: Model Context Protocol (MCP) Client
=============================================================================
Connects to the running FastMCP server over HTTP, dynamically discovers 
available tools, and executes a real database query against PostgreSQL.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Console encoding for Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")
load_dotenv()

# Official MCP Python SDK imports
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    server_url = "http://127.0.0.1:8000/mcp"
    rls_user_id = os.getenv("RLS_USER_ID", "00000000-0000-0000-0000-000000000000")

    print("=" * 70)
    print(" CONNECTING TO FASTMCP SERVER VIA STREAMABLE HTTP")
    print(f" Server URL:   {server_url}")
    print(f" RLS Context:  Super Admin ({rls_user_id})")
    print("=" * 70)

    # FastMCP uses headers to pass tenant / security context (RLS)
    headers = {"X-RLS-User-ID": rls_user_id}

    # Establish Streamable HTTP Client connection (returns read stream, write stream, session_id)
    async with streamablehttp_client(server_url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            # 1. Initialize the MCP protocol handshake
            await session.initialize()
            print("\n✅ MCP Handshake Successful!")

            # 2. Dynamic Tool Discovery
            print("\n>> Requesting available tools from MCP Server (tools/list)...")
            tools_result = await session.list_tools()

            print(f"\nDiscovered {len(tools_result.tools)} tool(s) exposed by the server:")
            print("-" * 70)
            for tool in tools_result.tools:
                print(f"🔧 Tool: {tool.name}")
                print(f"   Description: {tool.description.strip()}")
                print(f"   Required parameters: {tool.inputSchema.get('required', [])}")
                print()
            print("-" * 70)

            # 3. Call a Real Tool against PostgreSQL!
            product_search = "Hammer Drill"
            print(f"\n>> Executing live tool call: 'get_products_by_name(product_name=\"{product_search}\")'...")
            
            call_result = await session.call_tool(
                name="get_products_by_name",
                arguments={"product_name": product_search, "max_rows": 5}
            )

            print("\n📢 LIVE DATA RETURNED FROM POSTGRESQL DATABASE VIA MCP:")
            print("-" * 70)
            for content in call_result.content:
                if content.type == "text":
                    print(content.text)
            print("-" * 70)
            print("\n🎯 STAGE 2 VERIFICATION COMPLETE: Real DB tools are live over MCP!")


if __name__ == "__main__":
    asyncio.run(main())
