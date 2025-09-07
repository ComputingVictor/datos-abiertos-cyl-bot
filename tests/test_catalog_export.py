#!/usr/bin/env python3
"""Test script for catalog export functionality."""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Add the root directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api import JCYLAPIClient
import pandas as pd
import tempfile

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

async def test_catalog_export():
    """Test the catalog export functionality."""
    logger.info("=== TESTING CATALOG EXPORT ===")
    
    api_client = JCYLAPIClient()
    
    try:
        # Get sample datasets for testing (small amount)
        logger.info("Fetching sample datasets...")
        datasets, total_estimate = await api_client.get_datasets(limit=10, offset=0)
        logger.info(f"Retrieved {len(datasets)} datasets out of {total_estimate} total")
        
        if not datasets:
            logger.error("No datasets retrieved!")
            return
        
        # Prepare data for Excel
        logger.info("Preparing Excel data...")
        catalog_data = []
        for dataset in datasets:
            catalog_data.append({
                'ID': dataset.dataset_id,
                'Título': dataset.title,
                'Descripción': dataset.description[:100] + "..." if len(dataset.description) > 100 else dataset.description,
                'Editor': dataset.publisher,
                'Temas': ', '.join(dataset.themes) if dataset.themes else '',
                'Palabras Clave': ', '.join(dataset.keywords) if dataset.keywords else '',
                'Última Modificación': dataset.modified,
                'Registros': dataset.records_count,
                'Licencia': dataset.license
            })
        
        # Create DataFrame
        logger.info("Creating DataFrame...")
        df = pd.DataFrame(catalog_data)
        logger.info(f"DataFrame created with {len(df)} rows and {len(df.columns)} columns")
        
        # Create Excel file
        current_date = datetime.now().strftime("%Y-%m-%d")
        filename = f"test_catalogo_datos_abiertos_cyl_{current_date}.xlsx"
        
        logger.info(f"Creating Excel file: {filename}")
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            with pd.ExcelWriter(tmp_file.name, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Catálogo Completo', index=False)
                
                # Auto-adjust column widths
                worksheet = writer.sheets['Catálogo Completo']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # Copy to final filename
            import shutil
            shutil.copy2(tmp_file.name, filename)
            os.unlink(tmp_file.name)
        
        logger.info(f"✅ Excel file created successfully: {filename}")
        logger.info(f"File size: {os.path.getsize(filename)} bytes")
        
        # Show first few rows
        logger.info("Sample data:")
        for i, row in df.head(3).iterrows():
            logger.info(f"  Row {i+1}: {row['Título'][:50]}...")
        
    except Exception as e:
        logger.error(f"❌ Error in catalog export test: {e}", exc_info=True)
    
    finally:
        await api_client.close()
    
    logger.info("=== TEST COMPLETED ===")

if __name__ == "__main__":
    asyncio.run(test_catalog_export())