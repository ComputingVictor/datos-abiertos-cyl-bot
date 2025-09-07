#!/usr/bin/env python3
"""Debug test for catalog export."""

import asyncio
import logging
import os
import sys
import pandas as pd
import tempfile

# Add the root directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api import JCYLAPIClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_catalog_debug():
    """Debug the catalog export process step by step."""
    
    api_client = JCYLAPIClient()
    
    try:
        logger.info("=== STEP 1: Fetch datasets ===")
        datasets, total = await api_client.get_datasets(limit=3, offset=0)
        logger.info(f"Got {len(datasets)} datasets out of {total}")
        
        if not datasets:
            logger.error("No datasets returned!")
            return
        
        logger.info("=== STEP 2: Prepare data ===")
        catalog_data = []
        for i, dataset in enumerate(datasets):
            logger.info(f"Processing dataset {i+1}: {dataset.dataset_id}")
            
            row_data = {
                'ID': dataset.dataset_id or '',
                'Título': dataset.title or 'Sin título',
                'Descripción': (dataset.description or 'Sin descripción')[:100],
                'Editor': dataset.publisher or 'Sin editor',
                'Temas': ', '.join(dataset.themes) if dataset.themes else 'Sin temas',
                'Palabras Clave': ', '.join(dataset.keywords) if dataset.keywords else 'Sin palabras clave',
                'Última Modificación': dataset.modified or 'Sin fecha',
                'Registros': dataset.records_count if dataset.records_count is not None else 0,
                'Licencia': dataset.license or 'Sin licencia'
            }
            
            logger.info(f"Row data: {row_data}")
            catalog_data.append(row_data)
        
        logger.info("=== STEP 3: Create DataFrame ===")
        df = pd.DataFrame(catalog_data)
        logger.info(f"DataFrame shape: {df.shape}")
        logger.info(f"DataFrame columns: {list(df.columns)}")
        logger.info(f"DataFrame head:\n{df.head()}")
        
        if df.empty:
            logger.error("DataFrame is EMPTY!")
            return
        
        logger.info("=== STEP 4: Create Excel file ===")
        filename = "debug_catalog.xlsx"
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Test Catalog', index=False)
            logger.info("Excel file written successfully")
        
        # Check file size
        file_size = os.path.getsize(filename)
        logger.info(f"Excel file created: {filename} ({file_size} bytes)")
        
        logger.info("=== SUCCESS ===")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    
    finally:
        await api_client.close()

if __name__ == "__main__":
    asyncio.run(test_catalog_debug())