"""Alert detection and notification system."""

import json
import logging
from datetime import datetime
from typing import List, Set, Dict, Any, Optional

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from ..api import JCYLAPIClient
from ..models import DatabaseManager, DatasetSnapshot, ThemeSnapshot
from .config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


def clean_dataset_title(title: str) -> str:
    """Clean dataset title by removing redundant text."""
    if not title:
        return "Sin título"
    
    # Remove common redundant phrases
    cleaned_title = title.strip()
    
    # List of phrases to remove (case insensitive)
    phrases_to_remove = [
        "de la Junta de Castilla y León",
        "de la Junta de Castilla y Leon",
        "Junta de Castilla y León",
        "Junta de Castilla y Leon",
        "de Castilla y León",
        "de Castilla y Leon"
    ]
    
    for phrase in phrases_to_remove:
        # Remove at the end of the title
        if cleaned_title.lower().endswith(phrase.lower()):
            cleaned_title = cleaned_title[:-len(phrase)].strip()
        
        # Remove in the middle or beginning, being careful with spacing
        cleaned_title = cleaned_title.replace(f" {phrase} ", " ")
        cleaned_title = cleaned_title.replace(f" {phrase}", "")
        cleaned_title = cleaned_title.replace(f"{phrase} ", "")
        
        # Case insensitive replacements
        import re
        cleaned_title = re.sub(re.escape(phrase), "", cleaned_title, flags=re.IGNORECASE)
    
    # Clean up extra spaces and punctuation
    cleaned_title = re.sub(r'\s+', ' ', cleaned_title)  # Multiple spaces to single
    cleaned_title = cleaned_title.strip(' ,-')  # Remove trailing spaces, commas, dashes
    
    return cleaned_title if cleaned_title else "Sin título"


def clean_publisher_name(publisher: str) -> str:
    """Clean publisher name by removing redundant text."""
    if not publisher:
        return ""
    
    # Remove common redundant phrases
    cleaned_publisher = publisher.strip()
    
    # List of phrases to remove (case insensitive)
    phrases_to_remove = [
        "Junta de Castilla y León",
        "Junta de Castilla y Leon",
        "de la Junta de Castilla y León", 
        "de la Junta de Castilla y Leon",
        "- Junta de Castilla y León",
        "- Junta de Castilla y Leon"
    ]
    
    for phrase in phrases_to_remove:
        # Case insensitive replacements
        import re
        cleaned_publisher = re.sub(re.escape(phrase), "", cleaned_publisher, flags=re.IGNORECASE)
    
    # Clean up extra spaces and punctuation
    cleaned_publisher = re.sub(r'\s+', ' ', cleaned_publisher)  # Multiple spaces to single
    cleaned_publisher = cleaned_publisher.strip(' ,-')  # Remove trailing spaces, commas, dashes
    
    # If publisher becomes empty or too short after cleaning, return a generic name
    if not cleaned_publisher or len(cleaned_publisher.strip()) < 3:
        return "Administración Pública"
    
    return cleaned_publisher


