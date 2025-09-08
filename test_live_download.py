#!/usr/bin/env python3
"""Live test script for download functionality with actual Telegram bot."""

import asyncio
import logging
import os
import sys
import tempfile
from datetime import datetime
import html
import httpx
from telegram import Bot

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from api import JCYLAPIClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_telegram_file_upload():
    """Test file upload to Telegram."""
    # Note: This requires a valid bot token and chat ID to work
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    test_chat_id = os.getenv('TEST_CHAT_ID')  # Your own chat ID for testing
    
    if not bot_token:
        logger.warning("⚠️  TELEGRAM_BOT_TOKEN not set - skipping Telegram test")
        return await test_file_creation_only()
    
    if not test_chat_id:
        logger.warning("⚠️  TEST_CHAT_ID not set - skipping Telegram test")
        return await test_file_creation_only()
    
    try:
        logger.info("🤖 Testing with actual Telegram bot...")
        
        # Initialize bot
        bot = Bot(token=bot_token)
        
        # Get a dataset and download file
        api_client = JCYLAPIClient("https://analisis.datosabiertos.jcyl.es")
        
        datasets, _ = await api_client.get_datasets(search="salud", limit=1)
        if not datasets:
            logger.error("❌ No datasets found")
            return False
        
        dataset = datasets[0]
        exports = await api_client.get_dataset_exports(dataset.dataset_id)
        
        csv_export = None
        for export in exports:
            if export.format.lower() == 'csv':
                csv_export = export
                break
        
        if not csv_export:
            logger.error("❌ No CSV export found")
            return False
        
        # Download file
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(csv_export.url)
            response.raise_for_status()
        
        # Create filename
        safe_title = "".join(c for c in dataset.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title[:30]  # Shorter for testing
        filename = f"{safe_title}.csv"
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_file:
            tmp_file.write(response.content)
            tmp_file_path = tmp_file.name
        
        logger.info(f"📁 Created file: {tmp_file_path} ({len(response.content)} bytes)")
        
        # Create caption
        caption = (
            f"📎 <b>{html.escape(dataset.title)}</b>\n\n"
            f"📊 Formato: CSV\n"
            f"📅 Test: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            f"🧪 Archivo de prueba para debug"
        )
        
        # Send file via Telegram
        logger.info("📤 Sending file via Telegram...")
        with open(tmp_file_path, 'rb') as file:
            await bot.send_document(
                chat_id=test_chat_id,
                document=file,
                filename=filename,
                caption=caption,
                parse_mode='HTML'
            )
        
        logger.info("✅ File sent successfully!")
        
        # Cleanup
        os.unlink(tmp_file_path)
        await api_client.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in Telegram test: {e}", exc_info=True)
        return False

async def test_file_creation_only():
    """Test only file creation without Telegram."""
    logger.info("📁 Testing file creation only...")
    
    try:
        # Get a dataset and download file
        api_client = JCYLAPIClient("https://analisis.datosabiertos.jcyl.es")
        
        datasets, _ = await api_client.get_datasets(search="salud", limit=1)
        if not datasets:
            logger.error("❌ No datasets found")
            return False
        
        dataset = datasets[0]
        exports = await api_client.get_dataset_exports(dataset.dataset_id)
        
        csv_export = None
        for export in exports:
            if export.format.lower() == 'csv':
                csv_export = export
                break
        
        if not csv_export:
            logger.error("❌ No CSV export found")
            return False
        
        logger.info(f"📋 Dataset: {dataset.title}")
        logger.info(f"🔗 URL: {csv_export.url}")
        
        # Download file
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(csv_export.url)
            response.raise_for_status()
        
        logger.info(f"✅ Downloaded {len(response.content)} bytes")
        
        # Create filename
        safe_title = "".join(c for c in dataset.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title[:30]
        filename = f"{safe_title}.csv"
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_file:
            tmp_file.write(response.content)
            tmp_file_path = tmp_file.name
        
        # Verify file
        if os.path.exists(tmp_file_path):
            file_size = os.path.getsize(tmp_file_path)
            logger.info(f"✅ File created: {tmp_file_path} ({file_size} bytes)")
            
            # Read first few lines to verify content
            with open(tmp_file_path, 'r', encoding='utf-8') as f:
                first_lines = [f.readline().strip() for _ in range(3)]
                logger.info(f"📄 First lines: {first_lines}")
        else:
            logger.error("❌ File was not created")
            return False
        
        # Cleanup
        os.unlink(tmp_file_path)
        await api_client.close()
        
        logger.info("✅ File creation test passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in file test: {e}", exc_info=True)
        return False

async def main():
    """Main test function."""
    logger.info("🚀 Starting live download test...")
    
    success = await test_telegram_file_upload()
    
    if success:
        logger.info("✅ Test completed successfully!")
    else:
        logger.error("❌ Test failed!")

if __name__ == "__main__":
    asyncio.run(main())