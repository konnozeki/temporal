from fastapi import FastAPI
from temporalio.client import Client
from contextlib import asynccontextmanager
from .routers import generator_routes, git_routes, xml_routes
from fastapi.middleware.cors import CORSMiddleware
from .utils import sio
from socketio import ASGIApp
from .utils import set_client

# Global Temporal client
client: Client = None


# Lifespan để kết nối Temporal
@asynccontextmanager
async def lifespan(app: FastAPI):
    global client
    client = await Client.connect("temporal:7233")
    set_client(client)
    print("✅ Temporal client connected.")
    yield
    await client.close()
    print("🛑 Temporal client closed.")


# Tạo FastAPI app riêng
fastapi_app = FastAPI(lifespan=lifespan)

# Middleware CORS nếu cần
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Điều chỉnh tùy theo môi trường
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount các router
fastapi_app.include_router(generator_routes.router, prefix="/api/generator", tags=["generator"])
# fastapi_app.include_router(git_routes.router, prefix="/api/git", tags=["git"])  # Bỏ comment nếu dùng
fastapi_app.include_router(xml_routes.router, prefix="/api/xml", tags=["xml"])

# Gói FastAPI app vào Socket.IO ASGI app
app = ASGIApp(sio, other_asgi_app=fastapi_app)


# Chạy bằng: `uvicorn app.main:app --reload`
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
