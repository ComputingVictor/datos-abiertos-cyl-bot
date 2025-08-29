"""Main entry point for the JCYL Encyclopedia Bot."""

import asyncio
import logging
import signal
import sys
from typing import Optional

import uvicorn
from telegram.ext import Application

from src.services.config import get_settings
from src.services.fastapi_app import create_app
from src.services.scheduler import scheduler
from src.bot.telegram_bot import create_bot_application
from src.models import DatabaseManager

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

settings = get_settings()
app = create_app()
bot_application: Optional[Application] = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global bot_application
    
    # Initialize database
    db_manager = DatabaseManager(settings.database_url)
    db_manager.create_tables()
    
    # Initialize Telegram bot
    bot_application = create_bot_application()
    await bot_application.initialize()
    
    if settings.telegram_webhook_url:
        # Webhook mode
        webhook_url = f"{settings.telegram_webhook_url}{settings.telegram_webhook_path}"
        await bot_application.bot.set_webhook(webhook_url)
        logger.info(f"Telegram bot webhook set to: {webhook_url}")
    else:
        # Start bot in polling mode
        await bot_application.start()
        asyncio.create_task(bot_application.updater.start_polling())
        logger.info("Telegram bot started in polling mode")
    
    # Start scheduler for alerts
    scheduler.start()
    
    logger.info("Application startup complete")


@app.on_event("shutdown") 
async def shutdown_event():
    """Cleanup on shutdown."""
    global bot_application
    
    # Stop scheduler
    scheduler.stop()
    
    # Stop Telegram bot
    if bot_application:
        await bot_application.stop()
        await bot_application.shutdown()
    
    logger.info("Application shutdown complete")


# Handle Telegram webhook
@app.post(settings.telegram_webhook_path)
async def telegram_webhook(request):
    """Handle Telegram webhook."""
    if not bot_application:
        return {"ok": False, "error": "Bot not initialized"}
    
    try:
        json_data = await request.json()
        update = Update.de_json(json_data, bot_application.bot)
        
        await bot_application.process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"ok": False, "error": str(e)}


def handle_shutdown_signal(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    
    try:
        uvicorn.run(
            "main:app",
            host=settings.fastapi_host,
            port=settings.fastapi_port,
            reload=settings.fastapi_debug,
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)