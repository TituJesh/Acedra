import time

from fastapi import FastAPI, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import ENVIRONMENT
from app.dependencies import get_db
from app.routers.auth import router as auth_router
from app.routers.students import router as students_router
from app.routers.departments import router as departments_router
from app.routers.documents import router as documents_router
from app.utils.logger import logger

app = FastAPI(
    title="Acedra API",
    description="Production-ready Student Information & Cloud Document Management System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for cross-origin client access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.middleware("http")
async def add_process_time_and_log(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {process_time:.2f}ms"
    )
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled exception during {request.method} {request.url.path}: {exc}",
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


logger.info(f"Acedra application started in '{ENVIRONMENT}' environment")

app.include_router(auth_router)
app.include_router(students_router)
app.include_router(departments_router)
app.include_router(documents_router)


@app.get("/", tags=["General"])
def root():
    return {
        "message": "Welcome to Acedra Student Management System"
    }


@app.get("/health", tags=["General"])
def health_check(db: Session = Depends(get_db)):
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error(f"Database health check failed: {exc}")
        db_status = "unhealthy"

    is_healthy = db_status == "healthy"
    response_status = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=response_status,
        content={
            "status": "healthy" if is_healthy else "degraded",
            "environment": ENVIRONMENT,
            "database": db_status
        }
    )