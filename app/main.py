from app.api.routes.appointments import router as appointments_router

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.routes.chat import router as chat_router

from app.database.database import engine
from app.models.appointment import Base


app = FastAPI(title="Yellamma AI Receptionist")

app.mount("/static", StaticFiles(directory="static"), name="static")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


Base.metadata.create_all(bind=engine)

app.include_router(chat_router)
app.include_router(appointments_router)


@app.get("/")
def root():
        return FileResponse("static/index.html")
