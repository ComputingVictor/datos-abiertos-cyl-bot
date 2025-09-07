#!/usr/bin/env python3
"""Test script para verificar la limpieza de títulos."""

import sys
import os

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.alerts import clean_dataset_title

# Test cases
test_titles = [
    "Contratos ordinarios de la Junta de Castilla y León",
    "Subvenciones concedidas Junta de Castilla y León",
    "Registro de municipios de Castilla y León",
    "Estadísticas web de la Junta de Castilla y Leon",  # sin tilde
    "Directorio de la administración general e institucional de la comunidad",
    "Planes y programas",  # sin referencias a la Junta
    "Datos básicos de elecciones a las Cortes de Castilla y León"
]

print("=== PRUEBA DE LIMPIEZA DE TÍTULOS ===\n")

for original in test_titles:
    cleaned = clean_dataset_title(original)
    print(f"Original: {original}")
    print(f"Limpio  : {cleaned}")
    print("-" * 60)