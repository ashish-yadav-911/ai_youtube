# import logging
# from fastapi import FastAPI, Request
# from fastapi.responses import HTMLResponse
# from fastapi.staticfiles import StaticFiles
# from fastapi.templating import Jinja2Templates

# from app.core.config import settings
# from app.core.logging_config import setup_logging
# # Import routers later when they are created
# # from app.routers import input_processor, topic_generator, video_editor, youtube_uploader

# # Setup logging *before* creating FastAPI app instance
# setup_logging()
# logger = logging.getLogger(__name__)

# # Create FastAPI app instance
# app = FastAPI(
#     title=settings.PROJECT_NAME,
#     version=settings.VERSION,
#     # Add other FastAPI configurations like description, docs_url etc.
# )

# # --- Mount Static Files ---
# # This allows serving CSS, JS, images from the 'static' directory
# app.mount("/static", StaticFiles(directory="app/static"), name="static")

# # --- Setup Templates ---
# # This allows rendering HTML files from the 'templates' directory
# templates = Jinja2Templates(directory="app/templates")

# # --- Include Routers --- (Uncomment and add when routers are ready)
# # app.include_router(input_processor.router, prefix="/api/v1/input", tags=["Input Processing"])
# # app.include_router(topic_generator.router, prefix="/api/v1/topics", tags=["Topic Generation"])
# # app.include_router(video_editor.router, prefix="/api/v1/editor", tags=["Video Editor"])
# # app.include_router(youtube_uploader.router, prefix="/api/v1/youtube", tags=["YouTube"])

# # --- Root Endpoint (Simple Test) ---
# @app.get("/", response_class=HTMLResponse)
# async def read_root(request: Request):
#     """Serves the main landing page."""
#     logger.info("Root endpoint '/' accessed.")
#     # Create a dummy index.html in app/templates later
#     # return templates.TemplateResponse("index.html", {"request": request, "title": "YT AutoVid Suite"})
#     # For now, just return simple HTML:
#     return HTMLResponse(content="""
#         <html>
#             <head><title>YT AutoVid Suite</title></head>
#             <body><h1>Welcome to YT AutoVid Suite!</h1></body>
#         </html>
#     """)

# # --- Application Startup Event --- (Optional, for things like DB checks)
# @app.on_event("startup")
# async def startup_event():
#     logger.info("Application startup...")
#     # You could add a check here to ensure DB connection is okay
#     # or initialize other resources.
#     pass

# # --- Application Shutdown Event --- (Optional)
# @app.on_event("shutdown")
# async def shutdown_event():
#     logger.info("Application shutdown...")
#     # Clean up resources if needed
#     pass

# # --- Health Check Endpoint --- (Good practice)
# @app.get("/health", tags=["Health"])
# async def health_check():
#     """Simple health check endpoint."""
#     logger.debug("Health check endpoint accessed.")
#     return {"status": "ok"}

import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path # Import Path

from app.core.config import settings
from app.core.logging_config import setup_logging
# Import routers later when they are created
from app.routers import input_processor, topic_generator # Add topic_generator import later
from app.database import Base # Import Base and engine for Alembic check
#from app.database import Base

# Setup logging *before* creating FastAPI app instance
setup_logging()
logger = logging.getLogger(__name__)

# --- Check if DB exists, provide guidance if not ---
db_path = Path(settings.DATABASE_URL.split('///')[-1])
if settings.DATABASE_URL.startswith("sqlite") and not db_path.is_file():
    logger.warning(f"Database file not found at {db_path}")
    logger.warning("Please run 'alembic upgrade head' from the project root to create the database.")
    # You could exit here, but letting it run might be okay for initial setup
    # import sys
    # sys.exit("Database not found. Run Alembic migrations.")

# Create FastAPI app instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
)

# Mount Static Files (if you have CSS/JS files later)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Setup Templates
templates = Jinja2Templates(directory="app/templates")

# --- Include Routers --- (Uncomment and add when routers are ready)
# We will create these python files in the next steps
# app.include_router(input_processor.router, prefix="/api/v1", tags=["Jobs"])
# app.include_router(topic_generator.router, prefix="/api/v1/jobs", tags=["Jobs"]) # Merge into one conceptually?

# --- Root Endpoint ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serves the main landing page."""
    logger.info("Root endpoint '/' accessed.")
    return templates.TemplateResponse("index.html", {"request": request, "title": "YT AutoVid Suite"})

# --- Application Startup/Shutdown Events --- (Keep as before)
@app.on_event("startup")
async def startup_event():
    logger.info("Application startup...")
    # Optional: Check DB connection, preload models etc.
    pass

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown...")
    pass

# --- Health Check Endpoint --- (Keep as before)
@app.get("/health", tags=["Health"])
async def health_check():
    """Simple health check endpoint."""
    logger.debug("Health check endpoint accessed.")
    return {"status": "ok"}

# Add the routers here once created in routers/
from app.routers import jobs # We'll create this router file next
app.include_router(jobs.router, prefix="/api/v1", tags=["Jobs"])