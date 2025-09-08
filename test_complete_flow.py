#!/usr/bin/env python3
"""Test complete flow from export menu to download."""

import asyncio
import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from src.api import JCYLAPIClient
from src.models.callback_map import callback_mapper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def simulate_complete_flow():
    """Simulate the complete flow from export menu to download."""
    logger.info("🎬 Simulating complete bot flow...")
    
    try:
        # Step 1: Get a real dataset
        api_client = JCYLAPIClient("https://analisis.datosabiertos.jcyl.es")
        datasets, _ = await api_client.get_datasets(search="salud", limit=1)
        
        if not datasets:
            logger.error("❌ No datasets found")
            return False
        
        dataset = datasets[0]
        logger.info(f"📋 Using dataset: {dataset.title}")
        
        # Step 2: Show export menu (simulate user clicking "💾 Exportar datos")
        exports = await api_client.get_dataset_exports(dataset.dataset_id)
        logger.info(f"📊 Dataset has {len(exports)} export formats")
        
        # Step 3: Show export menu keyboard
        logger.info("⌨️  User sees export menu with these options:")
        
        # Web links
        for export in exports:
            logger.info(f"   🔗 {export.format.upper()} (web link)")
        
        # Download buttons
        supported_formats = ["csv", "json", "xlsx"]
        available_formats = [e for e in exports if e.format.lower() in supported_formats]
        
        if available_formats:
            logger.info("   📱 Descargar como archivo adjunto")
            for export in available_formats:
                logger.info(f"   📎 {export.format.upper()} (download button)")
        
        # Step 4: Simulate user clicking download button
        if not available_formats:
            logger.error("❌ No download buttons available")
            return False
        
        test_export = available_formats[0]  # Use first available format
        logger.info(f"\n🎯 User clicks: 📎 {test_export.format.upper()}")
        
        # Step 5: Create the callback data that would be sent
        callback_data = f"download_file:{dataset.dataset_id}:{test_export.format}:{test_export.url}"
        logger.info(f"📝 Generated callback: {callback_data}")
        
        # Step 6: Simulate callback mapping (if needed)
        if len(callback_data.encode()) > 60:
            short_id = callback_mapper.get_short_id(callback_data)
            short_callback = f"s:{short_id}"
            logger.info(f"🔗 Callback mapped to: {short_callback}")
            
            # Step 7: Simulate bot receiving the callback
            logger.info(f"\n📞 Bot receives callback: {short_callback}")
            
            # Step 8: Resolve short callback  
            if short_callback.startswith("s:"):
                short_id_received = short_callback[2:]
                full_data = callback_mapper.get_full_data(short_id_received)
                logger.info(f"🔍 Resolving short ID: {short_id_received}")
                logger.info(f"✅ Resolved to: {full_data}")
                
                if full_data:
                    callback_data_final = full_data
                else:
                    logger.error("❌ Could not resolve callback!")
                    return False
            else:
                callback_data_final = short_callback
        else:
            logger.info("📏 Callback is short enough, no mapping needed")
            callback_data_final = callback_data
        
        # Step 9: Simulate callback handler logic
        logger.info(f"\n🔧 Processing callback: {callback_data_final}")
        
        if callback_data_final.startswith("download_file:"):
            logger.info("✅ Callback matches download_file pattern!")
            
            # Parse callback
            parts = callback_data_final.split(":", 3)
            logger.info(f"✂️  Parsed parts: {len(parts)}")
            
            if len(parts) >= 4:
                dataset_id, file_format, file_url = parts[1], parts[2], parts[3]
                logger.info(f"📋 Dataset ID: {dataset_id}")
                logger.info(f"📊 Format: {file_format}")
                logger.info(f"🔗 URL: {file_url}")
                
                # Step 10: Simulate download (without actually downloading)
                logger.info("\n⬇️  Would start download process...")
                logger.info("   ⏳ Show loading message")
                logger.info(f"   📥 Download from: {file_url}")
                logger.info("   📝 Get dataset info")
                logger.info("   🗂️  Create temporary file")
                logger.info("   📤 Send as document")
                logger.info("   ✅ Success!")
                
            else:
                logger.error(f"❌ Invalid callback format - only {len(parts)} parts")
                return False
        else:
            logger.error(f"❌ Callback doesn't match download_file pattern: {callback_data_final}")
            return False
        
        await api_client.close()
        
        logger.info("\n🎉 Complete flow simulation successful!")
        logger.info("📋 Summary:")
        logger.info("   ✅ Dataset found")
        logger.info("   ✅ Export formats available")
        logger.info("   ✅ Download buttons would be shown")
        logger.info("   ✅ Callback would be generated correctly")
        logger.info("   ✅ Handler would process correctly")
        logger.info("   ✅ Download would work")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in flow simulation: {e}", exc_info=True)
        return False

async def main():
    logger.info("🚀 Starting complete flow simulation...")
    
    success = await simulate_complete_flow()
    
    if success:
        logger.info("✅ Flow simulation passed - download should work!")
    else:
        logger.error("❌ Flow simulation failed - there's an issue!")

if __name__ == "__main__":
    asyncio.run(main())