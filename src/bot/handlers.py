"""Telegram bot message handlers."""

import logging
from typing import Optional
import httpx
import os
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import html

from ..api import JCYLAPIClient
from ..api.client import format_user_friendly_date
from ..models import DatabaseManager
from ..services.config import get_settings
from ..models.callback_map import callback_mapper
from .keyboards import (
    create_themes_keyboard,
    create_theme_options_keyboard, 
    create_datasets_keyboard,
    create_dataset_info_keyboard,
    create_export_menu_keyboard,
    create_attachments_keyboard,
    create_subscriptions_keyboard,
    create_unsubscribe_confirm_keyboard,
    create_search_results_keyboard,
    create_recent_datasets_keyboard
)

logger = logging.getLogger(__name__)

settings = get_settings()
db_manager = DatabaseManager(settings.database_url)
api_client = JCYLAPIClient(settings.jcyl_api_base_url)


def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Markdown V2 format."""
    if not text:
        return ""
    
    # Characters that need to be escaped in Markdown V2
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    # Replace each special character with escaped version
    escaped_text = text
    for char in special_chars:
        escaped_text = escaped_text.replace(char, f'\\{char}')
    
    return escaped_text


def clean_text_for_markdown(text: str) -> str:
    """Clean text for safe use in Markdown messages."""
    if not text:
        return "Sin título"
    
    # Remove HTML entities first
    clean_text = html.unescape(text)
    
    # Handle bold formatting first - preserve **text** as actual bold
    # This regex finds **text** patterns and preserves them
    import re
    
    # Replace problematic characters but preserve intentional markdown
    clean_text = clean_text.replace('_', '-').replace('`', "'")
    clean_text = clean_text.replace('[', '(').replace(']', ')')
    clean_text = clean_text.replace('#', 'No.').replace('|', '-')
    
    # Handle asterisks more carefully - only replace standalone ones, not ** pairs
    # First, temporarily replace ** patterns with placeholders
    bold_patterns = re.findall(r'\*\*([^*]+)\*\*', clean_text)
    placeholders = {}
    for i, pattern in enumerate(bold_patterns):
        placeholder = f"__BOLD_{i}__"
        placeholders[placeholder] = f"**{pattern}**"
        clean_text = clean_text.replace(f"**{pattern}**", placeholder, 1)
    
    # Now replace remaining single asterisks
    clean_text = clean_text.replace('*', '•')
    
    # Restore bold patterns
    for placeholder, bold_text in placeholders.items():
        clean_text = clean_text.replace(placeholder, bold_text)
    
    # Remove any remaining control characters
    clean_text = ''.join(char for char in clean_text if char.isprintable())
    
    # Trim and return
    return clean_text.strip()


def format_description(description: str) -> str:
    """Format dataset description with better structure and readability."""
    if not description or description == "Dato no disponible":
        return "Dato no disponible"
    
    # Clean the text first
    clean_desc = clean_text_for_markdown(description)
    
    # Check for abbreviations section
    if 'ABREVIATURAS EMPLEADAS:' in clean_desc.upper():
        # Split main description from abbreviations
        upper_desc = clean_desc.upper()
        abbrev_start = upper_desc.find('ABREVIATURAS EMPLEADAS:')
        
        main_desc = clean_desc[:abbrev_start].strip()
        abbrev_section = clean_desc[abbrev_start:].strip()
        
        # Format main description with paragraph breaks
        formatted_main = format_main_description(main_desc)
        
        # Format abbreviations
        formatted_abbrevs = format_abbreviations(abbrev_section)
        
        # Combine both parts
        if formatted_abbrevs:
            result = formatted_main + "\n\n" + formatted_abbrevs
        else:
            result = formatted_main
    else:
        # No abbreviations, just format as regular text
        result = format_main_description(clean_desc)
    
    # Limit total length for Telegram
    if len(result) > 1500:
        result = result[:1500] + "\n\n_... descripción truncada por longitud_"
    
    return result


def format_main_description(text: str) -> str:
    """Format the main description part."""
    if not text:
        return ""
    
    # Split into sentences and create paragraphs
    sentences = []
    current = ""
    
    for char in text:
        current += char
        if char == '.' and len(current) > 30:
            # Check if next character indicates end of sentence
            remaining = text[len(' '.join(sentences)) + len(current):]
            if (not remaining or remaining[0].isspace() or remaining[0].isupper() or
                remaining.startswith(' (por ejemplo')):
                sentences.append(current.strip())
                current = ""
    
    if current.strip():
        sentences.append(current.strip())
    
    # Group sentences into paragraphs (max 2 sentences per paragraph)
    paragraphs = []
    current_para = []
    
    for sentence in sentences:
        current_para.append(sentence)
        if len(current_para) >= 2 or len(' '.join(current_para)) > 250:
            paragraphs.append(' '.join(current_para))
            current_para = []
    
    if current_para:
        paragraphs.append(' '.join(current_para))
    
    return '\n\n'.join(paragraphs)


def format_abbreviations(abbrev_text: str) -> str:
    """Format abbreviations section."""
    if not abbrev_text or ':' not in abbrev_text:
        return ""
    
    # Extract just the abbreviations part
    if 'ABREVIATURAS EMPLEADAS:' in abbrev_text:
        abbrev_content = abbrev_text.split('ABREVIATURAS EMPLEADAS:', 1)[1].strip()
    else:
        abbrev_content = abbrev_text
    
    formatted_abbrevs = ["**ABREVIATURAS:**"]
    
    # Simple manual parsing approach
    current_abbr = ""
    current_def = ""
    i = 0
    
    while i < len(abbrev_content):
        char = abbrev_content[i]
        
        if char.isupper() and not current_abbr:
            # Start of new abbreviation
            current_abbr = char
        elif char.isupper() and current_abbr and current_def:
            # New abbreviation starting, finish previous one
            if current_abbr and current_def.strip():
                formatted_abbrevs.append(f"• **{current_abbr}:** {current_def.strip()}")
            current_abbr = char
            current_def = ""
        elif char == ':' and current_abbr:
            # End of abbreviation, start definition
            i += 1  # Skip the colon
            current_def = ""
        elif current_abbr and char != ':':
            if not current_def and char != ' ':
                current_abbr += char
            else:
                current_def += char
        
        i += 1
    
    # Add the last abbreviation
    if current_abbr and current_def.strip():
        formatted_abbrevs.append(f"• **{current_abbr}:** {current_def.strip()}")
    
    return '\n'.join(formatted_abbrevs) if len(formatted_abbrevs) > 1 else ""


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    if not user:
        return
    
    # Save/update user in database
    db_manager.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code or "es"
    )
    
    try:
        logger.info("Getting themes for start command...")
        # Using global API client instance to maintain cache consistency
        themes = await api_client.get_themes_with_real_counts()
        
        logger.info(f"Received {len(themes)} themes")
        if not themes:
            await update.message.reply_text(
                "❌ No se pudieron cargar las categorías. Inténtalo más tarde."
            )
            return
        
        keyboard = create_themes_keyboard(themes, per_page=settings.themes_per_page)
        
        # Get popular categories to show in welcome message
        popular_themes = sorted(themes, key=lambda x: x.count, reverse=True)[:3]
        popular_examples = ", ".join([theme.name for theme in popular_themes])
        
        message = (
            "🏛️ <b>Portal de Datos Abiertos - Junta de Castilla y León</b>\n\n"
            "¡Bienvenido al explorador oficial de datos abiertos de Castilla y León!\n\n"
            
            "🌍 Acceso libre y transparente a la información pública oficial.\n\n"
            
            f"🔥 <b>Datos más consultados:</b> {popular_examples}\n\n"
            f"📊 <b>Total disponible:</b> {len(themes)} categorías con +400 datasets\n\n"
            
            "🎯 <b>¿Qué puedes hacer aquí?</b>\n"
            "• Explorar datasets organizados por categorías\n"
            "• Descargar datos en múltiples formatos (CSV, XLSX, JSON...)\n"
            "• Suscribirte a alertas de actualizaciones\n"
            "• Acceder a documentos adjuntos oficiales\n\n"
            
            "🚀 <b>¡Comienza explorando!</b>\n\n"

            "👇 Selecciona una categoría para descubrir datos oficiales:\n"
        )
        
        await update.message.reply_text(
            message,
            parse_mode="HTML",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(
            f"❌ Error al cargar las categorías: {str(e)}\n\nInténtalo más tarde."
        )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from inline keyboards."""
    query = update.callback_query
    await query.answer()
    
    try:
        data = query.data
        
        # Handle short IDs
        if data.startswith("s:"):
            short_id = data[2:]  # Remove "s:" prefix
            full_data = callback_mapper.get_full_data(short_id)
            if full_data:
                data = full_data
            else:
                await query.edit_message_text("❌ Enlace expirado. Usa /start para continuar.")
                return
        
        if data == "start":
            await show_themes(query, context)
        elif data == "refresh_stats":
            await refresh_portal_stats(query, context)
        elif data.startswith("themes_page:"):
            page = int(data.split(":")[1])
            await show_themes(query, context, page)
        elif data.startswith("theme:"):
            theme_name = data.split(":", 1)[1]
            await show_theme_options(query, context, theme_name)
        elif data.startswith("datasets:"):
            _, theme_name, page = data.split(":", 2)
            await show_datasets(query, context, theme_name, page=int(page))
        elif data.startswith("dataset_num:"):
            # Handle numbered dataset selection: dataset_num:theme_name:index:dataset_id
            parts = data.split(":", 3)
            theme_name, dataset_index, dataset_id = parts[1], int(parts[2]), parts[3]
            await show_dataset_info(query, context, dataset_id)
        elif data.startswith("search_num:"):
            # Handle numbered search result selection: search_num:search_term:index:dataset_id
            parts = data.split(":", 3)
            search_term, dataset_index, dataset_id = parts[1], int(parts[2]), parts[3]
            await show_dataset_info(query, context, dataset_id)
        elif data.startswith("recent_num:"):
            # Handle numbered recent dataset selection: recent_num:index:dataset_id
            parts = data.split(":", 2)
            dataset_index, dataset_id = int(parts[1]), parts[2]
            await show_dataset_info(query, context, dataset_id)
        elif data.startswith("fav_num:"):
            # Handle numbered favorite dataset selection: fav_num:index:dataset_id
            parts = data.split(":", 2)
            dataset_index, dataset_id = int(parts[1]), parts[2]
            await show_dataset_info(query, context, dataset_id)
        elif data.startswith("dataset:"):
            dataset_id = data.split(":", 1)[1]
            await show_dataset_info(query, context, dataset_id)
        elif data.startswith("attachments:"):
            dataset_id = data.split(":", 1)[1]
            await show_attachments(query, context, dataset_id)
        elif data.startswith("subscribe:"):
            await handle_subscription(query, context)
        elif data == "mis_alertas":
            await show_my_subscriptions(query, context)
        elif data.startswith("unsub_confirm:"):
            sub_id = int(data.split(":", 1)[1])
            await confirm_unsubscribe(query, context, sub_id)
        elif data.startswith("unsub:"):
            sub_id = int(data.split(":", 1)[1])
            await handle_unsubscribe(query, context, sub_id)
        elif data == "start_search":
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Inicio", callback_data="start")]
            ])
            await query.edit_message_text(
                "🔍 <b>Búsqueda de Datasets</b>\n\n"
                "Para buscar, usa el comando:\n"
                "<code>/buscar [término de búsqueda]</code>\n\n"
                "<b>Ejemplos:</b>\n"
                "• <code>/buscar covid</code>\n"
                "• <code>/buscar población</code>\n"
                "• <code>/buscar salud castilla</code>",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        elif data == "recent_datasets":
            await handle_recent_datasets_callback(query, context)
        elif data == "stats":
            await handle_stats_callback(query, context)
        elif data == "help":
            await show_help_callback(query, context)
        elif data.startswith("search_page:"):
            parts = data.split(":", 2)
            search_term, page = parts[1], int(parts[2])
            await handle_search_page(query, context, search_term, page)
        elif data.startswith("bookmark:"):
            dataset_id = data.split(":", 1)[1]
            # Get dataset info for title
            dataset = await api_client.get_dataset_info(dataset_id)
            dataset_title = dataset.title if dataset else "Dataset"
            await handle_bookmark_toggle(query, context, dataset_id, dataset_title)
            # Refresh the dataset info to update the bookmark button
            await show_dataset_info(query, context, dataset_id)
        elif data == "refresh_bookmarks":
            await handle_refresh_bookmarks_callback(query, context)
        elif data.startswith("preview:"):
            dataset_id = data.split(":", 1)[1]
            await handle_dataset_preview(query, context, dataset_id)
        elif data.startswith("share:"):
            dataset_id = data.split(":", 1)[1]
            await handle_dataset_share(query, context, dataset_id)
        elif data.startswith("export_menu:"):
            dataset_id = data.split(":", 1)[1]
            await show_export_menu(query, context, dataset_id)
        elif data.startswith("daily_summary:"):
            await handle_daily_summary_callback(query, context)
        else:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Inicio", callback_data="start")]
            ])
            await query.edit_message_text(
                "❌ Opción no reconocida.",
                reply_markup=keyboard
            )
            
    except Exception as e:
        logger.error(f"Error in handle_callback: {e}")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Inicio", callback_data="start")]
        ])
        await query.edit_message_text(
            "❌ Error procesando la solicitud.",
            reply_markup=keyboard
        )


