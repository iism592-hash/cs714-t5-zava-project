"""
inventory_specialist.py
=============================================================================
Inventory Specialist Agent for Zava DIY Retail System
Responsible for:
1. Grounding inquiries with the live FastMCP tool server (port 8000)
2. Fallback to pgvector cosine similarity semantic search if exact match is 0
=============================================================================
"""

import os
import sys
from pathlib import Path
from typing import Optional
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


class InventorySpecialistAgent:
    """Agent responsible for querying live stock and prices from PostgreSQL/FastMCP."""

    def __init__(self, mcp_url: str = "http://127.0.0.1:8000/mcp", rls_user_id: str = "00000000-0000-0000-0000-000000000000") -> None:
        self.mcp_url = mcp_url
        self.rls_user_id = rls_user_id

    async def query_inventory(self, search_term: str) -> str:
        """Executes exact FastMCP lookup with automatic pgvector semantic fallback."""
        headers = {"X-RLS-User-ID": self.rls_user_id}
        try:
            async with streamablehttp_client(self.mcp_url, headers=headers) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        name="get_products_by_name",
                        arguments={"product_name": search_term, "max_rows": 3}
                    )
                    output = ""
                    for item in result.content:
                        if item.type == "text":
                            output += item.text

                    # If literal search found results, return them
                    if '"row_count": 0' not in output and "Error" not in output:
                        return output

                    # FALLBACK: HYBRID SEMANTIC VECTOR SEARCH (pgvector)
                    # Add customer_sales folder to sys.path if needed
                    cs_dir = Path(__file__).resolve().parent.parent / "mcp_server" / "customer_sales"
                    if str(cs_dir) not in sys.path:
                        sys.path.insert(0, str(cs_dir))

                    from customer_sales_postgres import PostgreSQLCustomerSales
                    from customer_sales_semantic_search_text_embeddings import SemanticSearchTextEmbedding

                    embedder = SemanticSearchTextEmbedding()
                    query_vector = embedder.generate_query_embedding(search_term)

                    if query_vector:
                        db = PostgreSQLCustomerSales()
                        await db.create_pool()
                        semantic_res = await db.search_products_by_similarity(
                            query_vector,
                            rls_user_id=self.rls_user_id,
                            max_rows=3,
                            similarity_threshold=30.0
                        )
                        await db.close_pool()
                        return f"Exact search found no literal matches. Found closest related products via AI Semantic Vector Search:\n{semantic_res}"

                    return output

        except Exception as e:
            return f"Database query failed: {str(e)}"
