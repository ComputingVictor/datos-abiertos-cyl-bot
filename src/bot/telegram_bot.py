"""Telegram bot setup and main application."""

import logging
from typing import Optional

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from ..services.config import get_settings
from .handlers import (
    start_command,
    handle_callback,
    my_subscriptions_command,
    help_command,
    search_datasets,
    recent_datasets,
    portal_stats_command,
    dataset_stats,
    user_bookmarks,
    handle_text_search,
    keyword_alerts_command,
    daily_summary,
    export_catalog_command
)

logger = logging.getLogger(__name__)

settings = get_settings()


def create_bot_application() -> Application:
    """Create and configure the Telegram bot application."""
    if not settings.telegram_bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
    
    # Create application
    application = Application.builder().token(settings.telegram_bot_token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("buscar", search_datasets))
    application.add_handler(CommandHandler("recientes", recent_datasets))
    application.add_handler(CommandHandler("estadisticas", portal_stats_command))
    application.add_handler(CommandHandler("favoritos", user_bookmarks))
    application.add_handler(CommandHandler("mis_alertas", my_subscriptions_command))
    application.add_handler(CommandHandler("alertas_palabras", keyword_alerts_command))
    application.add_handler(CommandHandler("resumen_diario", daily_summary))
    application.add_handler(CommandHandler("catalogo", export_catalog_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    # Handle text messages as search queries (add this last to not interfere with commands)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_search))
    
    return application


async def setup_webhook(application: Application) -> None:
    """Setup webhook for the bot."""
    if settings.telegram_webhook_url:
        webhook_url = f"{settings.telegram_webhook_url}{settings.telegram_webhook_path}"
        await application.bot.set_webhook(webhook_url)
        logger.info(f"Webhook set to: {webhook_url}")
    else:
        logger.info("No webhook URL configured, running in polling mode")


async def start_bot() -> None:
    """Start the Telegram bot."""
    application = create_bot_application()
    
    # Initialize the application
    await application.initialize()
    
    if settings.telegram_webhook_url:
        # Webhook mode
        await setup_webhook(application)
        await application.start()
        logger.info("Bot started in webhook mode")
    else:
        # Polling mode
        await application.run_polling(
            drop_pending_updates=True,
            close_loop=False
        )


if __name__ == "__main__":
    import asyncio
    
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")