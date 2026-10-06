import os
import asyncpg


async def connect():
    host = os.getenv('POSTGRES_SERVER_FQDN')
    if host:
        from azure.identity.aio import DefaultAzureCredential
        async with DefaultAzureCredential() as credential:
            token = await credential.get_token('https://ossrdbms-aad.database.windows.net/.default')
        conn = await asyncpg.connect(host=host, database='zava',
            user=os.environ['POSTGRES_SERVER_USERNAME'], password=token.token,
            ssl='require', timeout=20, command_timeout=30)
    else:
        conn = await asyncpg.connect(os.environ['POSTGRES_URL'], timeout=20, command_timeout=30)
    await conn.execute("SELECT set_config('app.current_rls_user_id', $1, false)",
                       os.getenv('RLS_USER_ID', '00000000-0000-0000-0000-000000000000'))
    return conn
