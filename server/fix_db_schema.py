import asyncio
from sqlalchemy import text
from core.database import engine

async def fix_schema():
    async with engine.begin() as conn:
        print("Checking if column exists...")
        try:
             # Try to add the column. If it exists, it might fail or we can check first.
             # Simple approach: execute ALTER TABLE.
             await conn.execute(text("ALTER TABLE ocr_tasks ADD COLUMN owner_id INTEGER REFERENCES users(id);"))
             print("Successfully added owner_id column.")
        except Exception as e:
            print(f"Error adding column (maybe it exists?): {e}")

if __name__ == "__main__":
    asyncio.run(fix_schema())
