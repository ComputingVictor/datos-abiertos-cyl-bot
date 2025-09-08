#!/usr/bin/env python3
"""Debug script for file download functionality."""

import asyncio
import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.api import JCYLAPIClient
from src.models.callback_map import callback_mapper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def debug_callback_data():
    """Debug callback data construction and parsing."""
    logger.info("🔍 Debugging callback data construction...")
    
    try:
        # Initialize API client
        api_client = JCYLAPIClient("https://analisis.datosabiertos.jcyl.es")
        
        # Get a dataset with exports
        datasets, _ = await api_client.get_datasets(search="salud", limit=3)
        if not datasets:
            logger.error("❌ No datasets found")
            return False
            
        for dataset in datasets:
            logger.info(f"\n📋 Testing dataset: {dataset.title}")
            
            # Get export formats
            exports = await api_client.get_dataset_exports(dataset.dataset_id)
            if not exports:
                logger.info("   ⚠️  No exports found, skipping...")
                continue
                
            # Test callback construction
            supported_formats = ["csv", "json", "xlsx"]
            available_formats = [e for e in exports if e.format.lower() in supported_formats]
            
            if not available_formats:
                logger.info("   ⚠️  No supported formats found, skipping...")
                continue
                
            for export in available_formats:
                logger.info(f"\n   🔗 Testing format: {export.format}")
                logger.info(f"   📍 URL: {export.url}")
                
                # Test original callback construction
                callback_data = f"download_file:{dataset.dataset_id}:{export.format}:{export.url}"
                logger.info(f"   📝 Original callback: {callback_data}")
                logger.info(f"   📏 Length: {len(callback_data)} chars")
                
                # Test parsing
                parts = callback_data.split(":", 3)
                logger.info(f"   ✂️  Split parts: {len(parts)} parts")
                for i, part in enumerate(parts):
                    logger.info(f"      Part {i}: {part}")
                
                # Test with callback mapper if needed
                if len(callback_data.encode()) > 60:
                    short_id = callback_mapper.get_short_id(callback_data)
                    short_callback = f"s:{short_id}"
                    logger.info(f"   🔗 Short callback: {short_callback}")
                    
                    # Test retrieval
                    retrieved = callback_mapper.get_full_data(short_id)
                    if retrieved:
                        logger.info(f"   ✅ Retrieval successful: {retrieved == callback_data}")
                        
                        # Test parsing of retrieved data
                        retrieved_parts = retrieved.split(":", 3)
                        logger.info(f"   ✂️  Retrieved split parts: {len(retrieved_parts)} parts")
                        for i, part in enumerate(retrieved_parts):
                            logger.info(f"      Retrieved Part {i}: {part}")
                    else:
                        logger.error("   ❌ Retrieval failed!")
                
                # Only test first format to avoid too much output
                break
            
            # Only test first dataset to avoid too much output
            break
        
        logger.info("🎉 Debug completed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in debug: {e}", exc_info=True)
        return False
    
    finally:
        # Close API client
        await api_client.close()

async def main():
    """Main debug function."""
    logger.info("🚀 Starting download callback debug...")
    
    success = await debug_callback_data()
    
    if success:
        logger.info("✅ Debug completed successfully!")
    else:
        logger.error("❌ Debug failed!")

if __name__ == "__main__":
    asyncio.run(main())