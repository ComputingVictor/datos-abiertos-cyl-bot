#!/usr/bin/env python3
"""Test script for Telegram document sending functionality."""

import asyncio
import sys
import os
import logging
import tempfile
from datetime import datetime
import html
import httpx
import io

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.api import JCYLAPIClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def simulate_exact_bot_behavior():
    """Simulate the exact bot behavior for file download and sending."""
    logger.info("🎯 Simulating exact bot behavior...")
    
    try:
        # Step 1: Initialize API client (same as bot)
        api_client = JCYLAPIClient("https://analisis.datosabiertos.jcyl.es")
        
        # Step 2: Get dataset and exports (simulate user clicking download)
        datasets, _ = await api_client.get_datasets(search="salud", limit=1)
        if not datasets:
            logger.error("❌ No datasets found")
            return False
        
        test_dataset = datasets[0]
        exports = await api_client.get_dataset_exports(test_dataset.dataset_id)
        
        csv_export = None
        for export in exports:
            if export.format.lower() == 'csv':
                csv_export = export
                break
        
        if not csv_export:
            logger.error("❌ No CSV export found")
            return False
        
        # Step 3: Simulate callback data construction and parsing
        callback_data = f"download_file:{test_dataset.dataset_id}:{csv_export.format}:{csv_export.url}"
        logger.info(f"📝 Callback data constructed: {callback_data[:100]}...")
        
        # Parse it (simulate handler)
        parts = callback_data.split(":", 3)
        dataset_id, file_format, file_url = parts[1], parts[2], parts[3]
        logger.info(f"✅ Parsed: dataset_id={dataset_id}, format={file_format}")
        
        # Step 4: Download the file (exactly like handler)
        logger.info(f"⬇️  Starting download from URL: {file_url}")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(file_url)
            response.raise_for_status()
            logger.info(f"✅ Download completed, content length: {len(response.content)} bytes")
        
        # Step 5: Get dataset info for filename (exactly like handler)
        logger.info(f"📋 Getting dataset info for: {dataset_id}")
        dataset = await api_client.get_dataset_info(dataset_id)
        logger.info(f"✅ Dataset info retrieved: {dataset.title}")
        
        # Step 6: Create filename (exactly like handler)
        safe_title = "".join(c for c in dataset.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title[:50]
        filename = f"{safe_title}.{file_format.lower()}"
        logger.info(f"✅ Generated filename: {filename}")
        
        # Step 7: Create temporary file (exactly like handler)
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_format.lower()}") as tmp_file:
            tmp_file.write(response.content)
            tmp_file_path = tmp_file.name
        logger.info(f"✅ Created temporary file: {tmp_file_path}")
        
        # Step 8: Create caption (exactly like handler)
        caption = (
            f"📎 <b>{html.escape(dataset.title)}</b>\n\n"
            f"📊 Formato: {file_format.upper()}\n"
            f"📅 Descargado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        if dataset.records_count:
            caption += f"\n📄 Registros: {dataset.records_count:,}"
        logger.info(f"✅ Caption created: {len(caption)} chars")
        
        # Step 9: Simulate document preparation (exactly like handler) 
        logger.info("📤 Preparing document for sending...")
        
        # Read file data
        with open(tmp_file_path, 'rb') as file_obj:
            document_data = file_obj.read()
        
        # Create BytesIO stream
        file_stream = io.BytesIO(document_data)
        file_stream.name = filename
        
        logger.info(f"✅ Document prepared: {len(document_data)} bytes")
        logger.info(f"✅ Stream name: {file_stream.name}")
        logger.info(f"✅ Stream position: {file_stream.tell()}")
        
        # Reset stream position to beginning
        file_stream.seek(0)
        
        # Verify we can read the stream
        test_read = file_stream.read(100)
        logger.info(f"✅ Stream test read: {len(test_read)} bytes")
        file_stream.seek(0)  # Reset again
        
        # Step 10: Simulate what would happen in send_document
        logger.info("🔍 Simulating Telegram send_document preparation...")
        
        # Check if we have actual bot token for testing
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        test_chat_id = os.getenv('TEST_CHAT_ID')
        
        if bot_token and test_chat_id:
            logger.info("🤖 Bot token available - testing actual send...")
            from telegram import Bot
            
            bot = Bot(token=bot_token)
            
            try:
                message = await bot.send_document(
                    chat_id=test_chat_id,
                    document=file_stream,
                    filename=filename,
                    caption=caption,
                    parse_mode='HTML'
                )
                logger.info("✅ Document sent successfully via Telegram!")
                logger.info(f"📨 Message ID: {message.message_id}")
                
                # Check if document has file_id
                if message.document:
                    logger.info(f"📎 File ID: {message.document.file_id}")
                    logger.info(f"📏 File size: {message.document.file_size}")
                else:
                    logger.warning("⚠️  No document in message - this might be the issue!")
                
            except Exception as e:
                logger.error(f"❌ Failed to send document: {e}")
                return False
        else:
            logger.info("⚠️  No bot credentials - skipping actual send test")
        
        # Step 11: Cleanup
        os.unlink(tmp_file_path)
        await api_client.close()
        
        logger.info("🎉 Exact bot behavior simulation completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in simulation: {e}", exc_info=True)
        return False

async def main():
    """Main test function."""
    logger.info("🚀 Starting Telegram send test...")
    logger.info("💡 Set TELEGRAM_BOT_TOKEN and TEST_CHAT_ID env vars for live testing")
    
    success = await simulate_exact_bot_behavior()
    
    if success:
        logger.info("✅ Simulation completed successfully!")
        logger.info("🔧 The document sending should work correctly!")
    else:
        logger.error("❌ Simulation failed!")

if __name__ == "__main__":
    asyncio.run(main())