async def fetch_analysis_rows(conn, query):
    """The analyst may inspect workflow data, but never bypass manager decisions."""
    async with conn.transaction(readonly=True):
        return await conn.fetch(query)
