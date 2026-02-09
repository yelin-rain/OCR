import asyncio
from core.database import AsyncSessionLocal
from models.task import OCRTask
from sqlalchemy.future import select

async def check():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(OCRTask).order_by(OCRTask.id.desc()).limit(5))
        tasks = result.scalars().all()
        for t in tasks:
            print(f"ID: {t.id}, Status: {t.status}, Result: {str(t.result)[:50] if t.result else None}")

if __name__ == "__main__":
    asyncio.run(check())
