#!/usr/bin/env python3
"""Test keyboard generation directly."""

import sys
import os

# Add project root to path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Now I'll manually recreate the keyboard creation logic to test it
from src.api.client import ExportFormat
from src.models.callback_map import callback_mapper
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def create_export_menu_keyboard_test(dataset_id: str, exports) -> InlineKeyboardMarkup:
    """Test version of create_export_menu_keyboard with debugging."""
    print(f"🎯 Creating keyboard for dataset: {dataset_id}")
    print(f"📊 Total exports: {len(exports)}")
    
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
        print("🔗 Creating web link buttons...")
        for i in range(0, len(exports), 2):
            row = []
            for j in range(i, min(i + 2, len(exports))):
                export = exports[j]
                icon = format_icons.get(export.format.lower(), "💾")
                button = InlineKeyboardButton(f"{icon} {export.format.upper()}", url=export.url)
                row.append(button)
                print(f"   Added web link: {export.format.upper()}")
            keyboard.append(row)
        
        # Add file download options for supported formats
        supported_formats = ["csv", "json", "xlsx"]
        available_formats = [e for e in exports if e.format.lower() in supported_formats]
        
        print(f"📱 Checking for download formats...")
        print(f"   Supported: {supported_formats}")
        print(f"   Available: {[e.format for e in available_formats]}")
        
        if available_formats:
            print("✅ Adding download section...")
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
                    print(f"   📝 Creating download button for {export.format}")
                    print(f"      Callback: {download_callback}")
                    
                    if len(download_callback.encode()) > 60:
                        short_id = callback_mapper.get_short_id(download_callback)
                        download_callback = f"s:{short_id}"
                        print(f"      🔗 Mapped to short: {download_callback}")
                    
                    button = InlineKeyboardButton(
                        f"📎 {export.format.upper()}", 
                        callback_data=download_callback
                    )
                    row.append(button)
                    print(f"      ✅ Button created: 📎 {export.format.upper()}")
                keyboard.append(row)
            
            print(f"✅ Download section added with {len(available_formats)} buttons")
        else:
            print("⚠️  No download buttons - no supported formats found!")
    
    # Back button
    back_callback = f"dataset:{dataset_id}"
    if len(back_callback.encode()) > 60:
        short_id = callback_mapper.get_short_id(back_callback)
        back_callback = f"s:{short_id}"
    
    keyboard.append([
        InlineKeyboardButton("⬅️ Volver al dataset", callback_data=back_callback),
        InlineKeyboardButton("🏠 Inicio", callback_data="start")
    ])
    
    print(f"🎯 Final keyboard has {len(keyboard)} rows")
    for i, row in enumerate(keyboard):
        print(f"   Row {i}: {len(row)} buttons")
        for j, button in enumerate(row):
            if button.callback_data:
                print(f"      Button {j}: '{button.text}' -> callback: {button.callback_data}")
            else:
                print(f"      Button {j}: '{button.text}' -> URL: {button.url}")
    
    return InlineKeyboardMarkup(keyboard)

def test_keyboard():
    """Test keyboard creation."""
    print("🚀 Testing keyboard creation...")
    
    # Create mock exports
    exports = [
        ExportFormat(format="csv", url="https://example.com/test.csv"),
        ExportFormat(format="json", url="https://example.com/test.json"), 
        ExportFormat(format="xlsx", url="https://example.com/test.xlsx"),
        ExportFormat(format="xml", url="https://example.com/test.xml"),
        ExportFormat(format="pdf", url="https://example.com/test.pdf"),
    ]
    
    dataset_id = "test-dataset-id"
    
    keyboard = create_export_menu_keyboard_test(dataset_id, exports)
    
    print("🎉 Test completed!")
    return keyboard

if __name__ == "__main__":
    keyboard = test_keyboard()