def format_date_for_user(date_string: str) -> str:
    """Format a date string to be user-friendly in Spanish."""
    if not date_string or date_string == "Dato no disponible":
        return "Sin fecha disponible"
    
    try:
        # Try different date formats
        date_obj = None
        
        # Format: dd/mm/yyyy
        if "/" in date_string:
            try:
                date_obj = datetime.strptime(date_string, "%d/%m/%Y")
            except ValueError:
                try:
                    date_obj = datetime.strptime(date_string, "%Y/%m/%d")
                except ValueError:
                    pass
        
        # Format: yyyy-mm-dd or ISO format
        elif "-" in date_string:
            try:
                if "T" in date_string:
                    # ISO format with time
                    date_string_clean = date_string.replace("Z", "+00:00")
                    date_obj = datetime.fromisoformat(date_string_clean)
                else:
                    # Simple date format
                    date_obj = datetime.strptime(date_string, "%Y-%m-%d")
            except ValueError:
                pass
        
        if date_obj:
            # Format as "DD de MONTH de YYYY a las HH:MM" or just "DD de MONTH de YYYY"
            months = [
                "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
            ]
            
            day = date_obj.day
            month = months[date_obj.month - 1]
            year = date_obj.year
            
            if date_obj.hour != 0 or date_obj.minute != 0:
                # Include time if it's not midnight
                return f"{day} de {month} de {year} a las {date_obj.hour:02d}:{date_obj.minute:02d}"
            else:
                return f"{day} de {month} de {year}"
        
        # If we can't parse it, return the original but cleaned up
        return date_string.strip()
        
    except Exception:
        return date_string.strip() if date_string else "Sin fecha disponible"


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
            await self._check_keyword_changes()
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
        datasets, _ = await self.api_client.get_datasets(theme=theme_name, limit=1000)  # Get all
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
        
        # Check for changes - ONLY alert on data updates, not metadata
        changed = False
        
        if (latest_snapshot.data_processed != dataset.data_processed and 
            dataset.data_processed and dataset.data_processed != "Dato no disponible"):
            changed = True
            logger.info(f"Dataset {dataset_id} - data_processed changed: {latest_snapshot.data_processed} -> {dataset.data_processed}")
            logger.info("This is a DATA update (not just metadata) - will trigger alert")
        
        # We no longer alert on metadata changes, only log them
        if (latest_snapshot.metadata_processed != dataset.metadata_processed and 
            dataset.metadata_processed and dataset.metadata_processed != "Dato no disponible"):
            logger.info(f"Dataset {dataset_id} - metadata_processed changed (no alert): {latest_snapshot.metadata_processed} -> {dataset.metadata_processed}")
        
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

    async def _send_paginated_notifications(
        self, 
        subscribers: List, 
        datasets: List, 
        title: str,
        notification_type: str,
        theme_name: str = None
    ) -> None:
        """Send single notification with navigable buttons for each dataset."""
        if not datasets:
            return
            
        # Send to all subscribers
        for subscription in subscribers:
            session = self.db_manager.get_session()
            try:
                from ..models import User
                user = session.query(User).filter_by(id=subscription.user_id).first()
                if user:
                    # Store alert data for navigation
                    from ..bot.handlers import alert_sessions
                    alert_sessions[user.telegram_id] = {
                        'datasets': datasets,
                        'title': title,
                        'alert_type': notification_type,
                        'theme_name': theme_name
                    }
                    
                    # Send navigable alert message
                    await self._send_navigable_alert(
                        user_id=user.telegram_id,
                        datasets=datasets,
                        title=title,
                        current_index=0,
                        alert_type=notification_type,
                        theme_name=theme_name
                    )
                    logger.info(f"Navigable alert sent to user {user.telegram_id}")
            except Exception as e:
                logger.error(f"Failed to send alert to user {subscription.user_id}: {e}")
            finally:
                session.close()
                
    async def _send_navigable_alert(
        self,
        user_id: int,
        datasets: List,
        title: str,
        current_index: int = 0,
        alert_type: str = "",
        theme_name: str = None
    ) -> None:
        """Send a single alert message with navigation buttons."""
        if not datasets:
            return
            
        current_dataset = datasets[current_index]
        total_datasets = len(datasets)
        
        # Create message for current dataset
        title_text = clean_dataset_title(current_dataset.title)
        publisher_text = clean_publisher_name(current_dataset.publisher)
        formatted_date = format_date_for_user(current_dataset.data_processed)
        
        message = f"{title} ({current_index + 1}/{total_datasets})\n\n"
        message += f"📄 *{title_text}*\n"
        
        if publisher_text and publisher_text != "Administración Pública":
            message += f"🏢 {publisher_text}\n"
            
        message += f"📅 *Datos actualizados:* {formatted_date}\n"
        message += f"📊 *Registros:* {current_dataset.records_count:,}\n\n"
        
        if total_datasets > 1:
            message += f"📋 Usa los botones para navegar entre los {total_datasets} datasets"
        else:
            message += "Usa los botones para más acciones."
        
        # Create navigation keyboard
        keyboard = []
        
        if total_datasets > 1:
            nav_row = []
            if current_index > 0:
                nav_row.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"alert_nav:{current_index-1}"))
            if current_index < total_datasets - 1:
                nav_row.append(InlineKeyboardButton("➡️ Siguiente", callback_data=f"alert_nav:{current_index+1}"))
            
            if nav_row:
                keyboard.append(nav_row)
        
        # Add action buttons
        keyboard.append([
            InlineKeyboardButton("📋 Ver detalles", callback_data=f"dataset:{current_dataset.dataset_id}"),
            InlineKeyboardButton("🏠 Inicio", callback_data="start")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="Markdown",
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Failed to send navigable alert to user {user_id}: {e}")

    async def _notify_new_datasets_in_theme(self, theme_name: str, new_dataset_ids: Set[str]) -> None:
        """Notify users about new datasets in a theme with pagination."""
        subscribers = self.db_manager.get_subscriptions_by_type("theme", theme_name)
        
        if not subscribers:
            return
        
        logger.info(f"Notifying {len(subscribers)} users about {len(new_dataset_ids)} new datasets in theme '{theme_name}'")
        
        # Get dataset details for all new datasets
        datasets = []
        for dataset_id in list(new_dataset_ids):
            try:
                dataset = await self.api_client.get_dataset_info(dataset_id)
                if dataset:
                    datasets.append(dataset)
            except Exception as e:
                logger.error(f"Error getting dataset {dataset_id}: {e}")
        
        if not datasets:
            return
        
        # Send notifications with pagination
        await self._send_paginated_notifications(
            subscribers=subscribers,
            datasets=datasets,
            title=f"🆕 *Nuevos datasets en {theme_name}*",
            notification_type="new_theme_datasets",
            theme_name=theme_name
        )

    async def _notify_changed_datasets_in_theme(self, theme_name: str, changed_datasets: List) -> None:
        """Notify users about changed datasets in a theme with pagination."""
        subscribers = self.db_manager.get_subscriptions_by_type("theme", theme_name)
        
        if not subscribers:
            return
        
        logger.info(f"Notifying {len(subscribers)} users about {len(changed_datasets)} changed datasets in theme '{theme_name}'")
        
        # Send notifications with pagination
        await self._send_paginated_notifications(
            subscribers=subscribers,
            datasets=changed_datasets,
            title=f"🔄 *Datasets actualizados en {theme_name}*",
            notification_type="changed_theme_datasets",
            theme_name=theme_name
        )

    async def _notify_dataset_changed(self, dataset_id: str, dataset) -> None:
        """Notify users about specific dataset changes with improved formatting."""
        subscribers = self.db_manager.get_subscriptions_by_type("dataset", dataset_id)
        
        if not subscribers:
            return
        
        logger.info(f"Notifying {len(subscribers)} users about changes in dataset '{dataset_id}'")
        
        # Clean and format title, publisher and date
        title_text = clean_dataset_title(dataset.title)
        publisher_text = clean_publisher_name(dataset.publisher)
        formatted_date = format_date_for_user(dataset.data_processed)
        
        # Create message with improved formatting
        message = f"🔄 *Datos del dataset actualizados*\n\n📄 *{title_text}*\n"
        
        if publisher_text and publisher_text != "Administración Pública":
            message += f"🏢 {publisher_text}\n"
            
        message += (
            f"📅 *Datos actualizados:* {formatted_date}\n"
            f"📊 *Registros:* {dataset.records_count:,}\n\n"
            f"Usa /start para ver los detalles actualizados."
        )
        
        # Send notifications
        for subscription in subscribers:
            session = self.db_manager.get_session()
            try:
                from ..models import User
                user = session.query(User).filter_by(id=subscription.user_id).first()
                if user:
                    await self.bot.send_message(
                        chat_id=user.telegram_id,
                        text=message,
                        parse_mode="Markdown"
                    )
            except Exception as e:
                logger.error(f"Error sending notification to user {subscription.user_id}: {e}")
            finally:
                session.close()

    async def _check_keyword_changes(self) -> None:
        """Check for new datasets matching keyword subscriptions."""
        logger.info("Checking keyword changes...")
        
        # Get all keyword subscriptions
        session = self.db_manager.get_session()
        try:
            from ..models import Subscription
            keyword_subscriptions = session.query(Subscription).filter(
                Subscription.subscription_type == "keyword",
                Subscription.is_active == True
            ).all()
            
            if not keyword_subscriptions:
                logger.info("No active keyword subscriptions")
                return
            
            # Get unique keywords
            keywords = set(sub.subscription_id for sub in keyword_subscriptions)
            
            for keyword in keywords:
                try:
                    await self._check_single_keyword(keyword)
                except Exception as e:
                    logger.error(f"Error checking keyword {keyword}: {e}")
                    continue
            
        finally:
            session.close()

    async def _check_single_keyword(self, keyword: str) -> None:
        """Check for new datasets matching a specific keyword."""
        # Search for datasets containing the keyword
        try:
            # Search in recent datasets (last 100)
            recent_datasets, _ = await self.api_client.get_datasets(limit=100, offset=0)
            matching_datasets = []
            
            for dataset in recent_datasets:
                # Check if keyword appears in title or description
                title_match = keyword.lower() in dataset.title.lower() if dataset.title else False
                desc_match = keyword.lower() in dataset.description.lower() if dataset.description else False
                
                if title_match or desc_match:
                    # Check if this is a "new" dataset (modified in last 7 days)
                    if dataset.modified and dataset.modified != "Dato no disponible":
                        try:
                            from datetime import datetime, timedelta
                            modified_date = None
                            if "/" in dataset.modified:
                                modified_date = datetime.strptime(dataset.modified, "%d/%m/%Y")
                            elif "-" in dataset.modified:
                                if "T" in dataset.modified:
                                    modified_date = datetime.fromisoformat(dataset.modified.replace("Z", "+00:00"))
                                else:
                                    modified_date = datetime.strptime(dataset.modified, "%Y-%m-%d")
                            
                            if modified_date and modified_date >= datetime.now() - timedelta(days=7):
                                matching_datasets.append(dataset)
                        except:
                            continue
            
            if matching_datasets:
                await self._notify_keyword_matches(keyword, matching_datasets)
                
        except Exception as e:
            logger.error(f"Error searching for keyword {keyword}: {e}")

    async def _notify_keyword_matches(self, keyword: str, matching_datasets: list) -> None:
        """Notify users about datasets matching their keyword alerts with pagination."""
        subscribers = self.db_manager.get_subscriptions_by_type("keyword", keyword)
        
        if not subscribers:
            return
        
        logger.info(f"Notifying {len(subscribers)} users about {len(matching_datasets)} datasets matching keyword '{keyword}'")
        
        # Send notifications with pagination
        await self._send_paginated_notifications(
            subscribers=subscribers,
            datasets=matching_datasets,
            title=f"🔍 *Nuevos datasets con '{keyword}'*",
            notification_type="keyword_matches",
            theme_name=None
        )


async def run_alert_check() -> None:
    """Standalone function to run alert check."""
    alert_service = AlertService()
    try:
        await alert_service.check_and_notify_changes()
    finally:
        await alert_service.close()