async def show_themes(query, context, page: int = 0) -> None:
    """Show themes list."""
    try:
        # Using global API client instance to maintain cache consistency
        themes = await api_client.get_themes_with_real_counts()
        if not themes:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Reintentar", callback_data="start")]
            ])
            await query.edit_message_text(
                "❌ No se encontraron categorías.",
                reply_markup=keyboard
            )
            return
        
        keyboard = create_themes_keyboard(themes, page, settings.themes_per_page)
        
        total_pages = (len(themes) + settings.themes_per_page - 1) // settings.themes_per_page
        # Get some popular categories for the message
        popular_themes = sorted(themes, key=lambda x: x.count, reverse=True)[:3]
        popular_list = ", ".join([f"{theme.name} ({theme.count})" for theme in popular_themes])
        
        message = (
            "🏛️ *¡Bienvenido al Portal de Datos Abiertos de Castilla y León!*\n\n"
            f"🎯 **¿Qué datos necesitas?**\n"
            f"Explora {len(themes)} categorías con información oficial actualizada\n\n"
            f"🔥 **Más populares:** {popular_list}\n\n"
            f"👇 **Selecciona una categoría** (página {page + 1} de {total_pages})\n"
            f"💡 Los números indican cuántos datasets hay disponibles\n"
        )
        
        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in show_themes: {e}")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Reintentar", callback_data="start")]
        ])
        await query.edit_message_text(
            "❌ Error al cargar las categorías.",
            reply_markup=keyboard
        )


async def show_theme_options(query, context, theme_name: str) -> None:
    """Show theme exploration options."""
    keyboard = create_theme_options_keyboard(theme_name)
    
    message = (
        f"📊 *Categoría: {theme_name}*\n\n"
        "¿Qué te gustaría hacer?"
    )
    
    await query.edit_message_text(
        message,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def show_datasets(query, context, theme_name: str, page: int = 0) -> None:
    """Show datasets list."""
    try:
        logger.info(f"Requesting datasets for theme='{theme_name}', page={page}")
        # Use the global API client instance to maintain cache consistency
        datasets, _ = await api_client.get_datasets(
            theme=theme_name,
            limit=settings.datasets_per_page,
            offset=page * settings.datasets_per_page
        )
        
        # Get the real total count from facets (which are accurate)
        themes = await api_client.get_themes()
        real_total_count = next((t.count for t in themes if t.name == theme_name), 0)
        
        logger.info(f"Received {len(datasets)} datasets out of {real_total_count} total (from facets)")
        
        if not datasets:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Volver a categorías", callback_data="start")]
            ])
            message = f"❌ No se encontraron datasets en la categoría '{theme_name}'"
            await query.edit_message_text(
                message + ".",
                reply_markup=keyboard
            )
            return
        
        keyboard = create_datasets_keyboard(datasets, theme_name, page, settings.datasets_per_page)
        total_pages = (real_total_count + settings.datasets_per_page - 1) // settings.datasets_per_page
        
        # Show all datasets with full titles in the message
        dataset_list = []
        for i, dataset in enumerate(datasets, 1):
            title = clean_text_for_markdown(dataset.title) if dataset.title else "Sin título"
            # Don't truncate - show full title with bold formatting
            dataset_list.append(f"{i}. *{title}*")
        
        clean_theme_name = clean_text_for_markdown(theme_name)
        
        message = (
            f"📋 *{clean_theme_name}*\n\n"
            f"📊 Total: {real_total_count} datasets\n"
            f"📄 Página {page + 1} de {total_pages} ({len(datasets)} datasets)\n\n"
            f"**Datasets disponibles:**\n" + "\n\n".join(dataset_list) + "\n\n"
            f"_Haz clic en el número correspondiente para ver detalles._"
        )
        
        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in show_datasets: {e}")
        import traceback
        traceback.print_exc()
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Volver a categorías", callback_data="start")]
        ])
        await query.edit_message_text(
            f"❌ Error al cargar los datasets: {str(e)}",
            reply_markup=keyboard
        )


async def show_dataset_info(query, context, dataset_id: str) -> None:
    """Show detailed dataset information."""
    try:
        # Using global API client instance to maintain cache consistency
        dataset = await api_client.get_dataset_info(dataset_id)
        if not dataset:
            await query.edit_message_text("❌ Dataset no encontrado.")
            return
        
        exports = await api_client.get_dataset_exports(dataset_id)
        attachments = await api_client.get_dataset_attachments(dataset_id)
        
        # Check if dataset is bookmarked by user
        user_id = query.from_user.id
        user_db_id = db_manager.get_or_create_user(telegram_id=user_id)  # Now returns ID directly
        is_bookmarked = db_manager.is_bookmarked(user_db_id, dataset_id)
        
        keyboard = create_dataset_info_keyboard(dataset_id, exports, len(attachments) > 0, is_bookmarked, dataset.title)
        
        # Format dataset information with improved description formatting
        description = format_description(dataset.description)
        
        themes_text = ", ".join(dataset.themes) if dataset.themes else "Dato no disponible"
        themes_text = clean_text_for_markdown(themes_text)
        if len(themes_text) > 200:
            themes_text = themes_text[:200] + "..."
        
        # Limit title length to prevent message overflow  
        title = clean_text_for_markdown(dataset.title) if dataset.title else "Sin título"
        if len(title) > 80:
            title = title[:80] + "..."
        
        # Format the modification date to be user-friendly
        friendly_date = format_user_friendly_date(dataset.modified)
        
        publisher = clean_text_for_markdown(dataset.publisher) if dataset.publisher else "Dato no disponible"
        license_text = clean_text_for_markdown(dataset.license) if dataset.license else "Dato no disponible"
        
        message = (
            f"📄 *{title}*\n\n"
            f"📝 *Descripción:*\n{description}\n\n"
            f"🏢 *Publicador:* {publisher}\n"
            f"📜 *Licencia:* {license_text}\n"
            f"📊 *Registros:* {dataset.records_count:,}\n"
            f"📅 *Última modificación:* {friendly_date}\n"
            f"🏷️ *Categorías:* {themes_text}\n\n"
        )
        
        if exports:
            message += f"💾 *Formatos de descarga disponibles:* {len(exports)}\n"
        if attachments:
            message += f"📎 *Adjuntos:* {len(attachments)}\n"
        
        # Ensure message doesn't exceed Telegram's limit (4096 characters)
        if len(message) > 4000:
            message = message[:4000] + "\n\n⚠️ *Información truncada*"
        
        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in show_dataset_info for dataset '{dataset_id}': {e}")
        import traceback
        traceback.print_exc()
        await query.edit_message_text(
            f"❌ Error al cargar el dataset.\n\n"
            f"**Dataset ID:** {dataset_id}\n\n"
            f"Puede que este dataset tenga problemas temporales. "
            f"Inténtalo más tarde o selecciona otro dataset."
        )


