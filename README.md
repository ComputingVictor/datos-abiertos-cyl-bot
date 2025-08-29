# 🏛️ Portal de Datos Abiertos - Bot de Telegram

**Bot oficial para explorar los datos abiertos de Castilla y León de forma fácil e intuitiva**

[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue)](https://t.me/tu_bot)
[![Python](https://img.shields.io/badge/Python-3.11+-green)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

## 🌟 ¿Qué es este bot?

Un bot de Telegram que te permite acceder a **más de 400 datasets** oficiales de la Junta de Castilla y León de forma gratuita y sin complicaciones. Explora información sobre salud, educación, turismo, medio ambiente y mucho más.

### 📊 ¿Qué puedes encontrar?

- **Datos de Salud**: Hospitales, centros de salud, estadísticas sanitarias
- **Educación**: Centros educativos, programas formativos, becas
- **Turismo**: Alojamientos, rutas turísticas, patrimonio cultural  
- **Medio Ambiente**: Calidad del aire, espacios naturales, energías renovables
- **Demografía**: Población, censos, estadísticas municipales
- **Economía**: Empresas, comercio, indicadores económicos
- **Y mucho más**: Transporte, vivienda, deportes, cultura...

## 🚀 ¿Cómo empezar?

### 1. Busca el bot en Telegram
- Busca `@tu_bot_name` en Telegram
- O haz clic [aquí](https://t.me/tu_bot) para acceder directamente

### 2. Explora las categorías
- Usa `/start` para ver todas las categorías disponibles
- Cada categoría muestra cuántos datasets contiene
- Los emojis te ayudan a identificar rápidamente cada tema

### 3. Descarga los datos que necesites
- Múltiples formatos disponibles: **Excel, CSV, JSON, PDF**
- Enlaces directos de descarga desde fuentes oficiales
- Sin registros ni limitaciones

## 🔔 Sistema de Alertas

### ¿Te interesa estar al día?

**Suscríbete a categorías completas:**
- Recibe notificaciones cuando se publiquen nuevos datos de salud, educación, etc.
- Ejemplo: "Nuevo dataset sobre centros de salud disponible"

**Suscríbete a datasets específicos:**
- Te avisamos cuando se actualicen datos concretos que te interesan
- Ejemplo: "Actualizada la lista de hospitales de León"

### Gestiona tus alertas
- Usa `/mis_alertas` para ver tus suscripciones activas
- Cancela alertas cuando quieras con un clic
- Sin spam: solo recibes lo que realmente te interesa

## 📱 Comandos principales

| Comando | Descripción |
|---------|-------------|
| `/start` | Ver todas las categorías de datos disponibles |
| `/buscar [término]` | Buscar datasets por palabra clave |
| `/recientes` | Ver los datos más recientemente actualizados |
| `/estadisticas` | Estadísticas generales del portal |
| `/favoritos` | Tus datasets guardados como favoritos |
| `/mis_alertas` | Gestionar tus suscripciones de alertas |
| `/help` | Ayuda completa y información del bot |

## 💡 Casos de uso reales

### 👨‍🎓 Estudiantes e Investigadores
- **TFG/TFM**: Datos oficiales para proyectos académicos
- **Análisis estadísticos**: Información demográfica y económica
- **Visualización de datos**: CSV y JSON listos para usar

### 🏢 Empresas y Emprendedores  
- **Análisis de mercado**: Datos económicos y demográficos
- **Localización**: Información sobre municipios y comarcas
- **Turismo rural**: Rutas, alojamientos y puntos de interés

### 👨‍💼 Profesionales del Sector Público
- **Administraciones**: Benchmarking con otros municipios
- **ONGs**: Datos para proyectos sociales y ambientales  
- **Consultorías**: Informes con datos oficiales actualizados

### 📰 Periodistas y Comunicadores
- **Noticias basadas en datos**: Información oficial verificada
- **Seguimiento de tendencias**: Datos actualizados automáticamente
- **Contexto regional**: Comparativas entre provincias y municipios

## ✨ Ventajas del bot

### 🎯 **Fácil de usar**
- No necesitas conocimientos técnicos
- Interfaz intuitiva con botones y menús
- Búsqueda por categorías o palabras clave

### 📊 **Datos oficiales**
- Directamente de la Junta de Castilla y León
- Información actualizada automáticamente
- Sin manipulación ni interpretación

### 🔄 **Siempre actualizado**  
- Los datos se sincronizan automáticamente
- Alertas cuando hay nuevas actualizaciones
- Sin necesidad de consultar webs manualmente

### 💰 **Completamente gratuito**
- Sin limitaciones de descargas
- Sin registros complicados
- Acceso 24/7 desde cualquier dispositivo

## 🛠️ Para desarrolladores

### 🚀 Ejecutar tu propia instancia

**Prerrequisitos:**
- Token de bot de Telegram ([obtener aquí](https://t.me/BotFather))
- Docker y Docker Compose (recomendado)

**Instalación rápida:**
```bash
# 1. Clonar el repositorio
git clone https://github.com/ComputingVictor/DATOS-ABIERTOS-CYL-BOT
cd DATOS-ABIERTOS-CYL-BOT

# 2. Configurar variables
cp .env.example .env
# Edita .env y añade tu TELEGRAM_BOT_TOKEN

# 3. Ejecutar con Docker
docker-compose up -d
```

### 🔧 Configuración

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `TELEGRAM_BOT_TOKEN` | Token del bot (requerido) | - |
| `DATABASE_URL` | Base de datos | `sqlite:///data/bot.db` |
| `ALERTS_ENABLED` | Activar alertas automáticas | `true` |
| `ALERTS_CHECK_INTERVAL_HOURS` | Frecuencia de checks | `6` |

### 📡 API REST incluida

El bot también expone una API REST:
- `GET /health` - Estado del servicio
- `GET /debug/themes` - Test de conexión con JCYL
- `GET /debug/datasets` - Test de listado de datasets

## 🔒 Privacidad y transparencia

### ✅ **Qué datos almacenamos**
- Tu ID de Telegram (para enviarte alertas)
- Tus suscripciones a categorías/datasets
- Tus datasets marcados como favoritos

### ❌ **Qué NO almacenamos**
- Datos personales (nombre, teléfono, etc.)
- Contenido de los datasets (solo metadatos)
- Historial de búsquedas o descargas

### 🛡️ **Seguridad**
- Base de datos local cifrada
- Sin tracking ni análisis de comportamiento
- Código fuente abierto para auditoría

## 📞 Soporte y contribuciones

### 🐛 ¿Encontraste un error?
1. Describe el problema detalladamente
2. Incluye capturas si es posible
3. Crea un [issue en GitHub](https://github.com/ComputingVictor/DATOS-ABIERTOS-CYL-BOT/issues)

### 💡 ¿Tienes una idea?
- Comparte sugerencias de mejora
- Propón nuevas funcionalidades
- Contribuye con código (PRs bienvenidos)

### 📈 ¿Quieres más datos?
Este bot utiliza la API oficial de datos abiertos de JCyL. Si necesitas datos que no están disponibles, contacta directamente con:
- [Portal de Datos Abiertos JCyL](https://datosabiertos.jcyl.es)
- [Servicio de soporte JCyL](mailto:soporte@jcyl.es)

## 👨‍💻 Créditos

**Desarrollado por:** Víctor Viloria Vázquez  
**GitHub:** [@ComputingVictor](https://github.com/ComputingVictor)  
**Tecnologías:** Python, Telegram Bot API, FastAPI, SQLAlchemy

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más detalles.

---

**🏛️ Portal de Datos Abiertos - Junta de Castilla y León**  
*Explorando la información pública de manera simple y accesible*