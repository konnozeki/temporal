from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from config.configuration import DATABASE_URL, SQL_ECHO

# Engine bất đồng bộ
engine = create_async_engine(DATABASE_URL, echo=SQL_ECHO)

# Session dùng trong FastAPI
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Dependency để dùng trong route
async def get_db():
    async with async_session() as session:
        yield session
