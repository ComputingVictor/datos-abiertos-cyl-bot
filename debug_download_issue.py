#!/usr/bin/env python3
"""Debug script to identify the exact download issue."""

import asyncio
import logging
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from api import JCYLAPIClient
from bot.keyboards import create_export_menu_keyboard
from models.callback_map import callback_mapper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def debug_download_flow():
    """Debug the entire download flow step by step."""
    logger.info("🔍 Debugging download flow...")
    
    try:
        # Step 1: Get a real dataset with exports
        api_client = JCYLAPIClient("https://analisis.datosabiertos.jcyl.es")
        
        datasets, _ = await api_client.get_datasets(search="salud", limit=1)
        if not datasets:
            logger.error("❌ No datasets found")
            return False
            
        dataset = datasets[0]
        logger.info(f"📋 Using dataset: {dataset.title}")
        logger.info(f"🆔 Dataset ID: {dataset.dataset_id}")
        
        # Step 2: Get exports
        exports = await api_client.get_dataset_exports(dataset.dataset_id)
        logger.info(f"📊 Found {len(exports)} export formats")
        
        for export in exports[:3]:  # Show first 3
            logger.info(f"   - {export.format}: {export.url}")
        
        if not exports:
            logger.error("❌ No exports found")
            return False
        
        # Step 3: Create the export menu keyboard
        logger.info("⌨️  Creating export menu keyboard...")
        keyboard = create_export_menu_keyboard(dataset.dataset_id, exports)
        
        # Step 4: Analyze the keyboard structure
        logger.info("🔍 Analyzing keyboard structure...")
        for i, row in enumerate(keyboard.inline_keyboard):
            logger.info(f"Row {i}:")
            for j, button in enumerate(row):
                logger.info(f"  Button {j}: '{button.text}' -> '{button.callback_data or button.url}'")
                
                # Check if this is a download button
                if button.callback_data and button.callback_data.startswith("download_file:"):
                    logger.info(f"    🎯 FOUND DOWNLOAD BUTTON!")
                    logger.info(f"    📝 Callback: {button.callback_data}")
                    
                    # Test parsing the callback
                    parts = button.callback_data.split(":", 3)
                    logger.info(f"    ✂️  Parts: {len(parts)} - {parts}")
                    
                    if len(parts) >= 4:
                        logger.info(f"    ✅ Callback format is correct")
                    else:
                        logger.error(f"    ❌ Callback format is WRONG - only {len(parts)} parts")
                
                # Check if this is a short callback
                elif button.callback_data and button.callback_data.startswith("s:"):
                    short_id = button.callback_data[2:]
                    full_data = callback_mapper.get_full_data(short_id)
                    logger.info(f"    🔗 SHORT CALLBACK: {button.callback_data}")
                    logger.info(f"    📝 Full data: {full_data}")
                    
                    if full_data and full_data.startswith("download_file:"):
                        logger.info(f"    🎯 MAPPED DOWNLOAD BUTTON!")
                        parts = full_data.split(":", 3)
                        logger.info(f"    ✂️  Mapped parts: {len(parts)} - {parts}")
        
        # Step 5: Check supported formats
        logger.info("🔧 Checking supported formats...")
        supported_formats = ["csv", "json", "xlsx"]
        available_formats = [e for e in exports if e.format.lower() in supported_formats]
        
        logger.info(f"📋 Available supported formats: {len(available_formats)}")
        for fmt in available_formats:
            logger.info(f"   ✅ {fmt.format}: {fmt.url}")
        
        if not available_formats:
            logger.warning("⚠️  NO SUPPORTED FORMATS - Download buttons won't appear!")
            logger.info("Available formats in dataset:")
            for export in exports:
                logger.info(f"   - {export.format}")
        
        await api_client.close()
        
        logger.info("🎉 Debug completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in debug: {e}", exc_info=True)
        return False

async def main():
    logger.info("🚀 Starting download flow debug...")
    
    success = await debug_download_flow()
    
    if success:
        logger.info("✅ Debug completed!")
    else:
        logger.error("❌ Debug failed!")

if __name__ == "__main__":
    asyncio.run(main())