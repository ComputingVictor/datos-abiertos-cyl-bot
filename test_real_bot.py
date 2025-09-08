#!/usr/bin/env python3
"""Test with a real bot to see what's happening."""

import asyncio
import logging
import os
import sys
from telegram import Bot, Update
from telegram.ext import ContextTypes

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from src.api import JCYLAPIClient
from src.models.callback_map import callback_mapper
import tempfile
import httpx
import io
from datetime import datetime
import html

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_with_real_bot():
    """Test the download function directly with a real bot."""
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    test_chat_id = os.getenv('TEST_CHAT_ID')
    
    if not bot_token:
        logger.error("❌ TELEGRAM_BOT_TOKEN not set")
        logger.info("💡 Set TELEGRAM_BOT_TOKEN environment variable to test")
        return False
        
    if not test_chat_id:
        logger.error("❌ TEST_CHAT_ID not set") 
        logger.info("💡 Set TEST_CHAT_ID environment variable to test")
        return False
    
    try:
        logger.info("🤖 Testing with real Telegram bot...")
        
        # Initialize bot
        bot = Bot(token=bot_token)
        
        # Create a mock context object
        class MockContext:
            def __init__(self, bot):
                self.bot = bot
        
        context = MockContext(bot)
        
        # Get a real dataset
        api_client = JCYLAPIClient("https://analisis.datosabiertos.jcyl.es")
        datasets, _ = await api_client.get_datasets(search="salud", limit=1)
        
        if not datasets:
            logger.error("❌ No datasets found")
            return False
        
        dataset = datasets[0]
        exports = await api_client.get_dataset_exports(dataset.dataset_id)
        
        # Find CSV export
        csv_export = None
        for export in exports:
            if export.format.lower() == 'csv':
                csv_export = export
                break
        
        if not csv_export:
            logger.error("❌ No CSV export found")
            return False
        
        # Simulate the exact handler logic
        logger.info("🎯 Simulating exact handler logic...")
        
        # Create callback data
        callback_data = f"download_file:{dataset.dataset_id}:{csv_export.format}:{csv_export.url}"
        logger.info(f"📝 Callback data: {callback_data}")
        
        # Parse it
        parts = callback_data.split(":", 3)
        dataset_id, file_format, file_url = parts[1], parts[2], parts[3]
        logger.info(f"✅ Parsed: dataset_id={dataset_id}, format={file_format}")
        
        # Send loading message
        loading_msg = await bot.send_message(
            chat_id=test_chat_id,
            text=f"⏳ Descargando archivo {file_format.upper()}..."
        )
        logger.info(f"📤 Loading message sent: {loading_msg.message_id}")
        
        # Download the file (with size limit for testing)
        logger.info(f"⬇️  Starting download from URL: {file_url}")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.head(file_url)  # Use HEAD first to check size
            content_length = response.headers.get('content-length')
            
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                logger.info(f"📏 File size: {size_mb:.2f} MB")
                
                if size_mb > 20:  # Limit for testing
                    await loading_msg.edit_text(
                        f"⚠️  Archivo demasiado grande para test ({size_mb:.1f} MB).\n"
                        f"Usando archivo de ejemplo más pequeño..."
                    )
                    
                    # Create a small test file instead
                    test_content = f"Test download from {dataset.title}\nFormat: {file_format}\nURL: {file_url}\nDate: {datetime.now()}"
                    file_data = test_content.encode('utf-8')
                else:
                    # Download actual file
                    response = await client.get(file_url)
                    response.raise_for_status()
                    file_data = response.content
            else:
                # Download actual file (no size info)
                response = await client.get(file_url)
                response.raise_for_status()
                file_data = response.content
        
        logger.info(f"✅ Download completed, size: {len(file_data)} bytes")
        
        # Get dataset info
        dataset_info = await api_client.get_dataset_info(dataset_id)
        logger.info(f"✅ Dataset info retrieved")
        
        # Create filename
        safe_title = "".join(c for c in dataset_info.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title[:30]  # Shorter for testing
        filename = f"TEST_{safe_title}.{file_format.lower()}"
        logger.info(f"✅ Generated filename: {filename}")
        
        # Create file stream
        file_stream = io.BytesIO(file_data)
        file_stream.name = filename
        
        # Create caption
        caption = (
            f"📎 <b>{html.escape(dataset_info.title)}</b>\n\n"
            f"📊 Formato: {file_format.upper()}\n"
            f"📅 Test: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            f"🧪 Prueba de descarga automática"
        )
        
        # Send document
        logger.info(f"📤 Sending document to chat {test_chat_id}...")
        logger.info(f"📄 Filename: {filename}")
        logger.info(f"📝 Caption length: {len(caption)} chars")
        
        message = await bot.send_document(
            chat_id=test_chat_id,
            document=file_stream,
            filename=filename,
            caption=caption,
            parse_mode='HTML'
        )
        
        logger.info(f"✅ Document sent successfully! Message ID: {message.message_id}")
        if message.document:
            logger.info(f"📎 Telegram file_id: {message.document.file_id}")
            logger.info(f"📏 Telegram file_size: {message.document.file_size}")
        else:
            logger.warning("⚠️  No document object in response!")
        
        # Clean up loading message
        await loading_msg.delete()
        
        await api_client.close()
        
        logger.info("🎉 Real bot test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in real bot test: {e}", exc_info=True)
        return False

async def main():
    logger.info("🚀 Starting real bot test...")
    logger.info("💡 Make sure TELEGRAM_BOT_TOKEN and TEST_CHAT_ID are set")
    
    success = await test_with_real_bot()
    
    if success:
        logger.info("✅ Real bot test passed!")
    else:
        logger.error("❌ Real bot test failed!")

if __name__ == "__main__":
    asyncio.run(main())