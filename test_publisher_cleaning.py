#!/usr/bin/env python3
"""Test script para verificar la limpieza de publishers y títulos completos."""

import sys
import os

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.alerts import clean_dataset_title, clean_publisher_name

# Test cases for publishers
test_publishers = [
    "Junta de Castilla y León",
    "Consejería de Empleo - Junta de Castilla y León",
    "Consejería de la Presidencia de la Junta de Castilla y León",
    "Servicio Público de Empleo",
    "Dirección General de Estadística",
    "",
    "X"  # Too short case
]

# Test cases for full titles
test_long_titles = [
    "Actuaciones del Pacto para la Recuperación Económica, el Empleo y la Cohesión Social de Castilla y León",
    "Representantes en consejos de administración de empresas públicas y participadas de la Junta de Castilla y León",
    "Directorio de la administración general e institucional de la comunidad autónoma"
]

print("=== PRUEBA DE LIMPIEZA DE PUBLISHERS ===\n")

for original in test_publishers:
    cleaned = clean_publisher_name(original)
    print(f"Original: '{original}'")
    print(f"Limpio  : '{cleaned}'")
    print("-" * 60)

print("\n=== PRUEBA DE TÍTULOS COMPLETOS ===\n")

for original in test_long_titles:
    cleaned = clean_dataset_title(original)
    print(f"Original: {original}")
    print(f"Limpio  : {cleaned}")
    print(f"Longitud: {len(cleaned)} caracteres")
    print("-" * 60)