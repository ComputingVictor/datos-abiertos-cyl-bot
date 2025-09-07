#!/usr/bin/env python3
"""Test script para verificar la eliminación del publisher 'Administración Pública'."""

import sys
import os

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.alerts import clean_publisher_name

# Test cases
test_publishers = [
    "Junta de Castilla y León",
    "Consejería de Empleo - Junta de Castilla y León", 
    "Servicio Público de Empleo",
    "Dirección General de Estadística",
    "",
    "X"  # Too short case -> becomes "Administración Pública"
]

print("=== PRUEBA DE ELIMINACIÓN DE 'ADMINISTRACIÓN PÚBLICA' ===\n")

for original in test_publishers:
    cleaned = clean_publisher_name(original)
    should_show = cleaned and cleaned != "Administración Pública"
    
    print(f"Original: '{original}'")
    print(f"Limpio  : '{cleaned}'")
    print(f"Se muestra: {'SÍ' if should_show else 'NO'}")
    print("-" * 60)

# Simulate message formatting
print("\n=== EJEMPLOS DE MENSAJES ===\n")

test_cases = [
    ("Dataset de ejemplo 1", "Consejería de Empleo", "15/09/2025"),
    ("Dataset de ejemplo 2", "Administración Pública", "15/09/2025"),
    ("Dataset de ejemplo 3", "", "15/09/2025")
]

for title, publisher, date in test_cases:
    message = f"📄 **{title}**\n"
    
    cleaned_pub = clean_publisher_name(publisher)
    if cleaned_pub and cleaned_pub != "Administración Pública":
        message += f"🏢 {cleaned_pub}\n"
    
    message += f"📅 **Actualizado:** {date}\n\n"
    
    print(message)
    print("-" * 40)