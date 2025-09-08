#!/usr/bin/env python3
"""Full simulation of download functionality."""

import asyncio
import sys
import os
import logging
import tempfile
from datetime import datetime
import httpx
import html

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.api import JCYLAPIClient
from src.models.callback_map import callback_mapper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def simulate_file_download():
    """Simulate the exact file download process."""
    logger.info("🎬 Simulating file download process...")
    
    try:
        # Initialize API client
        api_client = JCYLAPIClient("https://analisis.datosabiertos.jcyl.es")
        
        # Step 1: Get a dataset with exports
        logger.info("📋 Step 1: Getting dataset with exports...")
        datasets, _ = await api_client.get_datasets(search="salud", limit=3)
        if not datasets:
            logger.error("❌ No datasets found")
            return False
        
        test_dataset = datasets[0]
        logger.info(f"✅ Using dataset: {test_dataset.title}")
        
        # Step 2: Get export formats
        logger.info("📊 Step 2: Getting export formats...")
        exports = await api_client.get_dataset_exports(test_dataset.dataset_id)
        if not exports:
            logger.error("❌ No exports found")
            return False
        
        # Find CSV export
        csv_export = None
        for export in exports:
            if export.format.lower() == 'csv':
                csv_export = export
                break
        
        if not csv_export:
            logger.error("❌ No CSV export found")
            return False
        
        logger.info(f"✅ Found CSV export: {csv_export.url}")
        
        # Step 3: Simulate callback construction
        logger.info("🔗 Step 3: Constructing callback data...")
        callback_data = f"download_file:{test_dataset.dataset_id}:{csv_export.format}:{csv_export.url}"
        logger.info(f"📝 Callback data: {callback_data}")
        
        # Use mapper if needed
        if len(callback_data.encode()) > 60:
            short_id = callback_mapper.get_short_id(callback_data)
            used_callback = f"s:{short_id}"
            logger.info(f"🔗 Using short callback: {used_callback}")
        else:
            used_callback = callback_data
            logger.info("📏 Callback is short enough, using directly")
        
        # Step 4: Simulate callback processing
        logger.info("⚙️  Step 4: Processing callback...")
        data = used_callback
        
        # Handle short IDs (simulate the handler logic)
        if data.startswith("s:"):
            short_id = data[2:]  # Remove "s:" prefix
            full_data = callback_mapper.get_full_data(short_id)
            if full_data:
                data = full_data
                logger.info("✅ Retrieved full data from mapper")
            else:
                logger.error("❌ Failed to retrieve full data")
                return False
        
        # Parse callback data
        parts = data.split(":", 3)
        if len(parts) < 4:
            logger.error(f"❌ Invalid callback format: {data}")
            return False
        
        dataset_id, file_format, file_url = parts[1], parts[2], parts[3]
        logger.info(f"✅ Parsed: dataset_id={dataset_id}, format={file_format}, url={file_url}")
        
        # Step 5: Download the file
        logger.info("⬇️  Step 5: Downloading file...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(file_url)
            response.raise_for_status()
            logger.info(f"✅ Download successful, size: {len(response.content)} bytes")
            
            # Check content type
            content_type = response.headers.get('content-type', 'unknown')
            logger.info(f"📄 Content-Type: {content_type}")
        
        # Step 6: Get dataset info for filename
        logger.info("📋 Step 6: Getting dataset info...")
        dataset = await api_client.get_dataset_info(dataset_id)
        logger.info(f"✅ Dataset info retrieved: {dataset.title}")
        
        # Step 7: Create filename
        logger.info("📝 Step 7: Creating filename...")
        safe_title = "".join(c for c in dataset.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title[:50]
        filename = f"{safe_title}.{file_format.lower()}"
        logger.info(f"✅ Generated filename: {filename}")
        
        # Step 8: Create temporary file
        logger.info("🗂️  Step 8: Creating temporary file...")
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_format.lower()}") as tmp_file:
            tmp_file.write(response.content)
            tmp_file_path = tmp_file.name
        logger.info(f"✅ Temporary file created: {tmp_file_path}")
        
        # Step 9: Simulate caption creation
        logger.info("📄 Step 9: Creating caption...")
        caption = (
            f"📎 <b>{html.escape(dataset.title)}</b>\n\n"
            f"📊 Formato: {file_format.upper()}\n"
            f"📅 Descargado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        if dataset.records_count:
            caption += f"\n📄 Registros: {dataset.records_count:,}"
        logger.info(f"✅ Caption created: {len(caption)} chars")
        
        # Step 10: Verify file exists and cleanup
        logger.info("🧹 Step 10: Cleanup...")
        if os.path.exists(tmp_file_path):
            file_size = os.path.getsize(tmp_file_path)
            logger.info(f"✅ Temporary file verified: {file_size} bytes")
            os.unlink(tmp_file_path)
            logger.info("✅ Temporary file cleaned up")
        else:
            logger.error("❌ Temporary file not found!")
            return False
        
        logger.info("🎉 Full simulation completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error in simulation: {e}", exc_info=True)
        return False
    
    finally:
        # Close API client
        await api_client.close()

async def main():
    """Main simulation function."""
    logger.info("🚀 Starting full download simulation...")
    
    success = await simulate_file_download()
    
    if success:
        logger.info("✅ Simulation completed successfully!")
        logger.info("🔧 The download functionality should work correctly!")
    else:
        logger.error("❌ Simulation failed!")
        logger.error("🔧 There may be an issue with the download functionality!")

if __name__ == "__main__":
    asyncio.run(main())