async def show_attachments(query, context, dataset_id: str) -> None:
    """Show dataset attachments."""
    try:
        attachments = await api_client.get_dataset_attachments(dataset_id)
        
        if not attachments:
            await query.edit_message_text("❌ No hay adjuntos disponibles para este dataset.")
            return
        
        keyboard = create_attachments_keyboard(dataset_id)
        
        message = f"📎 *Adjuntos del dataset*\n\n"
        
        for i, attachment in enumerate(attachments, 1):
            title = attachment.title if attachment.title != "Dato no disponible" else f"Adjunto {i}"
            message += f"{i}. [{title}]({attachment.href})\n"
            if attachment.description and attachment.description != "Dato no disponible":
                desc = attachment.description[:100] + "..." if len(attachment.description) > 100 else attachment.description
                message += f"   _{desc}_\n"
            message += "\n"
        
        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error in show_attachments: {e}")
        await query.edit_message_text("❌ Error al cargar los adjuntos.")


async def handle_subscription(query, context) -> None:
    """Handle subscription requests."""
    try:
        data = query.data
        logger.info(f"Processing subscription callback: {data}")
        
        # Handle shortened callbacks
        if data.startswith("s:"):
            # Get original callback from mapper
            from .keyboards import callback_mapper
            original_data = callback_mapper.get_original_callback(data.split(":", 1)[1])
            if not original_data:
                logger.error(f"Could not find original callback for short ID: {data}")
                await query.edit_message_text("❌ Error: callback no encontrado.")
                return
            data = original_data
            logger.info(f"Resolved short callback to: {data}")
        
        parts = data.split(":", 2)
        
        if len(parts) < 3:
            logger.error(f"Invalid callback data format: {data}")
            await query.edit_message_text("❌ Error: formato de datos inválido.")
            return
            
        sub_type, sub_id = parts[1], parts[2]
        
        user = query.from_user
        if not user:
            return
        
        # Get user from database
        user_db_id = db_manager.get_or_create_user(telegram_id=user.id)  # Now returns ID directly
        
        # Determine subscription name
        if sub_type == "theme":
            sub_name = sub_id  # theme name
        else:  # dataset
            dataset = await api_client.get_dataset_info(sub_id)
            sub_name = dataset.title if dataset else sub_id
        
        
        # Add subscription
        success = db_manager.add_subscription(user_db_id, sub_type, sub_id, sub_name)
        
        if success:
            type_text = "categoría" if sub_type == "theme" else "dataset"
            # Escape HTML characters in subscription name
            safe_name = sub_name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            
            # Add home button
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Inicio", callback_data="start")
            ]])
            
            await query.edit_message_text(
                f"✅ Te has suscrito a la {type_text}: {sub_name}\n\n"
                f"Recibirás alertas automáticas cada 2 horas si hay cambios.\n\n"
                f"Usa /mis_alertas para gestionar tus suscripciones.",
                reply_markup=keyboard
            )
        else:
            type_text = "categoría" if sub_type == "theme" else "dataset"
            # Escape HTML characters in subscription name
            safe_name = sub_name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            
            # Add home button
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Inicio", callback_data="start")
            ]])
            
            await query.edit_message_text(
                f"ℹ️ Ya estás suscrito a la {type_text}: {sub_name}",
                reply_markup=keyboard
            )
        
    except Exception as e:
        logger.error(f"Error in handle_subscription: {e}", exc_info=True)
        await query.edit_message_text(
            f"❌ Error al procesar la suscripción.\n\n"
            f"Debug: {str(e)[:100]}"
        )


