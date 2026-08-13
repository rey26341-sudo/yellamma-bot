from contextlib import asynccontextmanager
import logging
import os

from dotenv import load_dotenv

# Load .env FIRST, before any other app import — several modules
# (app.core.checkpointer, app.voice.session, etc.) read environment
# variables at import time, so this has to run before those imports
# happen below, not after.
load_dotenv()

# Normalize the Gemini credential naming across the different SDKs used
# in this repo. Some clients read GOOGLE_API_KEY while others expect
# GEMINI_API_KEY, so keep both aliases in sync for startup.
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")
elif os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.routes.appointments import router as appointments_router
from app.api.routes.chat import router as chat_router
from app.core.checkpointer import build_checkpointer
from app.core.graph import build_graph
from app.voice import receptionist as voice_router
from app.voice.session import get_redis
from app.database.database import engine
from app.models.appointment import Base
from seed_tenants import seed_tenants

# uvicorn doesn't configure the root logger by default, so custom
# loggers (like app.voice's TIMING logs) would otherwise print
# nowhere. This makes them show up in the same console.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s: %(message)s")


async def create_db_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up the Redis connection used by the voice receptionist's
    # session store, and fail fast at boot if it's unreachable rather
    # than on the first live call.
    redis_client = get_redis()
    await redis_client.ping()

    await create_db_tables()
    await seed_tenants()

    # LangGraph's Postgres checkpointer — replaces the old in-memory
    # ConversationService/GeminiService session dicts. Built once
    # here and stored on app.state, not per-request.
    checkpointer, checkpointer_cm = await build_checkpointer()
    app.state.chat_graph = build_graph(checkpointer)

    yield

    await redis_client.close()
    await checkpointer_cm.__aexit__(None, None, None)


app = FastAPI(title="Yellamma AI Receptionist", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(appointments_router)
app.include_router(voice_router.router)


@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.get("/health")
def health_check():
    return {"status": "ok"}
