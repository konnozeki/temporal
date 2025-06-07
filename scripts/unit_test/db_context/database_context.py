import asyncio
import asyncpg
from typing import List, Dict, Any


class DatabaseContext:
    def __init__(self):
        self.dsn = "postgresql://odoo:odoo17%402023@192.168.1.8:5433/nagaco"
        self.conn: asyncpg.Connection | None = None

    async def connect(self):
        self.conn = await asyncpg.connect(self.dsn)

    async def close(self):
        if self.conn:
            await self.conn.close()

    async def get_all_ids(self, table_name: str) -> List[Any]:
        try:
            rows = await self.conn.fetch(f"SELECT id FROM {table_name}")
            return [r["id"] for r in rows]
        except Exception as e:
            print(f"❌ Error getting IDs from {table_name}: {e}")
            return []

    async def get_next_id(self, table_name: str) -> int:
        try:
            row = await self.conn.fetchrow(f"SELECT pg_get_serial_sequence('{table_name}', 'id') AS seq_name")
            if not row or not row["seq_name"]:
                raise ValueError(f"No sequence found for {table_name}.id")
            sequence_name = row["seq_name"]
            nextval_row = await self.conn.fetchrow(f"SELECT nextval('{sequence_name}') AS next_id")
            return nextval_row["next_id"]
        except Exception as e:
            print(f"❌ Error getting next ID from {table_name}: {e}")
            return -1

    async def get_table_id_contexts(self, table_names: List[str]) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}
        for table in table_names:
            ids = await self.get_all_ids(table)
            next_id = await self.get_next_id(table)
            result[table] = {"ids": ids, "next_id": next_id}
        return result