async def my_subscriptions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /mis_alertas command."""
    user = update.effective_user
    if not user:
        return
    
    try:
        # Get user from database
        user_db_id = db_manager.get_or_create_user(telegram_id=user.id)  # Now returns ID directly
        subscriptions = db_manager.get_user_subscriptions(user_db_id)
        
        if not subscriptions:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Inicio", callback_data="start")]
            ])
            message = (
                "📭 *Mis alertas*\n\n"
                "No tienes suscripciones activas.\n\n"
                "Usa el botón de abajo para explorar y suscribirte a categorías o datasets."
            )
            await update.message.reply_text(
                message, 
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            return
        
        # Format subscriptions for keyboard
        sub_list = [(s.id, s.subscription_type, s.subscription_name, s.subscription_id) for s in subscriptions]
        keyboard = create_subscriptions_keyboard(sub_list)
        
        # Count different types of subscriptions
        theme_count = sum(1 for s in subscriptions if s.subscription_type == "theme")
        dataset_count = sum(1 for s in subscriptions if s.subscription_type == "dataset")
        keyword_count = sum(1 for s in subscriptions if s.subscription_type == "keyword")
        
        message = f"🔔 *Mis alertas*\n\n"
        message += f"Tienes {len(subscriptions)} suscripciones activas:\n"
        if theme_count > 0:
            message += f"📂 {theme_count} categorías\n"
        if dataset_count > 0:
            message += f"📄 {dataset_count} datasets\n"
        if keyword_count > 0:
            message += f"🔍 {keyword_count} palabras clave\n"
        message += f"\nRecibirás alertas cuando haya cambios cada 2 horas.\n\n"
        message += f"Toca una para cancelarla:"
        
        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in my_subscriptions_command: {e}")
        await update.message.reply_text("❌ Error al cargar las suscripciones.")


async def show_my_subscriptions(query, context) -> None:
    """Show user subscriptions (callback version)."""
    user = query.from_user
    if not user:
        return
    
    try:
        # Get user from database
        user_db_id = db_manager.get_or_create_user(telegram_id=user.id)  # Now returns ID directly
        subscriptions = db_manager.get_user_subscriptions(user_db_id)
        
        if not subscriptions:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Inicio", callback_data="start")]
            ])
            await query.edit_message_text(
                "📭 No tienes suscripciones activas.\n\n"
                "Usa el botón de abajo para explorar y suscribirte.",
                reply_markup=keyboard
            )
            return
        
        # Format subscriptions for keyboard
        sub_list = [(s.id, s.subscription_type, s.subscription_name, s.subscription_id) for s in subscriptions]
        keyboard = create_subscriptions_keyboard(sub_list)
        
        message = (
            f"🔔 *Mis alertas*\n\n"
            f"Tienes {len(subscriptions)} suscripciones activas.\n"
            f"Toca una para cancelarla:"
        )
        
        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in show_my_subscriptions: {e}")
        await query.edit_message_text("❌ Error al cargar las suscripciones.")


async def confirm_unsubscribe(query, context, sub_id: int) -> None:
    """Show unsubscribe confirmation."""
    user = query.from_user
    if not user:
        return
    
    try:
        # Get user and subscription details
        user_db_id = db_manager.get_or_create_user(telegram_id=user.id)  # Now returns ID directly
        subscriptions = db_manager.get_user_subscriptions(user_db_id)
        
        subscription = None
        for sub in subscriptions:
            if sub.id == sub_id:
                subscription = sub
                break
        
        if not subscription:
            await query.edit_message_text("❌ Suscripción no encontrada.")
            return
        
        keyboard = create_unsubscribe_confirm_keyboard(sub_id)
        
        type_text = "categoría" if subscription.subscription_type == "theme" else "dataset"
        message = (
            f"❓ *Confirmar cancelación*\n\n"
            f"¿Estás seguro de que quieres cancelar la suscripción a la {type_text}:\n"
            f"*{subscription.subscription_name}*?"
        )
        
        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in confirm_unsubscribe: {e}")
        await query.edit_message_text("❌ Error al procesar la solicitud.")


async def handle_unsubscribe(query, context, sub_id: int) -> None:
    """Handle subscription removal."""
    user = query.from_user
    if not user:
        return
    
    try:
        # Get user from database
        user_db_id = db_manager.get_or_create_user(telegram_id=user.id)  # Now returns ID directly
        
        success = db_manager.remove_subscription(user_db_id, sub_id)
        
        if success:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔔 Mis alertas", callback_data="mis_alertas")],
                [InlineKeyboardButton("🏠 Inicio", callback_data="start")]
            ])
            await query.edit_message_text(
                "✅ Suscripción cancelada correctamente.\n\n"
                "Puedes gestionar tus otras suscripciones desde 'Mis alertas'.",
                reply_markup=keyboard
            )
        else:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔔 Mis alertas", callback_data="mis_alertas")],
                [InlineKeyboardButton("🏠 Inicio", callback_data="start")]
            ])
            await query.edit_message_text(
                "❌ Error al cancelar la suscripción.",
                reply_markup=keyboard
            )
        
    except Exception as e:
        logger.error(f"Error in handle_unsubscribe: {e}")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔔 Mis alertas", callback_data="mis_alertas")],
            [InlineKeyboardButton("🏠 Inicio", callback_data="start")]
        ])
        await query.edit_message_text(
            "❌ Error al procesar la cancelación.",
            reply_markup=keyboard
        )


async def portal_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /estadisticas command."""
    user = update.effective_user
    if not user:
        return

    loading_message = await update.message.reply_text("📊 Obteniendo estadísticas del portal...")

    try:
        # Get basic portal statistics
        themes = await api_client.get_themes()
        total_themes = len(themes)
        
        # Get total datasets count and recent activity
        recent_datasets, total_datasets_estimate = await api_client.get_datasets(limit=100, offset=0)
        
        if total_datasets_estimate == 0:
            # Fallback calculation
            total_datasets_estimate = len(recent_datasets) * 10  # Conservative estimate
        
        # Calculate recent activity (last 30 days)
        cutoff_date = datetime.now() - timedelta(days=30)
        recent_count = 0
        
        # Count datasets modified in last 30 days
        sample_dates = []
        for i, dataset in enumerate(recent_datasets):
            if dataset.modified and dataset.modified != "Dato no disponible":
                # Collect first 3 dates as samples for debugging
                if len(sample_dates) < 3:
                    sample_dates.append(dataset.modified)
                try:
                    modified_date = None
                    date_str = dataset.modified.strip()
                    
                    # Try different date formats
                    formats = [
                        "%d/%m/%Y",         # 01/12/2024
                        "%Y-%m-%d",         # 2024-12-01
                        "%Y-%m-%dT%H:%M:%S", # 2024-12-01T10:30:45
                        "%Y-%m-%dT%H:%M:%SZ", # 2024-12-01T10:30:45Z
                        "%Y-%m-%d %H:%M:%S", # 2024-12-01 10:30:45
                    ]
                    
                    for fmt in formats:
                        try:
                            if "T" in date_str and "Z" in date_str:
                                modified_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            else:
                                modified_date = datetime.strptime(date_str, fmt)
                            break
                        except ValueError:
                            continue
                    
                    if modified_date and modified_date >= cutoff_date:
                        recent_count += 1
                        
                except Exception as e:
                    # Debug: log some failed dates to understand the format
                    logger.debug(f"Failed to parse date: {dataset.modified}")
                    continue
        
        # Log sample dates for debugging
        logger.info(f"Sample modification dates found: {sample_dates[:3]}")
        logger.info(f"Found {recent_count} datasets updated in last 30 days")
        
        # Get most active themes (top 5)
        theme_counts = []
        for theme in themes[:10]:  # Check top 10 themes
            try:
                theme_datasets, theme_count = await api_client.get_datasets(theme=theme.name, limit=1)
                count = theme_count or theme.count
                if count:
                    theme_counts.append((theme.name, count))
            except:
                continue
        
        theme_counts.sort(key=lambda x: x[1], reverse=True)
        top_themes = theme_counts[:5]
        
        # Get user subscription stats
        session = db_manager.get_session()
        try:
            from ..models import Subscription, User
            total_users = session.query(User).count()
            active_subs = session.query(Subscription).filter(Subscription.is_active == True).count()
        finally:
            session.close()
        
        # Build statistics message
        stats_message = "📊 **Estadísticas del Portal de Datos Abiertos CyL**\n\n"
        
        stats_message += f"📈 **Datos Generales**\n"
        stats_message += f"• Total datasets: **~{total_datasets_estimate:,}**\n"
        stats_message += f"• Categorías disponibles: **{total_themes}**\n"
        stats_message += f"• Actualizados últimos 30 días: **{recent_count}**\n\n"
        
        stats_message += f"🔥 **Categorías más populares**\n"
        for i, (theme_name, count) in enumerate(top_themes, 1):
            emoji = ["🥇", "🥈", "🥉", "🏅", "🏅"][i-1]
            stats_message += f"{emoji} **{theme_name}**: {count} datasets\n"
        
        if active_subs > 0:
            stats_message += f"\n🤖 **Estadísticas del Bot**\n"
            stats_message += f"• Usuarios registrados: **{total_users}**\n"
            stats_message += f"• Suscripciones activas: **{active_subs}**\n"
        
        stats_message += f"\n📅 Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        
        # Create keyboard
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Actualizar", callback_data="refresh_stats")],
            [InlineKeyboardButton("🏠 Inicio", callback_data="start")]
        ])
        
        await loading_message.edit_text(stats_message, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error getting portal stats: {e}")
        await loading_message.edit_text(
            "❌ Error al obtener las estadísticas.\n\n"
            "Inténtalo de nuevo más tarde.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Inicio", callback_data="start")
            ]])
        )


async def refresh_portal_stats(query, context) -> None:
    """Refresh portal statistics via callback."""
    await query.edit_message_text("📊 Actualizando estadísticas...")
    
    try:
        # Get updated statistics (same logic as portal_stats_command)
        themes = await api_client.get_themes()
        total_themes = len(themes)
        
        recent_datasets, total_datasets_estimate = await api_client.get_datasets(limit=100, offset=0)
        if total_datasets_estimate == 0:
            total_datasets_estimate = len(recent_datasets) * 10
        
        # Calculate recent activity
        cutoff_date = datetime.now() - timedelta(days=30)
        recent_count = 0
        
        for dataset in recent_datasets:
            if dataset.modified and dataset.modified != "Dato no disponible":
                try:
                    modified_date = None
                    date_str = dataset.modified.strip()
                    
                    # Try different date formats
                    formats = [
                        "%d/%m/%Y",         # 01/12/2024
                        "%Y-%m-%d",         # 2024-12-01
                        "%Y-%m-%dT%H:%M:%S", # 2024-12-01T10:30:45
                        "%Y-%m-%dT%H:%M:%SZ", # 2024-12-01T10:30:45Z
                        "%Y-%m-%d %H:%M:%S", # 2024-12-01 10:30:45
                    ]
                    
                    for fmt in formats:
                        try:
                            if "T" in date_str and "Z" in date_str:
                                modified_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            else:
                                modified_date = datetime.strptime(date_str, fmt)
                            break
                        except ValueError:
                            continue
                    
                    if modified_date and modified_date >= cutoff_date:
                        recent_count += 1
                        
                except Exception as e:
                    logger.debug(f"Failed to parse date: {dataset.modified}")
                    continue
        
        # Get theme counts
        theme_counts = []
        for theme in themes[:10]:
            try:
                theme_datasets, theme_count = await api_client.get_datasets(theme=theme.name, limit=1)
                count = theme_count or theme.count
                if count:
                    theme_counts.append((theme.name, count))
            except:
                continue
        
        theme_counts.sort(key=lambda x: x[1], reverse=True)
        top_themes = theme_counts[:5]
        
        # Get subscription stats
        session = db_manager.get_session()
        try:
            from ..models import Subscription, User
            total_users = session.query(User).count()
            active_subs = session.query(Subscription).filter(Subscription.is_active == True).count()
        finally:
            session.close()
        
        # Build message
        stats_message = "📊 **Estadísticas del Portal de Datos Abiertos CyL**\n\n"
        stats_message += f"📈 **Datos Generales**\n"
        stats_message += f"• Total datasets: **~{total_datasets_estimate:,}**\n"
        stats_message += f"• Categorías disponibles: **{total_themes}**\n"
        stats_message += f"• Actualizados últimos 30 días: **{recent_count}**\n\n"
        
        stats_message += f"🔥 **Categorías más populares**\n"
        for i, (theme_name, count) in enumerate(top_themes, 1):
            emoji = ["🥇", "🥈", "🥉", "🏅", "🏅"][i-1]
            stats_message += f"{emoji} **{theme_name}**: {count} datasets\n"
        
        if active_subs > 0:
            stats_message += f"\n🤖 **Estadísticas del Bot**\n"
            stats_message += f"• Usuarios registrados: **{total_users}**\n"
            stats_message += f"• Suscripciones activas: **{active_subs}**\n"
        
        stats_message += f"\n📅 Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Actualizar", callback_data="refresh_stats")],
            [InlineKeyboardButton("🏠 Inicio", callback_data="start")]
        ])
        
        await query.edit_message_text(stats_message, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error refreshing stats: {e}")
        await query.edit_message_text(
            "❌ Error al actualizar las estadísticas.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Inicio", callback_data="start")
            ]])
        )


