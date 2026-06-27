from fastapi import FastAPI

app = FastAPI(title="Yellamma AI Receptionist")


@app.get("/")
def home():
    return {
        "message": "Welcome to Yellamma AI Receptionist"
    }


@app.get("/health")
def health():
    return {
        "status": "running"
    }
