from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.routes.appointments import router as appointments_router
from app.api.routes.chat import router as chat_router
from app.voice import receptionist as voice_router
from app.voice.session import get_redis
from app.database.database import engine
from app.models.appointment import Base

# Create DB tables on startup (existing behaviour, unchanged)
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up the Redis connection used by the voice receptionist's
    # session store, and fail fast at boot if it's unreachable rather
    # than on the first live call.
    redis_client = get_redis()
    await redis_client.ping()

    yield

    await redis_client.close()


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