async def keyword_alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /alertas_palabras command."""
    user = update.effective_user
    if not user:
        return

    if not context.args:
        # Show help and current keyword alerts
        user_db_id = db_manager.get_or_create_user(telegram_id=user.id)
        
        # Get existing keyword subscriptions
        session = db_manager.get_session()
        try:
            from ..models import Subscription
            keyword_subs = session.query(Subscription).filter(
                Subscription.user_id == user_db_id,
                Subscription.subscription_type == "keyword",
                Subscription.is_active == True
            ).all()
        finally:
            session.close()
        
        message = "🔍 **Alertas por Palabras Clave**\n\n"
        message += "Recibe notificaciones cuando aparezcan nuevos datasets que contengan palabras específicas.\n\n"
        
        if keyword_subs:
            message += "🔔 **Tus alertas activas:**\n"
            for sub in keyword_subs:
                message += f"• {sub.subscription_id}\n"
            message += "\n"
        
        message += "**Uso:**\n"
        message += "`/alertas_palabras [palabra]` - Añadir alerta\n"
        message += "`/alertas_palabras quitar [palabra]` - Quitar alerta\n\n"
        message += "**Ejemplos:**\n"
        message += "`/alertas_palabras transporte`\n"
        message += "`/alertas_palabras educación`\n"
        message += "`/alertas_palabras quitar transporte`"
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Inicio", callback_data="start")
        ]])
        
        await update.message.reply_text(message, reply_markup=keyboard)
        return
    
    # Process the command
    args = context.args
    user_db_id = db_manager.get_or_create_user(telegram_id=user.id)
    
    if args[0].lower() == "quitar" and len(args) > 1:
        # Remove keyword alert
        keyword = " ".join(args[1:]).lower().strip()
        
        session = db_manager.get_session()
        try:
            from ..models import Subscription
            existing = session.query(Subscription).filter(
                Subscription.user_id == user_db_id,
                Subscription.subscription_type == "keyword",
                Subscription.subscription_id == keyword,
                Subscription.is_active == True
            ).first()
            
            if existing:
                existing.is_active = False
                session.commit()
                
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Inicio", callback_data="start")
                ]])
                
                await update.message.reply_text(
                    f"✅ Alerta eliminada para: {keyword}\n\n"
                    f"Ya no recibirás notificaciones de datasets con esta palabra.",
                    reply_markup=keyboard
                )
            else:
                await update.message.reply_text(
                    f"❌ No tienes alertas activas para: {keyword}"
                )
        finally:
            session.close()
    else:
        # Add keyword alert
        keyword = " ".join(args).lower().strip()
        
        if len(keyword) < 3:
            await update.message.reply_text(
                "❌ La palabra clave debe tener al menos 3 caracteres."
            )
            return
        
        success = db_manager.add_subscription(user_db_id, "keyword", keyword, f"Palabra clave: {keyword}")
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Inicio", callback_data="start")
        ]])
        
        if success:
            await update.message.reply_text(
                f"✅ Alerta creada para: {keyword}\n\n"
                f"Recibirás notificaciones cada 2 horas si aparecen nuevos datasets que contengan esta palabra.\n\n"
                f"Usa /mis_alertas para gestionar todas tus suscripciones.",
                reply_markup=keyboard
            )
        else:
            await update.message.reply_text(
                f"ℹ️ Ya tienes una alerta activa para: {keyword}",
                reply_markup=keyboard
            )


async def admin_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /admin_users command - Only for admins."""
    user = update.effective_user
    if not user:
        return

    # Lista de IDs de administradores (configurable)
    ADMIN_TELEGRAM_IDS = [
        # Añade tu Telegram ID aquí
        # 123456789,  # Tu ID de Telegram
    ]
    
    if user.id not in ADMIN_TELEGRAM_IDS:
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return
    
    try:
        # Get all users from database
        session = db_manager.get_session()
        try:
            from ..models import User, Subscription
            
            # Get users with subscription counts
            users_query = session.query(
                User.telegram_id,
                User.username, 
                User.first_name, 
                User.last_name,
                User.created_at
            ).all()
            
            if not users_query:
                await update.message.reply_text("📭 No hay usuarios registrados.")
                return
            
            # Build user list message
            message = "👥 **Lista de Usuarios del Bot**\n\n"
            
            for user_data in users_query:
                telegram_id, username, first_name, last_name, created_at = user_data
                
                # Build display name
                name_parts = []
                if first_name:
                    name_parts.append(first_name)
                if last_name:
                    name_parts.append(last_name)
                display_name = " ".join(name_parts) if name_parts else "Sin nombre"
                
                username_text = f"@{username}" if username else "Sin username"
                
                # Get subscription count for this user
                user_db = session.query(User).filter_by(telegram_id=telegram_id).first()
                if user_db:
                    sub_count = session.query(Subscription).filter(
                        Subscription.user_id == user_db.id,
                        Subscription.is_active == True
                    ).count()
                else:
                    sub_count = 0
                
                message += f"• **{display_name}**\n"
                message += f"  └ {username_text}\n"
                message += f"  └ ID: `{telegram_id}`\n"
                message += f"  └ Suscripciones: {sub_count}\n"
                message += f"  └ Registrado: {created_at.strftime('%d/%m/%Y')}\n\n"
            
            total_users = len(users_query)
            message += f"📊 **Total: {total_users} usuarios**"
            
            # Send message (split if too long)
            if len(message) > 4000:
                # Split message
                parts = message.split('\n\n')
                current_message = "👥 **Lista de Usuarios del Bot**\n\n"
                
                for part in parts[1:-1]:  # Skip header and footer
                    if len(current_message + part) > 3800:
                        await update.message.reply_text(current_message, parse_mode="Markdown")
                        current_message = ""
                    current_message += part + "\n\n"
                
                # Send remaining + footer
                current_message += parts[-1]
                await update.message.reply_text(current_message, parse_mode="Markdown")
            else:
                await update.message.reply_text(message, parse_mode="Markdown")
                
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error in admin_users_command: {e}")
        await update.message.reply_text("❌ Error al obtener la lista de usuarios.")


async def search_datasets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle search functionality."""
    if not context.args:
        await update.message.reply_text(
            "🔍 <b>Búsqueda de Datasets</b>\n\n"
            "Para buscar datasets, usa:\n"
            "<code>/buscar [término de búsqueda]</code>\n\n"
            "<b>Ejemplos:</b>\n"
            "• <code>/buscar covid</code>\n"
            "• <code>/buscar población castilla</code>\n"
            "• <code>/buscar medio ambiente</code>",
            parse_mode="HTML"
        )
        return
    
    search_term = " ".join(context.args)
    try:
        # Using global API client instance to maintain cache consistency
        datasets, total_count = await api_client.get_datasets(
            search=search_term,
            limit=settings.datasets_per_page,
            offset=0
        )
        
        if not datasets:
            await update.message.reply_text(
                f"🔍 **Búsqueda: '{search_term}'**\n\n"
                f"❌ No se encontraron datasets que coincidan con tu búsqueda.\n\n"
                f"💡 **Sugerencias:**\n"
                f"• Prueba con términos más generales\n"
                f"• Usa palabras clave como 'salud', 'población', 'educación'\n"
                f"• Revisa la ortografía",
                parse_mode="HTML"
            )
            return
        
        keyboard = create_search_results_keyboard(datasets, search_term, 0, settings.datasets_per_page, total_count)
        
        # Show all search results with full titles
        search_results = []
        for i, dataset in enumerate(datasets, 1):
            title = clean_text_for_markdown(dataset.title) if dataset.title else "Sin título"
            # Don't truncate - show full title
            search_results.append(f"{i}. {title}")
        
        clean_search_term = clean_text_for_markdown(search_term)
        
        message = (
            f"🔍 <b>Resultados: '{clean_search_term}'</b>\n\n"
            f"📊 <b>Total:</b> {total_count} datasets encontrados\n"
            f"📄 <b>Página:</b> 1 de {(total_count + settings.datasets_per_page - 1) // settings.datasets_per_page} ({len(datasets)} datasets)\n\n"
            f"<b>Datasets encontrados:</b>\n" + "\n\n".join(search_results) + "\n\n"
            f"💡 <i>Haz clic en el número correspondiente para ver detalles.</i>"
        )
        
        await update.message.reply_text(
            message,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in search_datasets: {e}")
        await update.message.reply_text("❌ Error al realizar la búsqueda. Inténtalo más tarde.")


async def recent_datasets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show recently updated datasets with numbered interface."""
    try:
        # Using global API client instance to maintain cache consistency
        datasets, total_count = await api_client.get_datasets(
            limit=settings.datasets_per_page,
            offset=0,
            order_by="-metadata_processed"  # Most recent first
        )
        
        if not datasets:
            await update.message.reply_text("❌ No se pudieron cargar los datasets recientes.")
            return
        
        keyboard = create_recent_datasets_keyboard(datasets, 0, settings.datasets_per_page)
        
        # Show all recent datasets with full titles numbered
        recent_list = []
        for i, dataset in enumerate(datasets, 1):
            title = clean_text_for_markdown(dataset.title) if dataset.title else "Sin título"
            # Show modification date if available
            if dataset.metadata_processed and dataset.metadata_processed != "Dato no disponible":
                friendly_date = format_user_friendly_date(dataset.metadata_processed)
                recent_list.append(f"{i}. *{title}*\n   _Actualizado: {friendly_date}_")
            else:
                recent_list.append(f"{i}. *{title}*")
        
        message = (
            f"🕒 *Datasets Actualizados Recientemente*\n\n"
            f"📊 Total disponible: {total_count} datasets\n"
            f"📄 Mostrando los {len(datasets)} más recientes\n\n"
            f"**Últimas actualizaciones:**\n\n" + "\n\n".join(recent_list) + "\n\n"
            f"_Haz clic en el número para ver detalles._"
        )
        
        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in recent_datasets: {e}")
        await update.message.reply_text("❌ Error al cargar datasets recientes.")


