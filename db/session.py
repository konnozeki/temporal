from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Đường dẫn đến PostgreSQL
DATABASE_URL = "postgresql+asyncpg://temporal:temporal@postgresql:5432/postgres"

# Engine bất đồng bộ
engine = create_async_engine(DATABASE_URL, echo=True)

# Session dùng trong FastAPI
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Dependency để dùng trong route
async def get_db():
    async with async_session() as session:
        yield session
