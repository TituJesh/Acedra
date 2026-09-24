from fastapi import FastAPI
from app.routers.auth import router as auth_router
from app.routers.students import router as students_router
from app.routers.departments import router as departments_router
from app.routers.documents import router as documents_router
from app.utils.logger import logger

app = FastAPI(title="Acedra")
logger.info("Acedra application started")
app.include_router(auth_router)
app.include_router(students_router)
app.include_router(departments_router)
app.include_router(documents_router)

@app.get("/")
def root():
    return {
        "message": "Welcome to Acedra Student Management System"
    }