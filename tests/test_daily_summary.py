#!/usr/bin/env python3
"""Test script para el sistema de resúmenes diarios."""

import asyncio
import logging
import os
import sys
from datetime import date, timedelta

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.daily_summary import DailySummaryService
from src.models import DatabaseManager
from src.services.config import get_settings

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

async def main():
    """Probar el sistema de resúmenes diarios."""
    settings = get_settings()
    
    logger.info("=== INICIANDO PRUEBA DEL SISTEMA DE RESÚMENES DIARIOS ===")
    
    # Crear las tablas si no existen
    db_manager = DatabaseManager(settings.database_url)
    db_manager.create_tables()
    logger.info("Tablas de base de datos verificadas")
    
    # Inicializar servicio
    daily_service = DailySummaryService()
    
    try:
        # Probar para hoy
        today = date.today()
        logger.info(f"Procesando resumen para hoy: {today}")
        
        result = await daily_service.discover_and_track_new_datasets(today)
        
        logger.info(f"✅ Resumen creado exitosamente:")
        logger.info(f"  Fecha: {result['date']}")
        logger.info(f"  Datasets nuevos: {result['new_datasets_count']}")
        logger.info(f"  Estado: {result['status']}")
        
        if result['new_datasets_count'] > 0:
            logger.info("📄 Primeros datasets nuevos:")
            for i, dataset in enumerate(result.get('new_datasets', [])[:3]):
                logger.info(f"  {i+1}. {dataset['title']}")
                logger.info(f"      Publisher: {dataset.get('publisher', 'N/A')}")
                logger.info(f"      Themes: {dataset.get('themes', [])}")
        
        # Obtener el resumen formateado
        summary = await daily_service.get_daily_summary(today)
        if summary:
            message = daily_service.format_daily_summary_message(summary)
            logger.info(f"\n=== MENSAJE FORMATEADO ===\n{message}")
        
        # Probar también para ayer
        yesterday = today - timedelta(days=1)
        logger.info(f"\nProcesando resumen para ayer: {yesterday}")
        
        result_yesterday = await daily_service.discover_and_track_new_datasets(yesterday)
        logger.info(f"✅ Resumen de ayer: {result_yesterday['new_datasets_count']} datasets nuevos")
        
        # Obtener resúmenes recientes
        recent_summaries = await daily_service.get_recent_daily_summaries(7)
        logger.info(f"\n=== RESÚMENES RECIENTES ===")
        for summary in recent_summaries:
            logger.info(f"  {summary['date']}: {summary['new_datasets_count']} datasets nuevos")
        
    except Exception as e:
        logger.error(f"❌ Error en la prueba: {e}", exc_info=True)
    
    finally:
        await daily_service.close()
    
    logger.info("=== PRUEBA COMPLETADA ===")

if __name__ == "__main__":
    asyncio.run(main())