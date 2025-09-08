#!/usr/bin/env python3
"""Simple debug script without complex imports."""

import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from src.api import JCYLAPIClient
from src.models.callback_map import callback_mapper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def simulate_keyboard_creation(dataset_id, exports):
    """Simulate the keyboard creation logic."""
    logger.info("🎯 Simulating keyboard creation...")
    
    # This is the exact logic from create_export_menu_keyboard
    supported_formats = ["csv", "json", "xlsx"]
    available_formats = [e for e in exports if e.format.lower() in supported_formats]
    
    logger.info(f"📋 Supported formats found: {len(available_formats)}")
    for fmt in available_formats:
        logger.info(f"   ✅ {fmt.format}: {fmt.url}")
    
    if not available_formats:
        logger.warning("⚠️  NO SUPPORTED FORMATS - This is why download buttons don't appear!")
        return []
    
    # Simulate button creation
    download_buttons = []
    for export in available_formats:
        callback_data = f"download_file:{dataset_id}:{export.format}:{export.url}"
        logger.info(f"📝 Would create button: 📎 {export.format.upper()}")
        logger.info(f"   Callback: {callback_data}")
        
        # Check if needs mapping
        if len(callback_data.encode()) > 60:
            short_id = callback_mapper.get_short_id(callback_data)
            short_callback = f"s:{short_id}"
            logger.info(f"   🔗 Mapped to: {short_callback}")
        else:
            logger.info(f"   📏 Direct callback (short enough)")
        
        download_buttons.append(callback_data)
    
    return download_buttons

async def debug_real_issue():
    """Find the real issue."""
    logger.info("🔍 Finding the real issue...")
    
    try:
        # Get dataset
        api_client = JCYLAPIClient("https://analisis.datosabiertos.jcyl.es")
        
        datasets, _ = await api_client.get_datasets(search="salud", limit=3)
        if not datasets:
            logger.error("❌ No datasets found")
            return False
        
        for i, dataset in enumerate(datasets):
            logger.info(f"\n📋 Dataset {i+1}: {dataset.title}")
            logger.info(f"🆔 ID: {dataset.dataset_id}")
            
            # Get exports
            exports = await api_client.get_dataset_exports(dataset.dataset_id)
            logger.info(f"📊 Total exports: {len(exports)}")
            
            # Show all formats
            all_formats = [e.format.lower() for e in exports]
            logger.info(f"📋 All formats: {', '.join(all_formats)}")
            
            # Simulate keyboard creation
            buttons = simulate_keyboard_creation(dataset.dataset_id, exports)
            
            if buttons:
                logger.info(f"✅ Would create {len(buttons)} download buttons")
                break
            else:
                logger.warning("⚠️  No download buttons would be created")
        
        await api_client.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return False

async def main():
    logger.info("🚀 Starting simple debug...")
    
    success = await debug_real_issue()
    
    if success:
        logger.info("✅ Debug completed!")
    else:
        logger.error("❌ Debug failed!")

if __name__ == "__main__":
    asyncio.run(main())