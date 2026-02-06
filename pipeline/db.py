from supabase import create_client, Client
from pipeline.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, BATCH_SIZE


def get_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def batch_upsert(client: Client, table: str, rows: list[dict], conflict_columns: str | None = None, batch_size: int = BATCH_SIZE):
    """Upsert rows in batches. Returns total inserted count."""
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        q = client.table(table).upsert(batch)
        if conflict_columns:
            q = client.table(table).upsert(batch, on_conflict=conflict_columns)
        result = q.execute()
        total += len(result.data) if result.data else 0
    return total


def batch_insert(client: Client, table: str, rows: list[dict], batch_size: int = BATCH_SIZE):
    """Insert rows in batches, ignoring duplicates."""
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        try:
            result = client.table(table).insert(batch).execute()
            total += len(result.data) if result.data else 0
        except Exception as e:
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                # Insert one by one to skip duplicates
                for row in batch:
                    try:
                        result = client.table(table).insert(row).execute()
                        total += 1
                    except Exception:
                        pass
            else:
                raise
    return total