async def handle_recent_datasets_callback(query, context) -> None:
    """Handle recent datasets callback."""
    try:
        # Using global API client instance to maintain cache consistency
        datasets, total_count = await api_client.get_datasets(
            limit=settings.datasets_per_page,
            offset=0,
            order_by="-metadata_processed"  # Most recent first
        )
        
        if not datasets:
            await query.edit_message_text("❌ No se pudieron cargar los datasets recientes.")
            return
        
        keyboard = create_recent_datasets_keyboard(datasets, 0, settings.datasets_per_page)
        
        # Show all recent datasets with full titles numbered
        recent_list = []
        for i, dataset in enumerate(datasets, 1):
            title = clean_text_for_markdown(dataset.title) if dataset.title else "Sin título"
            # Show modification date if available
            if dataset.metadata_processed and dataset.metadata_processed != "Dato no disponible":
                friendly_date = format_user_friendly_date(dataset.metadata_processed)
                recent_list.append(f"{i}. *{title}*\n   _Actualizado: {friendly_date}_")
            else:
                recent_list.append(f"{i}. *{title}*")
        
        message = (
            f"🕒 *Datasets Actualizados Recientemente*\n\n"
            f"📊 Total disponible: {total_count} datasets\n"
            f"📄 Mostrando los {len(datasets)} más recientes\n\n"
            f"**Últimas actualizaciones:**\n\n" + "\n\n".join(recent_list) + "\n\n"
            f"_Haz clic en el número para ver detalles._"
        )
        
        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in handle_recent_datasets_callback: {e}")
        await query.edit_message_text("❌ Error al cargar datasets recientes.")


