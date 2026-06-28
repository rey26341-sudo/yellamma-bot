from fastapi import FastAPI
from app.api.routes.chat import router as chat_router

app = FastAPI(title="Yellamma AI Receptionist")

app.include_router(chat_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to Yellamma AI Receptionist"
    }
