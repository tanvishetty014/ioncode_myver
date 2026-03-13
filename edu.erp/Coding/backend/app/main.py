from fastapi import FastAPI
from .api.v1.routes import router as api_router
from fastapi.middleware.cors import CORSMiddleware
from .db.models import Base
from .core.database import engine

# Disabled auto table creation - database schema is already finalized in HeidiSQL
# Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configuration for CORS - allows React frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # Allow all origins (dev mode)
    allow_credentials=False,        # Must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the main API router
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to IonCudos API", "status": "Online"}