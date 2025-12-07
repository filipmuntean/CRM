from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import init_db
from app.core.config import settings
from app.api import products, sync, sales

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title="Multi-Platform CRM",
    description="CRM for synchronizing products across Marktplaats, Vinted, Depop, and Facebook Marketplace",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(products.router, prefix="/api")
app.include_router(sync.router, prefix="/api")
app.include_router(sales.router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint - returns dashboard HTML"""
    with open("templates/dashboard.html", "r") as f:
        return f.read()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0"
    }


@app.on_event("startup")
async def startup_event():
    """Startup event - initialize services"""
    print("Starting Multi-Platform CRM...")
    print(f"Dashboard available at: http://{settings.HOST}:{settings.PORT}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
