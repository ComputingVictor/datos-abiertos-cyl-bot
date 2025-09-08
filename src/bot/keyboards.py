"""Telegram bot keyboard utilities."""

from typing import List, Optional, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from ..api import Facet, Dataset, ExportFormat
from ..api.client import format_user_friendly_date
from ..models.callback_map import callback_mapper


def create_themes_keyboard(themes: List[Facet], page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
    """Create keyboard with themes (categories)."""
    keyboard = []
    
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_themes = themes[start_idx:end_idx]
    
    # Emoji mapping for different themes/categories - each category has a unique, intuitive emoji
    theme_emojis = {
        'salud': '🏥',
        'sector público': '🏛️', 
        'cultura y ocio': '🎭',
        'cultura': '🎨',
        'ocio': '🎪',
        'medio rural y pesca': '🚜',
        'medio rural': '🌾',
        'pesca': '🐟',
        'empleo': '💼',
        'sociedad y bienestar': '🤝',
        'economía': '💰',
        'medio ambiente': '🌱',
        'energía': '⚡',
        'turismo': '🗽',
        'transporte': '🚌',
        'educación': '🎓',
        'vivienda': '🏠',
        'comercio': '🛒',
        'industria': '🏭',
        'territorio': '🗺️',
        'información': '💾',  # Changed from 📊 to avoid conflicts
        'seguridad': '🛡️',
        'deportes': '⚽',
        'tecnología': '💻',
        'ciencia': '🔬',
        'agricultura': '🌽',
        'ganadería': '🐄',
        'ganadería y pesca': '🐮',
        'forestales': '🌲',
        'montes': '🌳',
        'minería': '⛏️',
        'construcción': '🏗️',
        'urbanismo e infraestructuras': '🏘️',
        'urbanismo': '🏙️',
        'infraestructuras': '🛣️',
        'servicios': '🔧',
        'sector privado': '🏢',
        'administración': '📋',
        'justicia': '⚖️',
        'hacienda': '💳',
        'demografía': '👥',
        'estadística': '📊',
        'planificación': '📐',
        'comunicaciones': '📡',
        'investigación': '🔍',
        'innovación': '💡',
        'patrimonio': '🏰',
        'cooperación': '🤲',
        'desarrollo': '📈',
        'ordenación': '📑',
        'recursos': '⚙️',
        'agua': '💧',
        'residuos': '♻️',
        'contaminación': '🌫️',
        'clima': '🌤️',
        'biodiversidad': '🦋',
        'protección': '🔒'
    }
    
    for theme in page_themes:
        # Skip categories we want to hide
        theme_lower = theme.name.lower()
        if theme_lower == 'urbanismo e infraestructura':  # Skip this specific category
            continue
            
        callback_data = f"theme:{theme.name}"
        # Use short ID if callback data is too long
        if len(callback_data.encode()) > 60:  # Leave some margin
            short_id = callback_mapper.get_short_id(callback_data)
            callback_data = f"s:{short_id}"
        
        # Get appropriate emoji for theme
        emoji = theme_emojis.get(theme_lower, '📊')  # Default to 📊 if no specific emoji
        
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {theme.name} ({theme.count})",
                callback_data=callback_data
            )
        ])
    
    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"themes_page:{page-1}"))
    if end_idx < len(themes):
        nav_buttons.append(InlineKeyboardButton("Siguiente ➡️", callback_data=f"themes_page:{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Add quick access buttons with better organization
    keyboard.append([
        InlineKeyboardButton("🔍 Búsqueda avanzada", callback_data="start_search"),
    ])
    keyboard.append([
        InlineKeyboardButton("🕒 Datos recientes", callback_data="recent_datasets"),
        InlineKeyboardButton("📈 Estadísticas", callback_data="stats")
    ])
    keyboard.append([
        InlineKeyboardButton("🔔 Mis alertas", callback_data="mis_alertas"),
        InlineKeyboardButton("❓ Ayuda", callback_data="help")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def create_theme_options_keyboard(theme_name: str) -> InlineKeyboardMarkup:
    """Create keyboard with theme exploration options."""
    keyboard = [
        [InlineKeyboardButton("📋 Ver datasets", callback_data=f"datasets:{theme_name}:0")],
        [InlineKeyboardButton("🔔 Suscribirme a esta categoría", callback_data=f"subscribe:theme:{theme_name}")],
        [
            InlineKeyboardButton("⬅️ Volver a categorías", callback_data="start"),
            InlineKeyboardButton("🏠 Inicio", callback_data="start")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)




def create_datasets_keyboard(
    datasets: List[Dataset], 
    theme_name: str,
    page: int = 0,
    per_page: int = 10,
    total_available: int = None
) -> InlineKeyboardMarkup:
    """Create keyboard with numbered dataset buttons."""
    keyboard = []
    
    # Create numbered buttons for datasets (up to 3 per row for better layout)
    for i in range(0, len(datasets), 3):
        row = []
        for j in range(i, min(i + 3, len(datasets))):
            dataset = datasets[j]
            dataset_number = j + 1
            callback_data = f"dataset_num:{theme_name}:{j}:{dataset.dataset_id}"
            
            # Use short ID if callback data is too long
            if len(callback_data.encode()) > 60:
                short_id = callback_mapper.get_short_id(callback_data)
                callback_data = f"s:{short_id}"
            
            row.append(InlineKeyboardButton(
                f"{dataset_number}",
                callback_data=callback_data
            ))
        keyboard.append(row)
    
    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data=f"datasets:{theme_name}:{page-1}"))
    
    if len(datasets) == per_page:  # Likely more pages available
        nav_buttons.append(InlineKeyboardButton("Siguiente ➡️", callback_data=f"datasets:{theme_name}:{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Back button
    keyboard.append([
        InlineKeyboardButton("🏠 Inicio", callback_data="start")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def create_dataset_info_keyboard(dataset_id: str, exports: List[ExportFormat], has_attachments: bool = False, is_bookmarked: bool = False, dataset_title: str = "") -> InlineKeyboardMarkup:
    """Create keyboard for dataset information page."""
    keyboard = []
    
    # Single export button that opens format selection menu
    if exports:
        export_callback = f"export_menu:{dataset_id}"
        if len(export_callback.encode()) > 60:
            short_id = callback_mapper.get_short_id(export_callback)
            export_callback = f"s:{short_id}"
        
        keyboard.append([
            InlineKeyboardButton("💾 Exportar datos", callback_data=export_callback)
        ])
    
    # Web link only
    keyboard.append([
        InlineKeyboardButton("🌐 Ver en web", url=f"https://analisis.datosabiertos.jcyl.es/explore/dataset/{dataset_id}")
    ])
    
    # Attachments
    if has_attachments:
        attachments_callback = f"attachments:{dataset_id}"
        if len(attachments_callback.encode()) > 60:
            short_id = callback_mapper.get_short_id(attachments_callback)
            attachments_callback = f"s:{short_id}"
            
        keyboard.append([
            InlineKeyboardButton("📎 Ver adjuntos", callback_data=attachments_callback)
        ])
    
    # Action buttons: Bookmark and Subscribe only
    bookmark_text = "❌ Quitar favorito" if is_bookmarked else "⭐ Favorito"
    
    # Handle long dataset IDs with callback mapping
    bookmark_callback = f"bookmark:{dataset_id}"
    subscribe_callback = f"subscribe:dataset:{dataset_id}"
    
    if len(bookmark_callback.encode()) > 60:
        short_id = callback_mapper.get_short_id(bookmark_callback)
        bookmark_callback = f"s:{short_id}"
        
    if len(subscribe_callback.encode()) > 60:
        short_id = callback_mapper.get_short_id(subscribe_callback)
        subscribe_callback = f"s:{short_id}"
    
    keyboard.append([
        InlineKeyboardButton(bookmark_text, callback_data=bookmark_callback),
        InlineKeyboardButton("🔔 Alertas", callback_data=subscribe_callback)
    ])
    
    # Navigation buttons
    keyboard.append([
        InlineKeyboardButton("🏠 Inicio", callback_data="start")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def create_export_menu_keyboard(dataset_id: str, exports: List[ExportFormat]) -> InlineKeyboardMarkup:
    """Create keyboard for export format selection with direct download and web options."""
    keyboard = []
    
    if not exports:
        keyboard.append([
            InlineKeyboardButton("❌ No hay formatos disponibles", callback_data="dummy")
        ])
    else:
        # Export formats as direct links to the JCYL website
        format_icons = {
            "xlsx": "📊", "csv": "📈", "json": "💾", "parquet": "🗃️",
            "geojson": "🗺️", "shapefile": "🏗️", "kml": "🌍", 
            "xml": "📄", "rdf": "🔗", "pdf": "📋"
        }
        
        # Group exports in rows of 2
        for i in range(0, len(exports), 2):
            row = []
            for j in range(i, min(i + 2, len(exports))):
                export = exports[j]
                icon = format_icons.get(export.format.lower(), "💾")
                row.append(InlineKeyboardButton(f"{icon} {export.format.upper()}", url=export.url))
            keyboard.append(row)
        
        # Add file download options for supported formats
        download_row = []
        supported_formats = ["csv", "json", "xlsx"]
        available_formats = [e for e in exports if e.format.lower() in supported_formats]
        
        if available_formats:
            keyboard.append([
                InlineKeyboardButton("📱 Descargar como archivo adjunto", callback_data="download_menu_header")
            ])
            
            # Add download buttons for supported formats
            for i in range(0, len(available_formats), 2):
                row = []
                for j in range(i, min(i + 2, len(available_formats))):
                    export = available_formats[j]
                    icon = format_icons.get(export.format.lower(), "💾")
                    
                    download_callback = f"download_file:{dataset_id}:{export.format}:{export.url}"
                    if len(download_callback.encode()) > 60:
                        short_id = callback_mapper.get_short_id(download_callback)
                        download_callback = f"s:{short_id}"
                    
                    row.append(InlineKeyboardButton(
                        f"📎 {export.format.upper()}", 
                        callback_data=download_callback
                    ))
                keyboard.append(row)
    
    # Back button
    back_callback = f"dataset:{dataset_id}"
    if len(back_callback.encode()) > 60:
        short_id = callback_mapper.get_short_id(back_callback)
        back_callback = f"s:{short_id}"
    
    keyboard.append([
        InlineKeyboardButton("⬅️ Volver al dataset", callback_data=back_callback),
        InlineKeyboardButton("🏠 Inicio", callback_data="start")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def create_attachments_keyboard(dataset_id: str) -> InlineKeyboardMarkup:
    """Create keyboard for attachments view."""
    callback_data = f"dataset:{dataset_id}"
    
    # Use short ID if callback data is too long
    if len(callback_data.encode()) > 60:
        short_id = callback_mapper.get_short_id(callback_data)
        callback_data = f"s:{short_id}"
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Volver al dataset", callback_data=callback_data)],
        [InlineKeyboardButton("🏠 Inicio", callback_data="start")]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_subscriptions_keyboard(subscriptions: List[Tuple[int, str, str, str]]) -> InlineKeyboardMarkup:
    """Create keyboard for user subscriptions management."""
    keyboard = []
    
    for sub_id, sub_type, sub_name, _ in subscriptions:
        if sub_type == "theme":
            icon = "📊"
            type_text = "Categoría"
        elif sub_type == "keyword":
            icon = "🔍"
            type_text = "Palabra clave"
        else:
            icon = "📄"
            type_text = "Dataset"
        name = sub_name[:30] + "..." if len(sub_name) > 30 else sub_name
        
        keyboard.append([
            InlineKeyboardButton(
                f"{icon} {type_text}: {name}",
                callback_data=f"unsub_confirm:{sub_id}"
            )
        ])
    
    if not keyboard:
        keyboard.append([
            InlineKeyboardButton("➕ Explorar para suscribirte", callback_data="start")
        ])
    else:
        # Add home button when there are subscriptions
        keyboard.append([
            InlineKeyboardButton("🏠 Inicio", callback_data="start")
        ])
    
    return InlineKeyboardMarkup(keyboard)


def create_unsubscribe_confirm_keyboard(sub_id: int) -> InlineKeyboardMarkup:
    """Create confirmation keyboard for unsubscribing."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Sí, cancelar", callback_data=f"unsub:{sub_id}"),
            InlineKeyboardButton("❌ No, mantener", callback_data="mis_alertas")
        ],
        [InlineKeyboardButton("🏠 Inicio", callback_data="start")]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_search_results_keyboard(datasets: List[Dataset], search_term: str, page: int, per_page: int, total_count: int) -> InlineKeyboardMarkup:
    """Create keyboard for search results with numbered buttons."""
    keyboard = []
    
    # Create numbered buttons for search results (up to 3 per row)
    for i in range(0, len(datasets), 3):
        row = []
        for j in range(i, min(i + 3, len(datasets))):
            dataset = datasets[j]
            # Calculate global dataset number based on page and position
            dataset_number = (page * per_page) + j + 1
            callback_data = f"search_num:{search_term}:{j}:{dataset.dataset_id}"
            
            # Use short ID if callback data is too long
            if len(callback_data.encode()) > 60:
                short_id = callback_mapper.get_short_id(callback_data)
                callback_data = f"s:{short_id}"
            
            row.append(InlineKeyboardButton(
                f"{dataset_number}",
                callback_data=callback_data
            ))
        keyboard.append(row)
    
    # Pagination
    nav_buttons = []
    if page > 0:
        prev_callback = f"search_page:{search_term}:{page-1}"
        if len(prev_callback.encode()) > 60:
            short_id = callback_mapper.get_short_id(prev_callback)
            prev_callback = f"s:{short_id}"
        nav_buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data=prev_callback))
    
    total_pages = (total_count + per_page - 1) // per_page
    # Only show next button if we have more pages AND current page has full results
    if page < total_pages - 1 and len(datasets) == per_page:
        next_callback = f"search_page:{search_term}:{page+1}"
        if len(next_callback.encode()) > 60:
            short_id = callback_mapper.get_short_id(next_callback)
            next_callback = f"s:{short_id}"
        nav_buttons.append(InlineKeyboardButton("Siguiente ➡️", callback_data=next_callback))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Quick actions
    keyboard.append([
        InlineKeyboardButton("🔍 Nueva búsqueda", callback_data="start_search"),
        InlineKeyboardButton("🏠 Inicio", callback_data="start")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def create_recent_datasets_keyboard(datasets: List[Dataset], page: int, per_page: int) -> InlineKeyboardMarkup:
    """Create keyboard for recent datasets with numbered buttons."""
    keyboard = []
    
    # Create numbered buttons for recent datasets (up to 3 per row)
    for i in range(0, len(datasets), 3):
        row = []
        for j in range(i, min(i + 3, len(datasets))):
            dataset = datasets[j]
            dataset_number = j + 1
            callback_data = f"recent_num:{j}:{dataset.dataset_id}"
            
            # Use short ID if callback data is too long
            if len(callback_data.encode()) > 60:
                short_id = callback_mapper.get_short_id(callback_data)
                callback_data = f"s:{short_id}"
            
            row.append(InlineKeyboardButton(
                f"{dataset_number}",
                callback_data=callback_data
            ))
        keyboard.append(row)
    
    # Navigation and actions
    keyboard.append([
        InlineKeyboardButton("🔄 Actualizar", callback_data="recent_datasets"),
        InlineKeyboardButton("🏠 Inicio", callback_data="start")
    ])
    
    return InlineKeyboardMarkup(keyboard)