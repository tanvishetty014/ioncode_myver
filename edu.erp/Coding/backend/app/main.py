from fastapi import FastAPI, Request  # Added Request
import time  # Added time for the logger
from .api.v1.routes import router as api_router
from fastapi.middleware.cors import CORSMiddleware
from .db.models import Base
from .core.database import engine

# Disabled auto table creation - database schema is already finalized in HeidiSQL
# Base.metadata.create_all(bind=engine)

app = FastAPI()

# --- NEW: Middleware to log requests (useful for CORS debugging) ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    print(f"REQUEST: {request.method} {request.url.path} - STATUS: {response.status_code} - TIME: {process_time:.2f}ms")
    return response

# Configuration for CORS - allows React frontend to communicate with backend (UNTOUCHED)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # Allow all origins (dev mode)
    allow_credentials=False,        # Must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the main API router (UNTOUCHED)
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to IonCudos API", "status": "Online"}