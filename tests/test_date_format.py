#!/usr/bin/env python3
"""Test script para verificar el formato de fechas con hora."""

import sys
import os

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api.client import format_user_friendly_date

# Test cases
test_dates = [
    "2025-09-07T14:30:45.123000+00:00",  # Con hora
    "2025-09-07T00:00:00.000000+00:00",  # Medianoche (no debe mostrar hora)
    "2025-09-07T09:15:30+02:00",         # Con zona horaria diferente
    "2025-09-07",                        # Solo fecha
    "2025-12-25T23:59:59.999Z",          # Formato Z
    "Dato no disponible",                # Dato no disponible
    "",                                  # Vacío
    None                                 # None
]

print("=== PRUEBA DE FORMATO DE FECHAS CON HORA ===\n")

for date_str in test_dates:
    try:
        formatted = format_user_friendly_date(str(date_str) if date_str is not None else "")
        print(f"Original: {date_str}")
        print(f"Formateado: {formatted}")
        print("-" * 50)
    except Exception as e:
        print(f"Original: {date_str}")
        print(f"Error: {e}")
        print("-" * 50)

print("\n=== EJEMPLO DE DATOS RECIENTES ===\n")

# Simulando títulos en negrita
example_titles = [
    "Previsión de jubilaciones",
    "Contratos realizados en las provincias de Castilla y León", 
    "Actuaciones del Pacto para la Recuperación Económica, el Empleo y la Cohesión Social"
]

example_dates = [
    "2025-09-07T14:30:45.123000+00:00",
    "2025-09-06T00:00:00.000000+00:00",
    "2025-09-05T09:15:30+02:00"
]

for i, (title, date) in enumerate(zip(example_titles, example_dates), 1):
    formatted_date = format_user_friendly_date(date)
    print(f"{i}. *{title}*")
    print(f"   _Actualizado: {formatted_date}_\n")