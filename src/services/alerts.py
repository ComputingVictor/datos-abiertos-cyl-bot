"""Alert detection and notification system."""

import json
import logging
from datetime import datetime
from typing import List, Set, Dict, Any, Optional

from telegram import Bot

from ..api import JCYLAPIClient
from ..models import DatabaseManager, DatasetSnapshot, ThemeSnapshot
from .config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class AlertService:
    def __init__(self):
        self.db_manager = DatabaseManager(settings.database_url)
        self.api_client = JCYLAPIClient(settings.jcyl_api_base_url)
        self.bot = Bot(settings.telegram_bot_token)

    async def close(self) -> None:
        """Close API client."""
        await self.api_client.close()

    async def check_and_notify_changes(self) -> None:
        """Check for changes and notify subscribers."""
        if not settings.alerts_enabled:
            logger.info("Alerts are disabled")
            return

        logger.info("Starting change detection check")
        
        try:
            await self._check_theme_changes()
            await self._check_dataset_changes()
        except Exception as e:
            logger.error(f"Error in change detection: {e}")

    async def _check_theme_changes(self) -> None:
        """Check for changes in themes (new datasets)."""
        logger.info("Checking theme changes...")
        
        # Get all theme subscriptions
        session = self.db_manager.get_session()
        try:
            from ..models import Subscription
            theme_subscriptions = session.query(Subscription).filter(
                Subscription.subscription_type == "theme",
                Subscription.is_active == True
            ).all()
            
            if not theme_subscriptions:
                logger.info("No active theme subscriptions")
                return
            
            # Get unique themes
            themes = set(sub.subscription_id for sub in theme_subscriptions)
            
            for theme_name in themes:
                try:
                    await self._check_single_theme(theme_name)
                except Exception as e:
                    logger.error(f"Error checking theme {theme_name}: {e}")
                    continue
            
        finally:
            session.close()

    async def _check_single_theme(self, theme_name: str) -> None:
        """Check changes for a single theme."""
        # Get current datasets in theme
        datasets = await self.api_client.get_datasets(theme=theme_name, limit=1000)  # Get all
        current_dataset_ids = set(d.dataset_id for d in datasets)
        
        # Get latest snapshot
        latest_snapshot = self.db_manager.get_latest_theme_snapshot(theme_name)
        
        if latest_snapshot:
            previous_dataset_ids = set(json.loads(latest_snapshot.dataset_ids))
            
            # Check for new datasets
            new_datasets = current_dataset_ids - previous_dataset_ids
            if new_datasets:
                await self._notify_new_datasets_in_theme(theme_name, new_datasets)
            
            # Check for changes in existing datasets
            changed_datasets = []
            for dataset_id in current_dataset_ids & previous_dataset_ids:
                try:
                    dataset = await self.api_client.get_dataset_info(dataset_id)
                    if dataset and await self._has_dataset_changed(dataset_id, dataset):
                        changed_datasets.append(dataset)
                except Exception as e:
                    logger.error(f"Error checking dataset {dataset_id}: {e}")
                    continue
            
            if changed_datasets:
                await self._notify_changed_datasets_in_theme(theme_name, changed_datasets)
        
        # Save new snapshot
        self.db_manager.save_theme_snapshot(theme_name, list(current_dataset_ids))

    async def _check_dataset_changes(self) -> None:
        """Check for changes in specific dataset subscriptions."""
        logger.info("Checking dataset changes...")
        
        # Get all dataset subscriptions
        session = self.db_manager.get_session()
        try:
            from ..models import Subscription
            dataset_subscriptions = session.query(Subscription).filter(
                Subscription.subscription_type == "dataset",
                Subscription.is_active == True
            ).all()
            
            if not dataset_subscriptions:
                logger.info("No active dataset subscriptions")
                return
            
            # Get unique dataset IDs
            dataset_ids = set(sub.subscription_id for sub in dataset_subscriptions)
            
            for dataset_id in dataset_ids:
                try:
                    await self._check_single_dataset(dataset_id)
                except Exception as e:
                    logger.error(f"Error checking dataset {dataset_id}: {e}")
                    continue
            
        finally:
            session.close()

    async def _check_single_dataset(self, dataset_id: str) -> None:
        """Check changes for a single dataset."""
        dataset = await self.api_client.get_dataset_info(dataset_id)
        if not dataset:
            logger.warning(f"Dataset {dataset_id} not found")
            return
        
        if await self._has_dataset_changed(dataset_id, dataset):
            await self._notify_dataset_changed(dataset_id, dataset)

    async def _has_dataset_changed(self, dataset_id: str, dataset) -> bool:
        """Check if a dataset has changed since last snapshot."""
        latest_snapshot = self.db_manager.get_latest_dataset_snapshot(dataset_id)
        
        if not latest_snapshot:
            # No previous snapshot, save current state
            self.db_manager.save_dataset_snapshot(
                dataset_id=dataset_id,
                modified=dataset.modified,
                data_processed=dataset.data_processed,
                metadata_processed=dataset.metadata_processed,
                records_count=dataset.records_count,
                themes=dataset.themes
            )
            return False
        
        # Check for changes
        changed = False
        
        if (latest_snapshot.modified != dataset.modified and 
            dataset.modified and dataset.modified != "Dato no disponible"):
            changed = True
            logger.info(f"Dataset {dataset_id} - modified changed: {latest_snapshot.modified} -> {dataset.modified}")
        
        if (latest_snapshot.data_processed != dataset.data_processed and 
            dataset.data_processed and dataset.data_processed != "Dato no disponible"):
            changed = True
            logger.info(f"Dataset {dataset_id} - data_processed changed: {latest_snapshot.data_processed} -> {dataset.data_processed}")
        
        if (latest_snapshot.metadata_processed != dataset.metadata_processed and 
            dataset.metadata_processed and dataset.metadata_processed != "Dato no disponible"):
            changed = True
            logger.info(f"Dataset {dataset_id} - metadata_processed changed: {latest_snapshot.metadata_processed} -> {dataset.metadata_processed}")
        
        if latest_snapshot.records_count != dataset.records_count:
            changed = True
            logger.info(f"Dataset {dataset_id} - records_count changed: {latest_snapshot.records_count} -> {dataset.records_count}")
        
        if changed:
            # Save new snapshot
            self.db_manager.save_dataset_snapshot(
                dataset_id=dataset_id,
                modified=dataset.modified,
                data_processed=dataset.data_processed,
                metadata_processed=dataset.metadata_processed,
                records_count=dataset.records_count,
                themes=dataset.themes
            )
        
        return changed

    async def _notify_new_datasets_in_theme(self, theme_name: str, new_dataset_ids: Set[str]) -> None:
        """Notify users about new datasets in a theme."""
        subscribers = self.db_manager.get_subscriptions_by_type("theme", theme_name)
        
        if not subscribers:
            return
        
        logger.info(f"Notifying {len(subscribers)} users about {len(new_dataset_ids)} new datasets in theme '{theme_name}'")
        
        # Get dataset details
        datasets = []
        for dataset_id in list(new_dataset_ids)[:5]:  # Limit to first 5
            try:
                dataset = await self.api_client.get_dataset_info(dataset_id)
                if dataset:
                    datasets.append(dataset)
            except Exception as e:
                logger.error(f"Error getting dataset {dataset_id}: {e}")
        
        if not datasets:
            return
        
        # Create message
        message = f"🆕 *Nuevos datasets en {theme_name}*\n\n"
        
        for dataset in datasets:
            title = dataset.title[:50] + "..." if len(dataset.title) > 50 else dataset.title
            message += f"📄 *{title}*\n"
            message += f"🏢 {dataset.publisher}\n"
            message += f"📅 {dataset.modified}\n\n"
        
        if len(new_dataset_ids) > len(datasets):
            message += f"... y {len(new_dataset_ids) - len(datasets)} más.\n\n"
        
        message += "Usa /start para explorar los nuevos datasets."
        
        # Send notifications
        for subscription in subscribers:
            try:
                user = self.db_manager.get_session().query(self.db_manager.User).filter_by(id=subscription.user_id).first()
                if user:
                    await self.bot.send_message(
                        chat_id=user.telegram_id,
                        text=message,
                        parse_mode="Markdown"
                    )
            except Exception as e:
                logger.error(f"Error sending notification to user {subscription.user_id}: {e}")

    async def _notify_changed_datasets_in_theme(self, theme_name: str, changed_datasets: List) -> None:
        """Notify users about changed datasets in a theme."""
        subscribers = self.db_manager.get_subscriptions_by_type("theme", theme_name)
        
        if not subscribers:
            return
        
        logger.info(f"Notifying {len(subscribers)} users about {len(changed_datasets)} changed datasets in theme '{theme_name}'")
        
        # Create message
        message = f"🔄 *Datasets actualizados en {theme_name}*\n\n"
        
        for dataset in changed_datasets[:3]:  # Limit to first 3
            title = dataset.title[:50] + "..." if len(dataset.title) > 50 else dataset.title
            message += f"📄 *{title}*\n"
            message += f"🏢 {dataset.publisher}\n"
            message += f"📅 {dataset.modified}\n\n"
        
        if len(changed_datasets) > 3:
            message += f"... y {len(changed_datasets) - 3} más.\n\n"
        
        message += "Usa /start para ver los datasets actualizados."
        
        # Send notifications
        for subscription in subscribers:
            try:
                user = self.db_manager.get_session().query(self.db_manager.User).filter_by(id=subscription.user_id).first()
                if user:
                    await self.bot.send_message(
                        chat_id=user.telegram_id,
                        text=message,
                        parse_mode="Markdown"
                    )
            except Exception as e:
                logger.error(f"Error sending notification to user {subscription.user_id}: {e}")

    async def _notify_dataset_changed(self, dataset_id: str, dataset) -> None:
        """Notify users about specific dataset changes."""
        subscribers = self.db_manager.get_subscriptions_by_type("dataset", dataset_id)
        
        if not subscribers:
            return
        
        logger.info(f"Notifying {len(subscribers)} users about changes in dataset '{dataset_id}'")
        
        # Create message
        title = dataset.title[:50] + "..." if len(dataset.title) > 50 else dataset.title
        message = (
            f"🔄 *Dataset actualizado*\n\n"
            f"📄 *{title}*\n"
            f"🏢 {dataset.publisher}\n"
            f"📅 Modificado: {dataset.modified}\n"
            f"📊 Registros: {dataset.records_count}\n\n"
            f"Usa /start para ver los detalles actualizados."
        )
        
        # Send notifications
        for subscription in subscribers:
            try:
                user = self.db_manager.get_session().query(self.db_manager.User).filter_by(id=subscription.user_id).first()
                if user:
                    await self.bot.send_message(
                        chat_id=user.telegram_id,
                        text=message,
                        parse_mode="Markdown"
                    )
            except Exception as e:
                logger.error(f"Error sending notification to user {subscription.user_id}: {e}")


async def run_alert_check() -> None:
    """Standalone function to run alert check."""
    alert_service = AlertService()
    try:
        await alert_service.check_and_notify_changes()
    finally:
        await alert_service.close()