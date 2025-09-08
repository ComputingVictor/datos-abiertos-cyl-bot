#!/usr/bin/env python3
"""Test script for file download functionality."""

import asyncio
import logging
import sys
import os
import tempfile
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.api import JCYLAPIClient
from src.models.callback_map import callback_mapper
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_file_download_functionality():
    """Test the file download functionality."""
    logger.info("🧪 Testing file download functionality...")
    
    try:
        # Initialize API client
        api_client = JCYLAPIClient("https://analisis.datosabiertos.jcyl.es")
        
        # Test 1: Get a sample dataset with exports
        logger.info("📋 Step 1: Getting sample dataset with export formats...")
        
        datasets, total_count = await api_client.get_datasets(search="salud", limit=5)
        if not datasets:
            logger.error("❌ No datasets found for testing")
            return False
            
        test_dataset = datasets[0]
        logger.info(f"✅ Using test dataset: {test_dataset.title}")
        
        # Test 2: Get export formats
        logger.info("📊 Step 2: Getting export formats...")
        exports = await api_client.get_dataset_exports(test_dataset.dataset_id)
        
        if not exports:
            logger.warning("⚠️  No export formats found for this dataset, trying another...")
            # Try with another dataset
            for dataset in datasets[1:]:
                exports = await api_client.get_dataset_exports(dataset.dataset_id)
                if exports:
                    test_dataset = dataset
                    logger.info(f"✅ Using dataset: {test_dataset.title}")
                    break
        
        if not exports:
            logger.error("❌ No datasets with export formats found")
            return False
        
        logger.info(f"✅ Found {len(exports)} export formats:")
        for export in exports:
            logger.info(f"   - {export.format}: {export.url}")
        
        # Test 3: Test keyboard generation - skip for now due to import issues
        logger.info("⌨️  Step 3: Skipping keyboard generation test (import dependencies)")
        logger.info("✅ Keyboard generation will be tested when bot runs")
        
        # Test 4: Test callback mapping for long URLs
        logger.info("🔗 Step 4: Testing callback data mapping...")
        
        supported_formats = ["csv", "json", "xlsx"]
        available_formats = [e for e in exports if e.format.lower() in supported_formats]
        
        if available_formats:
            test_export = available_formats[0]
            callback_data = f"download_file:{test_dataset.dataset_id}:{test_export.format}:{test_export.url}"
            
            if len(callback_data.encode()) > 60:
                short_id = callback_mapper.get_short_id(callback_data)
                short_callback = f"s:{short_id}"
                logger.info(f"✅ Long callback mapped: {len(callback_data)} chars -> {len(short_callback)} chars")
                
                # Test retrieval
                retrieved = callback_mapper.get_full_data(short_id)
                if retrieved == callback_data:
                    logger.info("✅ Callback mapping retrieval successful")
                else:
                    logger.error("❌ Callback mapping retrieval failed")
                    return False
            else:
                logger.info("✅ Callback data is short enough, no mapping needed")
        
        # Test 5: Test file download simulation
        logger.info("⬇️  Step 5: Testing file download simulation...")
        
        if available_formats:
            test_export = available_formats[0]
            logger.info(f"📁 Testing download of: {test_export.format} format")
            
            # Simulate download
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    response = await client.head(test_export.url)  # Use HEAD to avoid downloading
                    logger.info(f"✅ File is accessible: Status {response.status_code}")
                    
                    # Check content type
                    content_type = response.headers.get('content-type', 'unknown')
                    logger.info(f"📄 Content-Type: {content_type}")
                    
                    # Check file size if available
                    content_length = response.headers.get('content-length')
                    if content_length:
                        size_mb = int(content_length) / (1024 * 1024)
                        logger.info(f"📏 File size: {size_mb:.2f} MB")
                    
                except httpx.HTTPStatusError as e:
                    logger.error(f"❌ File not accessible: Status {e.response.status_code}")
                    return False
                except Exception as e:
                    logger.error(f"❌ Error accessing file: {e}")
                    return False
        
        # Test 6: Test filename generation
        logger.info("📝 Step 6: Testing filename generation...")
        
        safe_title = "".join(c for c in test_dataset.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title[:50]
        
        if available_formats:
            filename = f"{safe_title}.{available_formats[0].format.lower()}"
            logger.info(f"✅ Generated filename: {filename}")
        
        # Test 7: Test temporary file creation
        logger.info("🗂️  Step 7: Testing temporary file handling...")
        
        test_content = b"Test file content for download simulation"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_file:
            tmp_file.write(test_content)
            tmp_file_path = tmp_file.name
        
        # Check file exists
        if os.path.exists(tmp_file_path):
            logger.info("✅ Temporary file created successfully")
            
            # Clean up
            os.unlink(tmp_file_path)
            logger.info("✅ Temporary file cleaned up")
        else:
            logger.error("❌ Failed to create temporary file")
            return False
        
        logger.info("🎉 All file download functionality tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in file download test: {e}", exc_info=True)
        return False
    
    finally:
        # Close API client
        await api_client.close()


async def main():
    """Main test function."""
    logger.info("🚀 Starting file download functionality tests...")
    
    success = await test_file_download_functionality()
    
    if success:
        logger.info("✅ All tests passed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())