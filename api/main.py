from fastapi import FastAPI
from temporalio.client import Client
from contextlib import asynccontextmanager
from .routers import generator_routes, git_routes, xml_routes

client: Client = None  # Global biến

from .utils import set_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    client = await Client.connect("temporal:7233")
    set_client(client)
    print("✅ Temporal client connected.")
    yield
    await client.close()
    print("🛑 Temporal client closed.")


app = FastAPI(lifespan=lifespan)
app.include_router(generator_routes.router, prefix="/api/generator", tags=["generator"])
# app.include_router(git_routes.router, prefix="/api/git", tags=["git"])
# app.include_router(xml_routes.router, prefix="/api/xml", tags=["xml"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
