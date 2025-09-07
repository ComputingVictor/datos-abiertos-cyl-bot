#!/usr/bin/env python3
"""Test script para verificar el sistema de alertas manualmente."""

import asyncio
import logging
import os
import sys

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.alerts import AlertService
from src.models import DatabaseManager
from src.services.config import get_settings

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

async def main():
    """Ejecutar verificación de alertas manualmente."""
    settings = get_settings()
    
    logger.info("=== INICIANDO PRUEBA DEL SISTEMA DE ALERTAS ===")
    logger.info(f"Alertas habilitadas: {settings.alerts_enabled}")
    logger.info(f"Intervalo de verificación: {settings.alerts_check_interval_hours} horas")
    
    # Verificar base de datos
    db_manager = DatabaseManager(settings.database_url)
    session = db_manager.get_session()
    
    try:
        from src.models import Subscription, User
        
        # Contar usuarios activos
        users_count = session.query(User).filter(User.is_active == True).count()
        logger.info(f"Usuarios activos: {users_count}")
        
        # Contar suscripciones activas por tipo
        theme_subs = session.query(Subscription).filter(
            Subscription.subscription_type == "theme",
            Subscription.is_active == True
        ).count()
        
        dataset_subs = session.query(Subscription).filter(
            Subscription.subscription_type == "dataset", 
            Subscription.is_active == True
        ).count()
        
        keyword_subs = session.query(Subscription).filter(
            Subscription.subscription_type == "keyword",
            Subscription.is_active == True
        ).count()
        
        logger.info(f"Suscripciones activas:")
        logger.info(f"  - Temas: {theme_subs}")
        logger.info(f"  - Datasets: {dataset_subs}")
        logger.info(f"  - Keywords: {keyword_subs}")
        
        if theme_subs + dataset_subs + keyword_subs == 0:
            logger.warning("¡No hay suscripciones activas! Las alertas no se enviarán.")
            return
        
        # Mostrar algunas suscripciones de ejemplo
        if theme_subs > 0:
            sample_themes = session.query(Subscription).filter(
                Subscription.subscription_type == "theme",
                Subscription.is_active == True
            ).limit(3).all()
            
            logger.info("Ejemplos de suscripciones a temas:")
            for sub in sample_themes:
                user = session.query(User).filter(User.id == sub.user_id).first()
                logger.info(f"  - Usuario {user.telegram_id}: {sub.subscription_name}")
        
    finally:
        session.close()
    
    # Ejecutar verificación de alertas
    logger.info("\n=== EJECUTANDO VERIFICACIÓN DE ALERTAS ===")
    alert_service = AlertService()
    
    try:
        await alert_service.check_and_notify_changes()
        logger.info("✅ Verificación de alertas completada")
    except Exception as e:
        logger.error(f"❌ Error en verificación de alertas: {e}", exc_info=True)
    finally:
        await alert_service.close()
        
    logger.info("=== PRUEBA COMPLETADA ===")

if __name__ == "__main__":
    asyncio.run(main())