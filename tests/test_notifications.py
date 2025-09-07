#!/usr/bin/env python3
"""Test script para forzar el envío de notificaciones."""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.alerts import AlertService
from src.models import DatabaseManager, ThemeSnapshot
from src.services.config import get_settings

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

async def create_fake_snapshot():
    """Crear un snapshot antiguo para forzar una diferencia."""
    settings = get_settings()
    db_manager = DatabaseManager(settings.database_url)
    
    # Crear snapshot falso para "Empleo" con menos datasets de los que hay realmente
    fake_dataset_ids = ["test1", "test2", "test3"]  # Solo 3 datasets en lugar de los 23 reales
    
    session = db_manager.get_session()
    try:
        # Eliminar snapshots existentes para "Empleo"
        existing = session.query(ThemeSnapshot).filter(
            ThemeSnapshot.theme_name == "Empleo"
        ).all()
        
        for snapshot in existing:
            session.delete(snapshot)
        
        # Crear nuevo snapshot falso
        fake_snapshot = ThemeSnapshot(
            theme_name="Empleo",
            dataset_ids=json.dumps(fake_dataset_ids),
            dataset_count=len(fake_dataset_ids),
            created_at=datetime.utcnow()
        )
        session.add(fake_snapshot)
        session.commit()
        
        logger.info(f"Snapshot falso creado para Empleo con {len(fake_dataset_ids)} datasets")
        
    finally:
        session.close()

async def test_notifications():
    """Probar el envío de notificaciones."""
    logger.info("=== CREANDO CONDICIONES PARA NOTIFICACIÓN ===")
    await create_fake_snapshot()
    
    logger.info("=== EJECUTANDO VERIFICACIÓN DE ALERTAS ===")
    alert_service = AlertService()
    
    try:
        await alert_service.check_and_notify_changes()
        logger.info("✅ Verificación completada - deberían haberse enviado notificaciones")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
    finally:
        await alert_service.close()

if __name__ == "__main__":
    asyncio.run(test_notifications())