async def handle_stats_callback(query, context) -> None:
    """Handle stats callback."""
    try:
        # Get themes with counts
        themes = await api_client.get_themes_with_real_counts()
        
        if not themes:
            await query.edit_message_text("❌ No se pudieron cargar las estadísticas.")
            return
        
        # Get total datasets count
        _, total_datasets = await api_client.get_datasets(limit=1)
        
        # Top themes
        top_themes = sorted(themes, key=lambda x: x.count, reverse=True)[:5]
        
        message = (
            f"📈 <b>Estadísticas de Datos Abiertos</b>\n\n"
            f"📊 <b>Total de datasets:</b> {total_datasets}\n"
            f"🏷️ <b>Categorías disponibles:</b> {len(themes)}\n\n"
            f"🔝 <b>Top 5 Categorías:</b>\n"
        )
        
        for i, theme in enumerate(top_themes, 1):
            message += f"{i}. {theme.name}: {theme.count} datasets\n"
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔍 Buscar Datasets", callback_data="start_search"),
            InlineKeyboardButton("🕒 Recientes", callback_data="recent_datasets")
        ], [
            InlineKeyboardButton("🏠 Inicio", callback_data="start")
        ]])
        
        await query.edit_message_text(
            message,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in handle_stats_callback: {e}")
        await query.edit_message_text("❌ Error al cargar estadísticas.")


async def handle_search_page(query, context, search_term: str, page: int) -> None:
    """Handle search pagination."""
    try:
        datasets, total_count = await api_client.get_datasets(
            search=search_term,
            limit=settings.datasets_per_page,
            offset=page * settings.datasets_per_page,
            order_by="-metadata_processed"  # Ensure consistent ordering
        )
        
        if not datasets:
            if page == 0:
                await query.edit_message_text(f"❌ No se encontraron resultados para '{search_term}'.")
            else:
                await query.edit_message_text(
                    f"❌ No hay más resultados en la página {page + 1} para '{search_term}'.\n\n"
                    f"💡 Intenta volver a la página anterior."
                )
            return
        
        keyboard = create_search_results_keyboard(datasets, search_term, page, settings.datasets_per_page, total_count)
        
        # Show all search results with full titles
        search_results = []
        for i, dataset in enumerate(datasets, 1):
            title = clean_text_for_markdown(dataset.title) if dataset.title else "Sin título"
            # Don't truncate - show full title
            search_results.append(f"{i}. {title}")
        
        clean_search_term = clean_text_for_markdown(search_term)
        total_pages = (total_count + settings.datasets_per_page - 1) // settings.datasets_per_page
        message = (
            f"🔍 <b>Resultados: '{clean_search_term}'</b>\n\n"
            f"📊 <b>Total:</b> {total_count} datasets encontrados\n"
            f"📄 <b>Página:</b> {page + 1} de {total_pages} ({len(datasets)} datasets)\n\n"
            f"<b>Datasets encontrados:</b>\n" + "\n\n".join(search_results) + "\n\n"
            f"💡 <i>Haz clic en el número para ver detalles del dataset.</i>"
        )
        
        await query.edit_message_text(
            message,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in handle_search_page: {e}")
        await query.edit_message_text("❌ Error al cargar la página de búsqueda.")


async def dataset_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show dataset statistics."""
    try:
        # Get themes with counts
        themes = await api_client.get_themes_with_real_counts()
        
        if not themes:
            await update.message.reply_text("❌ No se pudieron cargar las estadísticas.")
            return
        
        # Get total datasets count
        _, total_datasets = await api_client.get_datasets(limit=1)
        
        # Top themes
        top_themes = sorted(themes, key=lambda x: x.count, reverse=True)[:5]
        
        message = (
            f"📈 <b>Estadísticas de Datos Abiertos</b>\n\n"
            f"📊 <b>Total de datasets:</b> {total_datasets}\n"
            f"🏷️ <b>Categorías disponibles:</b> {len(themes)}\n\n"
            f"🔝 <b>Top 5 Categorías:</b>\n"
        )
        
        for i, theme in enumerate(top_themes, 1):
            message += f"{i}. {theme.name}: {theme.count} datasets\n"
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔍 Buscar Datasets", callback_data="start_search"),
            InlineKeyboardButton("🕒 Recientes", callback_data="recent_datasets")
        ], [
            InlineKeyboardButton("🏠 Inicio", callback_data="start")
        ]])
        
        await update.message.reply_text(
            message,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in dataset_stats: {e}")
        await update.message.reply_text("❌ Error al cargar estadísticas.")


async def user_bookmarks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's bookmarked datasets."""
    try:
        user_id = update.message.from_user.id
        user_db_id = db_manager.get_or_create_user(telegram_id=user_id)  # Now returns ID directly
        
        bookmarks = db_manager.get_user_bookmarks(user_db_id)
        
        if not bookmarks:
            message = (
                "⭐ **Mis Favoritos**\n\n"
                "❌ No tienes datasets favoritos guardados.\n\n"
                "💡 **Para guardar favoritos:**\n"
                "• Explora datasets desde /start\n"
                "• Usa el botón ⭐ en la información del dataset\n"
                "• Busca con /buscar y marca como favorito"
            )
        else:
            # Show bookmarks with numbered interface like other parts of the bot
            bookmarks_list = []
            for i, bookmark in enumerate(bookmarks[:15], 1):  # Limit to 15 to avoid message length issues
                title = clean_text_for_markdown(bookmark.dataset_title) if bookmark.dataset_title else "Sin título"
                bookmarks_list.append(f"{i}. {title}")
            
            message = (
                f"⭐ *Mis Favoritos* ({len(bookmarks)} datasets)\n\n"
                f"📄 Mostrando {len(bookmarks_list)} favoritos:\n\n" + 
                "\n\n".join(bookmarks_list) + "\n\n" +
                "_Haz clic en el número para ver detalles._"
            )
            
            if len(bookmarks) > 15:
                message += f"\n\n⚠️ Mostrando solo los primeros 15 de {len(bookmarks)} favoritos."
            
            # Create numbered keyboard buttons
            keyboard = []
            for i in range(0, min(len(bookmarks), 15), 3):  # Up to 3 buttons per row
                row = []
                for j in range(i, min(i + 3, min(len(bookmarks), 15))):
                    bookmark = bookmarks[j]
                    dataset_number = j + 1
                    callback_data = f"fav_num:{j}:{bookmark.dataset_id}"
                    
                    if len(callback_data.encode()) > 60:
                        short_id = callback_mapper.get_short_id(callback_data)
                        callback_data = f"s:{short_id}"
                    
                    row.append(InlineKeyboardButton(
                        f"{dataset_number}",
                        callback_data=callback_data
                    ))
                keyboard.append(row)
            
            # Add action buttons
            keyboard.append([
                InlineKeyboardButton("🔄 Actualizar", callback_data="refresh_bookmarks"),
                InlineKeyboardButton("🏠 Inicio", callback_data="start")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=reply_markup if bookmarks else None
        )
        
    except Exception as e:
        logger.error(f"Error in user_bookmarks: {e}")
        await update.message.reply_text("❌ Error al cargar favoritos.")


async def handle_bookmark_toggle(query, context, dataset_id: str, dataset_title: str) -> None:
    """Handle bookmark toggle (add/remove)."""
    try:
        user_id = query.from_user.id
        user_db_id = db_manager.get_or_create_user(telegram_id=user_id)  # Now returns ID directly
        
        is_bookmarked = db_manager.is_bookmarked(user_db_id, dataset_id)
        
        if is_bookmarked:
            # Remove bookmark
            success = db_manager.remove_bookmark(user_db_id, dataset_id)
            if success:
                await query.answer("❌ Eliminado de favoritos", show_alert=False)
            else:
                await query.answer("❌ Error al eliminar de favoritos", show_alert=True)
        else:
            # Add bookmark
            success = db_manager.add_bookmark(user_db_id, dataset_id, dataset_title)
            if success:
                await query.answer("⭐ Añadido a favoritos", show_alert=False)
            else:
                await query.answer("⚠️ Ya está en favoritos", show_alert=True)
                
    except Exception as e:
        logger.error(f"Error in handle_bookmark_toggle: {e}")
        await query.answer("❌ Error al procesar favorito", show_alert=True)


async def handle_refresh_bookmarks_callback(query, context) -> None:
    """Handle refresh bookmarks callback."""
    try:
        user_id = query.from_user.id
        user_db_id = db_manager.get_or_create_user(telegram_id=user_id)  # Now returns ID directly
        
        bookmarks = db_manager.get_user_bookmarks(user_db_id)
        
        if not bookmarks:
            message = (
                "⭐ **Mis Favoritos**\n\n"
                "❌ No tienes datasets favoritos guardados.\n\n"
                "💡 **Para guardar favoritos:**\n"
                "• Explora datasets desde /start\n"
                "• Usa el botón ⭐ en la información del dataset\n"
                "• Busca con /buscar y marca como favorito"
            )
            await query.edit_message_text(message, parse_mode="HTML")
        else:
            # Show bookmarks with numbered interface like other parts of the bot
            bookmarks_list = []
            for i, bookmark in enumerate(bookmarks[:15], 1):  # Limit to 15 to avoid message length issues
                title = clean_text_for_markdown(bookmark.dataset_title) if bookmark.dataset_title else "Sin título"
                bookmarks_list.append(f"{i}. {title}")
            
            message = (
                f"⭐ *Mis Favoritos* ({len(bookmarks)} datasets)\n\n"
                f"📄 Mostrando {len(bookmarks_list)} favoritos:\n\n" + 
                "\n\n".join(bookmarks_list) + "\n\n" +
                "_Haz clic en el número para ver detalles._"
            )
            
            if len(bookmarks) > 15:
                message += f"\n\n⚠️ Mostrando solo los primeros 15 de {len(bookmarks)} favoritos."
            
            # Create numbered keyboard buttons
            keyboard = []
            for i in range(0, min(len(bookmarks), 15), 3):  # Up to 3 buttons per row
                row = []
                for j in range(i, min(i + 3, min(len(bookmarks), 15))):
                    bookmark = bookmarks[j]
                    dataset_number = j + 1
                    callback_data = f"fav_num:{j}:{bookmark.dataset_id}"
                    
                    if len(callback_data.encode()) > 60:
                        short_id = callback_mapper.get_short_id(callback_data)
                        callback_data = f"s:{short_id}"
                    
                    row.append(InlineKeyboardButton(
                        f"{dataset_number}",
                        callback_data=callback_data
                    ))
                keyboard.append(row)
            
            # Add action buttons
            keyboard.append([
                InlineKeyboardButton("🔄 Actualizar", callback_data="refresh_bookmarks"),
                InlineKeyboardButton("🏠 Inicio", callback_data="start")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        
    except Exception as e:
        logger.error(f"Error in handle_refresh_bookmarks_callback: {e}")
        await query.edit_message_text("❌ Error al cargar favoritos.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    message = (
        "🤖 <b>Ayuda - Portal de Datos Abiertos</b>\n\n"
        
        "🏛️ <b>Sobre este bot</b>\n"
        "Bot oficial para explorar los datos abiertos de Castilla y León. "
        "Accede a más de 400 datasets actualizados desde la plataforma oficial.\n\n"
        
        "📋 <b>Comandos principales:</b>\n"
        "🏠 /start - Mostrar categorías y comenzar exploración\n"
        "🔍 /buscar [término] - Buscar datasets por texto\n"
        "🕒 /recientes - Ver datasets actualizados recientemente\n"
        "📅 /resumen_diario - Ver resúmenes diarios de datasets nuevos\n"
        "📈 /estadisticas - Ver estadísticas generales\n"
        "⭐ /favoritos - Ver tus datasets favoritos guardados\n"
        "🔔 /mis_alertas - Ver y gestionar tus suscripciones\n"
        "🔤 /alertas_palabras - Crear alertas por palabras clave\n"
        "❓ /help - Mostrar esta ayuda\n\n"
        
        "🎯 <b>Cómo usar el bot:</b>\n"
        "1️⃣ Selecciona una categoría (Salud, Educación, etc.)\n"
        "2️⃣ Elige 'Ver datasets' o refina por palabra clave\n"
        "3️⃣ Explora datasets y descarga datos directamente\n"
        "4️⃣ Suscríbete para recibir alertas de actualizaciones\n\n"
        
        "📊 <b>Formatos disponibles:</b>\n"
        "• CSV - Datos tabulares\n"
        "• XLSX - Hojas de cálculo Excel\n"
        "• JSON - Datos estructurados\n"
        "• GeoJSON - Datos geográficos\n"
        "• PDF/ZIP - Documentos adjuntos\n\n"
        
        "🔔 <b>Sistema de alertas:</b>\n"
        "• Suscríbete a categorías completas\n"
        "• Suscríbete a datasets específicos\n"
        "• Recibe notificaciones de nuevos datos\n"
        "• Gestiona suscripciones con /mis_alertas\n\n"
        
        "👨‍💻 <b>Créditos:</b>\n"
        "Desarrollado por: <b>Víctor Viloria Vázquez</b>\n"
        "GitHub: @ComputingVictor\n\n"
        
        "💡 ¡Usa /start para comenzar a explorar!"
    )
    
    await update.message.reply_text(message, parse_mode="HTML")


async def show_help_callback(query, context) -> None:
    """Handle help callback from inline keyboard."""
    message = (
        "🤖 <b>Ayuda - Portal de Datos Abiertos</b>\n\n"
        
        "🏛️ <b>Sobre este bot</b>\n"
        "Bot oficial para explorar los datos abiertos de Castilla y León. "
        "Accede a más de 400 datasets actualizados desde la plataforma oficial.\n\n"
        
        "📋 <b>Comandos principales:</b>\n"
        "🏠 /start - Mostrar categorías y comenzar exploración\n"
        "🔍 /buscar [término] - Buscar datasets por texto\n"
        "🕒 /recientes - Ver datasets actualizados recientemente\n"
        "📅 /resumen_diario - Ver resúmenes diarios de datasets nuevos\n"
        "📈 /estadisticas - Ver estadísticas generales\n"
        "⭐ /favoritos - Ver tus datasets favoritos guardados\n"
        "🔔 /mis_alertas - Ver y gestionar tus suscripciones\n"
        "🔤 /alertas_palabras - Crear alertas por palabras clave\n"
        "❓ /help - Mostrar esta ayuda\n\n"
        
        "🎯 <b>Cómo usar el bot:</b>\n"
        "1️⃣ Selecciona una categoría (Salud, Educación, etc.)\n"
        "2️⃣ Elige 'Ver datasets' o refina por palabra clave\n"
        "3️⃣ Explora datasets y descarga datos directamente\n"
        "4️⃣ Suscríbete para recibir alertas de actualizaciones\n\n"
        
        "📊 <b>Formatos disponibles:</b>\n"
        "• CSV - Datos tabulares\n"
        "• XLSX - Hojas de cálculo Excel\n"
        "• JSON - Datos estructurados\n"
        "• GeoJSON - Datos geográficos\n"
        "• PDF/ZIP - Documentos adjuntos\n\n"
        
        "🔔 <b>Sistema de alertas:</b>\n"
        "• Suscríbete a categorías completas\n"
        "• Suscríbete a datasets específicos\n"
        "• Recibe notificaciones de nuevos datos\n"
        "• Gestiona suscripciones con /mis_alertas\n\n"
        
        "👨‍💻 <b>Créditos:</b>\n"
        "Desarrollado por: <b>Víctor Viloria Vázquez</b>\n"
        "GitHub: @ComputingVictor\n\n"
        
        "💡 ¡Usa /start para comenzar a explorar!"
    )
    
    from .keyboards import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Volver al inicio", callback_data="start")]
    ])
    
    await query.edit_message_text(message, parse_mode="HTML", reply_markup=keyboard)


async def handle_dataset_preview(query, context, dataset_id: str) -> None:
    """Handle dataset preview request."""
    try:
        await query.answer("🔄 Cargando vista previa...", show_alert=False)
        
        # Get dataset info and some sample records
        dataset = await api_client.get_dataset_info(dataset_id)
        if not dataset:
            await query.answer("❌ Dataset no encontrado", show_alert=True)
            return
        
        # Create preview message with dataset info
        title = dataset.title[:50] + "..." if len(dataset.title) > 50 else dataset.title
        records_text = f"{dataset.records_count:,}" if dataset.records_count else "Dato no disponible"
        
        preview_message = (
            f"👁️ <b>Vista previa</b>\n\n"
            f"📄 <b>{title}</b>\n\n"
            f"📊 <b>Registros totales:</b> {records_text}\n"
            f"📅 <b>Última actualización:</b> {dataset.modified}\n"
            f"🏢 <b>Publicador:</b> {dataset.publisher}\n\n"
            f"💡 <b>Consejo:</b> Usa el botón de descarga para obtener los datos completos."
        )
        
        # Create back button
        callback_data = f"dataset:{dataset_id}"
        if len(callback_data.encode()) > 60:
            short_id = callback_mapper.get_short_id(callback_data)
            callback_data = f"s:{short_id}"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Volver al dataset", callback_data=callback_data)]
        ])
        
        await query.edit_message_text(
            preview_message,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in handle_dataset_preview: {e}")
        await query.answer("❌ Error al cargar vista previa", show_alert=True)


async def show_export_menu(query, context, dataset_id: str) -> None:
    """Show export format selection menu."""
    try:
        # Get dataset info and exports
        dataset = await api_client.get_dataset_info(dataset_id)
        exports = await api_client.get_dataset_exports(dataset_id)
        
        if not dataset:
            await query.answer("❌ Dataset no encontrado", show_alert=True)
            return
        
        # Create the export menu
        keyboard = create_export_menu_keyboard(dataset_id, exports)
        
        title = dataset.title[:60] + "..." if len(dataset.title) > 60 else dataset.title
        
        message = (
            f"💾 <b>Exportar: {title}</b>\n\n"
            f"📊 <b>Registros:</b> {dataset.records_count:,}\n\n"
            f"<b>📱 Envío directo:</b> El archivo se envía a tu chat (máx. 5 MB)\n"
            f"<b>🌐 Descarga web:</b> Enlace directo para descargar\n\n"
            f"💡 <i>Los archivos pequeños se procesan automáticamente</i>"
        )
        
        if exports:
            message += f"🎯 <b>Selecciona el formato que prefieras:</b>\n\n"
            # Show format list with sizes if available
            format_list = []
            for export in exports:
                format_name = export.format.upper()
                format_list.append(f"• <b>{format_name}</b>")
            
            if len(format_list) <= 6:  # Don't show too many in text
                message += "\n".join(format_list[:6])
                if len(format_list) > 6:
                    message += f"\n... y {len(format_list) - 6} formatos más"
        else:
            message += "❌ <b>No hay formatos de exportación disponibles</b>"
        
        await query.edit_message_text(
            message,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in show_export_menu: {e}")
        await query.answer("❌ Error al cargar menú de exportación", show_alert=True)



async def handle_dataset_share(query, context, dataset_id: str) -> None:
    """Handle dataset share request."""
    try:
        dataset = await api_client.get_dataset_info(dataset_id)
        if not dataset:
            await query.answer("❌ Dataset no encontrado", show_alert=True)
            return
        
        # Create share message with dataset info and link
        title = dataset.title[:60] + "..." if len(dataset.title) > 60 else dataset.title
        web_url = f"https://analisis.datosabiertos.jcyl.es/explore/dataset/{dataset_id}"
        
        share_message = (
            f"📤 <b>Compartir Dataset</b>\n\n"
            f"📄 <b>{title}</b>\n\n"
            f"🔗 <b>Enlace directo:</b>\n"
            f"<code>{web_url}</code>\n\n"
            f"📊 <b>Registros:</b> {dataset.records_count:,}\n"
            f"🏢 <b>Publicador:</b> {dataset.publisher}\n\n"
            f"💡 <b>Copia el enlace y compártelo con quien quieras</b>"
        )
        
        # Create back button and web link button
        callback_data = f"dataset:{dataset_id}"
        if len(callback_data.encode()) > 60:
            short_id = callback_mapper.get_short_id(callback_data)
            callback_data = f"s:{short_id}"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Abrir en navegador", url=web_url)],
            [InlineKeyboardButton("⬅️ Volver al dataset", callback_data=callback_data)]
        ])
        
        await query.edit_message_text(
            share_message,
            parse_mode="HTML",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error in handle_dataset_share: {e}")
        await query.answer("❌ Error al compartir dataset", show_alert=True)


async def handle_text_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages as search queries."""
    try:
        search_term = update.message.text.strip()
        
        # Skip if message is too short or empty
        if not search_term or len(search_term) < 2:
            await update.message.reply_text(
                "🔍 *Búsqueda automática*\n\n"
                "Escribe al menos 2 caracteres para buscar datasets.\n\n"
                "💡 También puedes usar:\n"
                "• /buscar [término] - Búsqueda manual\n"
                "• /start - Menú principal\n"
                "• /help - Ayuda",
                parse_mode="Markdown"
            )
            return
        
        # Show search indicator
        await update.message.reply_text(f"🔍 Buscando '{search_term}'...")
        
        # Use the global API client instance to maintain cache consistency
        # Use consistent sorting to ensure stable pagination
        datasets, total_count = await api_client.get_datasets(
            search=search_term, 
            limit=settings.datasets_per_page,
            offset=0,
            order_by="-metadata_processed"  # Ensure consistent ordering
        )
        
        if not datasets:
            no_results_message = (
                f"❌ No se encontraron datasets para '{search_term}'\n\n"
                "💡 **Sugerencias:**\n"
                "• Prueba con palabras más generales\n"
                "• Revisa la ortografía\n"
                "• Usa sinónimos o términos relacionados\n"
                "• Explora categorías con /start"
            )
            await update.message.reply_text(no_results_message)
            return
        
        keyboard = create_search_results_keyboard(datasets, search_term, 0, settings.datasets_per_page, total_count)
        
        # Show all search results with full titles
        search_results = []
        for i, dataset in enumerate(datasets, 1):
            title = clean_text_for_markdown(dataset.title) if dataset.title else "Sin título"
            # Don't truncate - show full title
            search_results.append(f"{i}. {title}")
        
        clean_search_term = clean_text_for_markdown(search_term)
        total_pages = (total_count + settings.datasets_per_page - 1) // settings.datasets_per_page
        message = (
            f"🔍 <b>Resultados: '{clean_search_term}'</b>\n\n"
            f"📊 <b>Total:</b> {total_count} datasets encontrados\n"
            f"📄 <b>Página:</b> 1 de {total_pages} ({len(datasets)} datasets)\n\n"
            f"<b>Datasets encontrados:</b>\n" + "\n\n".join(search_results) + "\n\n"
            f"💡 <i>Haz clic en el número para ver detalles del dataset.</i>"
        )
        
        await update.message.reply_text(
            message,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in handle_text_search: {e}")
        await update.message.reply_text("❌ Error al realizar la búsqueda. Intenta nuevamente.")


async def daily_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show daily summary of new datasets."""
    try:
        from datetime import date, timedelta
        from ..services.daily_summary import DailySummaryService
        
        daily_service = DailySummaryService()
        
        # Get date from command args or default to today
        target_date = date.today()
        if context.args:
            try:
                # Try to parse date in YYYY-MM-DD format
                date_str = context.args[0]
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                await update.message.reply_text(
                    "❌ Formato de fecha inválido. Usa YYYY-MM-DD (ejemplo: 2025-09-07)"
                )
                return
        
        # Get or create daily summary
        summary = await daily_service.get_daily_summary(target_date)
        
        if not summary:
            # Try to create summary for the date
            result = await daily_service.discover_and_track_new_datasets(target_date)
            summary = {
                'date': result['date'],
                'new_datasets_count': result['new_datasets_count'],
                'new_datasets': result.get('new_datasets', [])
            }
        
        # Format and send message
        message = daily_service.format_daily_summary_message(summary)
        
        # Create keyboard with recent days navigation
        keyboard = []
        today = date.today()
        recent_dates = [today - timedelta(days=i) for i in range(7)]
        
        # Create buttons for last 7 days (2 rows)
        for i in range(0, 7, 4):
            row = []
            for j in range(i, min(i + 4, 7)):
                date_obj = recent_dates[j]
                date_str = date_obj.strftime('%Y-%m-%d')
                label = "Hoy" if date_obj == today else f"{date_obj.day}/{date_obj.month}"
                row.append(InlineKeyboardButton(label, callback_data=f"daily_summary:{date_str}"))
            keyboard.append(row)
        
        # Add refresh button
        keyboard.append([
            InlineKeyboardButton("🔄 Actualizar", callback_data=f"daily_summary:{target_date.strftime('%Y-%m-%d')}")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
        # Close service
        await daily_service.close()
        
    except Exception as e:
        logger.error(f"Error in daily_summary: {e}")
        await update.message.reply_text("❌ Error al cargar el resumen diario.")


async def handle_daily_summary_callback(query, context) -> None:
    """Handle daily summary callback."""
    try:
        from datetime import datetime
        from ..services.daily_summary import DailySummaryService
        
        # Extract date from callback data
        _, date_str = query.data.split(":")
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        daily_service = DailySummaryService()
        
        # Get summary for the date
        summary = await daily_service.get_daily_summary(target_date)
        
        if not summary:
            # Try to create summary
            result = await daily_service.discover_and_track_new_datasets(target_date)
            summary = {
                'date': result['date'],
                'new_datasets_count': result['new_datasets_count'],
                'new_datasets': result.get('new_datasets', [])
            }
        
        # Format message
        message = daily_service.format_daily_summary_message(summary)
        
        # Create keyboard with navigation
        keyboard = []
        from datetime import date, timedelta
        today = date.today()
        recent_dates = [today - timedelta(days=i) for i in range(7)]
        
        # Create buttons for last 7 days
        for i in range(0, 7, 4):
            row = []
            for j in range(i, min(i + 4, 7)):
                date_obj = recent_dates[j]
                date_obj_str = date_obj.strftime('%Y-%m-%d')
                label = "Hoy" if date_obj == today else f"{date_obj.day}/{date_obj.month}"
                
                # Highlight current selection
                if date_obj == target_date:
                    label = f"• {label} •"
                
                row.append(InlineKeyboardButton(label, callback_data=f"daily_summary:{date_obj_str}"))
            keyboard.append(row)
        
        # Add refresh button
        keyboard.append([
            InlineKeyboardButton("🔄 Actualizar", callback_data=f"daily_summary:{date_str}")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
        # Close service
        await daily_service.close()
        
    except Exception as e:
        logger.error(f"Error in handle_daily_summary_callback: {e}")
        await query.edit_message_text("❌ Error al cargar el resumen diario.")


