#!/usr/bin/env python3
"""Test script para verificar el formato en negrita correcto."""

# Test de formato Telegram
print("=== PRUEBA DE FORMATO TELEGRAM ===\n")

# Simulando mensajes de ejemplo
datasets = [
    ("Previsión de jubilaciones", "Consejería de Empleo", "15 de septiembre de 2025"),
    ("Actuaciones del Pacto para la Recuperación Económica, el Empleo y la Cohesión Social", None, "14 de septiembre de 2025"),
    ("Contratos realizados en las provincias", "Servicio Público de Empleo", "13 de septiembre de 2025")
]

for title, publisher, date in datasets:
    message = f"📄 *{title}*\n"
    
    if publisher and publisher != "Administración Pública":
        message += f"🏢 {publisher}\n"
    
    message += f"📅 *Actualizado:* {date}\n\n"
    
    print(message)
    print("-" * 40)

print("\nFormato correcto para Telegram:")
print("*texto* = negrita")
print("**texto** = no funciona en Telegram")
print("_texto_ = cursiva")
print("`texto` = código")