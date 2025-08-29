"""FastAPI application."""

import logging
from typing import Dict, Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..models import DatabaseManager
from ..api import JCYLAPIClient
from .config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
db_manager = DatabaseManager(settings.database_url)
api_client = JCYLAPIClient(settings.jcyl_api_base_url)


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="JCYL Encyclopedia Bot API",
        description="Backend for JCYL Open Data Telegram Bot",
        version="1.0.0",
        debug=settings.fastapi_debug
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup_event():
        """Initialize database on startup."""
        db_manager.create_tables()
        logger.info("FastAPI application started")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown."""
        await api_client.close()
        logger.info("FastAPI application shutdown")

    @app.get("/health")
    async def health_check() -> Dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy", "service": "jcyl-encyclopedia-bot"}

    @app.get("/debug/themes")
    async def debug_themes() -> Dict[str, Any]:
        """Debug endpoint to check themes from API."""
        try:
            themes = await api_client.get_themes_with_real_counts()
            return {
                "status": "ok",
                "themes_count": len(themes),
                "themes": [{"name": t.name, "count": t.count} for t in themes[:10]]
            }
        except Exception as e:
            logger.error(f"Error in debug_themes: {e}")
            return {"status": "error", "message": str(e)}

    @app.get("/debug/datasets")
    async def debug_datasets(theme: str = None, limit: int = 5) -> Dict[str, Any]:
        """Debug endpoint to check datasets from API."""
        try:
            datasets, total_count = await api_client.get_datasets(theme=theme, limit=limit)
            return {
                "status": "ok",
                "datasets_count": len(datasets),
                "total_count": total_count,
                "datasets": [
                    {
                        "id": d.dataset_id,
                        "title": d.title,
                        "publisher": d.publisher,
                        "modified": d.modified
                    } for d in datasets
                ]
            }
        except Exception as e:
            logger.error(f"Error in debug_datasets: {e}")
            return {"status": "error", "message": str(e)}

    @app.get("/debug/dataset/{dataset_id}")
    async def debug_dataset_info(dataset_id: str) -> Dict[str, Any]:
        """Debug endpoint to check specific dataset info."""
        try:
            dataset = await api_client.get_dataset_info(dataset_id)
            if not dataset:
                return {"status": "not_found", "dataset_id": dataset_id}
            
            exports = await api_client.get_dataset_exports(dataset_id)
            attachments = await api_client.get_dataset_attachments(dataset_id)
            
            return {
                "status": "ok",
                "dataset": {
                    "id": dataset.dataset_id,
                    "title": dataset.title,
                    "description": dataset.description,
                    "publisher": dataset.publisher,
                    "license": dataset.license,
                    "modified": dataset.modified,
                    "records_count": dataset.records_count,
                    "themes": dataset.themes,
                    "keywords": dataset.keywords
                },
                "exports": [{"format": e.format, "url": e.url} for e in exports],
                "attachments": [{"href": a.href, "title": a.title} for a in attachments]
            }
        except Exception as e:
            logger.error(f"Error in debug_dataset_info: {e}")
            return {"status": "error", "message": str(e)}

    @app.post(settings.telegram_webhook_path)
    async def telegram_webhook(request: Request):
        """Handle Telegram webhook."""
        try:
            # This will be handled by the Telegram bot
            # For now, just return ok
            return JSONResponse(content={"ok": True})
        except Exception as e:
            logger.error(f"Error in telegram webhook: {e}")
            return JSONResponse(content={"ok": False, "error": str(e)}, status_code=500)

    return app


app = create_app()