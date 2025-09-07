"""Daily summary service for detecting and reporting new datasets."""

import json
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from ..api import JCYLAPIClient
from ..models import DatabaseManager, KnownDataset, DailySummary
from .config import get_settings
from .alerts import clean_dataset_title, clean_publisher_name

logger = logging.getLogger(__name__)
settings = get_settings()


class DailySummaryService:
    """Service for managing daily summaries of new datasets."""
    
    def __init__(self):
        self.db_manager = DatabaseManager(settings.database_url)
        self.api_client = JCYLAPIClient()
    
    async def discover_and_track_new_datasets(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Discover new datasets for a specific date and create daily summary.
        
        Args:
            target_date: Date to process. If None, uses today.
            
        Returns:
            Dict with summary information
        """
        if target_date is None:
            target_date = date.today()
        
        date_str = target_date.strftime('%Y-%m-%d')
        logger.info(f"Processing daily summary for {date_str}")
        
        # Check if summary already exists
        session = self.db_manager.get_session()
        try:
            existing_summary = session.query(DailySummary).filter(
                DailySummary.date == date_str
            ).first()
            
            if existing_summary:
                logger.info(f"Daily summary for {date_str} already exists")
                return {
                    'date': date_str,
                    'new_datasets_count': existing_summary.new_datasets_count,
                    'status': 'already_exists'
                }
            
            # Get all current datasets from API (in batches)
            logger.info("Fetching all datasets from API...")
            all_datasets = []
            offset = 0
            limit = 1000
            
            while True:
                batch_datasets, total_estimate = await self.api_client.get_datasets(
                    limit=limit, 
                    offset=offset
                )
                
                if not batch_datasets:
                    break
                    
                all_datasets.extend(batch_datasets)
                offset += limit
                
                logger.info(f"Fetched {len(all_datasets)} datasets so far...")
                
                # If we got fewer than the limit, we're at the end
                if len(batch_datasets) < limit:
                    break
                
                # Safety check to avoid infinite loop
                if offset > 50000:  # Max reasonable number of datasets
                    logger.warning(f"Reached maximum offset {offset}, stopping")
                    break
            
            # Get known datasets from database
            known_dataset_ids = set()
            known_datasets = session.query(KnownDataset).all()
            for known in known_datasets:
                known_dataset_ids.add(known.dataset_id)
            
            logger.info(f"Found {len(all_datasets)} total datasets, {len(known_dataset_ids)} already known")
            
            # Identify new datasets
            new_datasets = []
            for dataset in all_datasets:
                if dataset.dataset_id not in known_dataset_ids:
                    new_datasets.append(dataset)
                    
                    # Add to known datasets
                    known_dataset = KnownDataset(
                        dataset_id=dataset.dataset_id,
                        title=dataset.title,
                        publisher=dataset.publisher,
                        themes=json.dumps(dataset.themes) if dataset.themes else "[]",
                        first_seen=datetime.utcnow()
                    )
                    session.add(known_dataset)
            
            logger.info(f"Discovered {len(new_datasets)} new datasets")
            
            # Create daily summary
            new_datasets_data = []
            for dataset in new_datasets:
                new_datasets_data.append({
                    'dataset_id': dataset.dataset_id,
                    'title': dataset.title,
                    'publisher': dataset.publisher,
                    'themes': dataset.themes,
                    'modified': dataset.modified,
                    'records_count': dataset.records_count
                })
            
            daily_summary = DailySummary(
                date=date_str,
                new_datasets_count=len(new_datasets),
                new_datasets=json.dumps(new_datasets_data),
                created_at=datetime.utcnow()
            )
            session.add(daily_summary)
            session.commit()
            
            logger.info(f"Created daily summary for {date_str} with {len(new_datasets)} new datasets")
            
            return {
                'date': date_str,
                'new_datasets_count': len(new_datasets),
                'new_datasets': new_datasets_data,
                'status': 'created'
            }
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating daily summary for {date_str}: {e}")
            raise
        finally:
            session.close()
    
    async def get_daily_summary(self, target_date: date) -> Optional[Dict[str, Any]]:
        """Get daily summary for a specific date."""
        date_str = target_date.strftime('%Y-%m-%d')
        session = self.db_manager.get_session()
        
        try:
            summary = session.query(DailySummary).filter(
                DailySummary.date == date_str
            ).first()
            
            if not summary:
                return None
            
            return {
                'date': summary.date,
                'new_datasets_count': summary.new_datasets_count,
                'new_datasets': json.loads(summary.new_datasets) if summary.new_datasets else [],
                'created_at': summary.created_at
            }
            
        finally:
            session.close()
    
    async def get_recent_daily_summaries(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent daily summaries."""
        session = self.db_manager.get_session()
        
        try:
            summaries = session.query(DailySummary).order_by(
                DailySummary.date.desc()
            ).limit(days).all()
            
            result = []
            for summary in summaries:
                result.append({
                    'date': summary.date,
                    'new_datasets_count': summary.new_datasets_count,
                    'new_datasets': json.loads(summary.new_datasets) if summary.new_datasets else [],
                    'created_at': summary.created_at
                })
            
            return result
            
        finally:
            session.close()
    
    def format_daily_summary_message(self, summary: Dict[str, Any]) -> str:
        """Format daily summary as a Telegram message."""
        date_str = summary['date']
        new_count = summary['new_datasets_count']
        new_datasets = summary['new_datasets']
        
        # Parse date for friendly format
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            months = [
                "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
            ]
            friendly_date = f"{date_obj.day} de {months[date_obj.month - 1]} de {date_obj.year}"
        except:
            friendly_date = date_str
        
        if new_count == 0:
            return f"📅 *Resumen del {friendly_date}*\n\n" \
                   f"ℹ️ No se añadieron datasets nuevos este día.\n\n" \
                   f"_Los datasets pueden haber sido actualizados, pero no se crearon completamente nuevos._"
        
        message = f"📅 *Resumen del {friendly_date}*\n\n" \
                  f"🆕 *{new_count} dataset{'s' if new_count != 1 else ''} completamente nuevo{'s' if new_count != 1 else ''}*\n\n"
        
        # Group by themes for better organization
        by_theme = {}
        for dataset in new_datasets[:10]:  # Show max 10
            themes = dataset.get('themes', [])
            theme = themes[0] if themes else 'Sin categoría'
            
            if theme not in by_theme:
                by_theme[theme] = []
            by_theme[theme].append(dataset)
        
        for theme, datasets in by_theme.items():
            message += f"📊 **{theme}**\n"
            for dataset in datasets:
                title = clean_dataset_title(dataset.get('title', 'Sin título'))
                publisher = clean_publisher_name(dataset.get('publisher', ''))
                
                message += f"  📄 *{title}*\n"
                if publisher and publisher != "Administración Pública":
                    message += f"      🏢 {publisher}\n"
                
                records = dataset.get('records_count', 0)
                if records > 0:
                    message += f"      📊 {records:,} registros\n"
                message += "\n"
        
        if len(new_datasets) > 10:
            message += f"... y {len(new_datasets) - 10} más.\n\n"
        
        message += "_Estos son datasets completamente nuevos, no actualizaciones de existentes._"
        
        return message
    
    async def close(self):
        """Close API client."""
        if hasattr(self.api_client, 'close'):
            await self.api_client.close()