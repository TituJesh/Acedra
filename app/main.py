from fastapi import FastAPI
from app.routers.auth import router as auth_router

app = FastAPI(title="Acedra")
app.include_router(auth_router)

@app.get("/")
def root():
    return {
        "message": "Welcome to Acedra Student Management System"
    }