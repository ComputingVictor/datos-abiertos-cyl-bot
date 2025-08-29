# JCYL Encyclopedia Bot

Bot de Telegram y microservicio FastAPI para explorar los datos abiertos de Castilla y León utilizando la API Explore v2.1.

## 🎯 Funcionalidades

### Exploración de Datos
- **Índice por categorías**: Navega por themes con contadores de datasets
- **Refinamiento**: Filtra por palabras clave (keywords) dentro de cada categoría
- **Datasets paginados**: Lista de datasets con información básica
- **Ficha detallada**: Información completa de cada dataset

### Descarga de Datos
- **Enlaces directos**: Botones con URLs de descarga en múltiples formatos
- **Formatos soportados**: CSV, XLSX, JSON, GeoJSON, Parquet, KML, Shapefile
- **Adjuntos**: Acceso a archivos PDF, ZIP y otros documentos

### Sistema de Alertas
- **Suscripciones a categorías**: Notificaciones de nuevos datasets en un theme
- **Suscripciones a datasets**: Alertas cuando cambia un dataset específico
- **Gestión personal**: Comandos para suscribirse y cancelar alertas

## 🏗️ Arquitectura

```
jcyl-encyclopedia-bot/
├── src/
│   ├── api/                 # Cliente API Explore v2.1
│   ├── bot/                 # Bot de Telegram
│   ├── models/              # Modelos de base de datos
│   └── services/            # FastAPI, configuración, alertas
├── main.py                  # Punto de entrada principal
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 🚀 Instalación y Uso

### 1. Prerrequisitos
- Python 3.11+
- Token de bot de Telegram (obtenido de [@BotFather](https://t.me/BotFather))

### 2. Configuración

```bash
# Clonar el repositorio
git clone <repository-url>
cd jcyl-encyclopedia-bot

# Crear archivo de configuración
cp .env.example .env
```

Editar `.env` con tu configuración:
```bash
TELEGRAM_BOT_TOKEN=tu_token_aqui
# Opcional: configurar webhook para producción
TELEGRAM_WEBHOOK_URL=https://tudominio.com
```

### 3. Ejecución con Docker (Recomendado)

```bash
# Crear directorio de datos
mkdir -p data

# Ejecutar con Docker Compose
docker-compose up -d

# Ver logs
docker-compose logs -f
```

### 4. Ejecución manual

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar aplicación
python main.py
```

## 📱 Comandos del Bot

- `/start` - Explorar categorías de datos
- `/mis_alertas` - Gestionar suscripciones
- `/help` - Mostrar ayuda

## 🔧 Configuración

### Variables de Entorno

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `TELEGRAM_BOT_TOKEN` | Token del bot de Telegram | **Requerido** |
| `TELEGRAM_WEBHOOK_URL` | URL para webhook (opcional) | - |
| `DATABASE_URL` | URL de la base de datos | `sqlite:///data/jcyl_bot.db` |
| `ALERTS_ENABLED` | Habilitar sistema de alertas | `true` |
| `ALERTS_CHECK_INTERVAL_HOURS` | Frecuencia de checks (horas) | `6` |
| `DATASETS_PER_PAGE` | Datasets por página | `10` |

### Modos de Ejecución

#### Modo Polling (Desarrollo)
- No requiere webhook público
- Ideal para desarrollo local
- Configuración: dejar `TELEGRAM_WEBHOOK_URL` vacío

#### Modo Webhook (Producción)
- Requiere URL pública HTTPS
- Mejor rendimiento en producción
- Configuración: establecer `TELEGRAM_WEBHOOK_URL`

## 🗄️ Base de Datos

### SQLite (por defecto)
- Archivo local: `data/jcyl_bot.db`
- Sin configuración adicional requerida

### PostgreSQL (opcional)
Descomentar en `docker-compose.yml` y configurar:
```bash
DATABASE_URL=postgresql://username:password@postgres:5432/jcyl_bot
```

## 🔍 API REST

El servicio expone endpoints REST:

- `GET /health` - Estado del servicio
- `GET /debug/themes` - Probar conexión con API JCyL
- `GET /debug/datasets` - Probar listado de datasets
- `GET /debug/dataset/{id}` - Probar información de dataset

## ⚡ Sistema de Alertas

### Detección de Cambios

**Para datasets:**
- Campo `modified` modificado
- Campo `data_processed` modificado  
- Campo `metadata_processed` modificado
- Cambio en número de registros (`records_count`)

**Para categorías:**
- Nuevos datasets añadidos al theme
- Cambios en datasets existentes del theme

### Frecuencia
- Configuración por defecto: cada 6 horas
- Configurable via `ALERTS_CHECK_INTERVAL_HOURS`
- Ejecución con APScheduler

## 🛠️ API de JCYL Utilizada

Todos los datos provienen de la **API Explore v2.1** oficial:

- Base URL: `https://analisis.datosabiertos.jcyl.es`
- Endpoints utilizados:
  - `/api/explore/v2.1/catalog/facets` - Categorías y palabras clave
  - `/api/explore/v2.1/catalog/datasets` - Listado de datasets
  - `/api/explore/v2.1/catalog/datasets/{id}` - Información del dataset
  - `/api/explore/v2.1/catalog/datasets/{id}/exports` - Formatos de descarga
  - `/api/explore/v2.1/catalog/datasets/{id}/attachments` - Archivos adjuntos

## 🔧 Desarrollo

### Estructura del Código
- `src/api/client.py` - Cliente HTTP para API JCyL
- `src/bot/handlers.py` - Handlers del bot de Telegram
- `src/bot/keyboards.py` - Teclados inline del bot
- `src/models/database.py` - Modelos SQLAlchemy
- `src/services/alerts.py` - Sistema de alertas
- `src/services/scheduler.py` - Programador de tareas

### Logging
Los logs incluyen:
- Actividad del bot de Telegram
- Solicitudes a la API de JCyL
- Ejecución del sistema de alertas
- Errores y warnings

## 📄 Datos y Privacidad

- **Cero datos inventados**: Toda la información proviene de la API oficial
- **Sin scraping**: Uso exclusivo de endpoints oficiales
- **Almacenamiento mínimo**: Solo datos de usuarios y suscripciones
- **Transparencia**: Campo "Dato no disponible" cuando falta información

## 🚨 Troubleshooting

### Bot no responde
- Verificar `TELEGRAM_BOT_TOKEN`
- Comprobar logs: `docker-compose logs jcyl-bot`
- Verificar conectividad con API JCyL

### Alertas no funcionan
- Verificar `ALERTS_ENABLED=true`
- Comprobar logs del scheduler
- Verificar base de datos

### Error de conexión con API
- Verificar `JCYL_API_BASE_URL`
- Comprobar conectividad de red
- Revisar logs de la API

## 📞 Soporte

Para problemas o sugerencias:
1. Revisar logs en `docker-compose logs`
2. Verificar configuración en `.env`
3. Probar endpoints de debug: `/debug/themes`

## 📊 Monitoreo

- Health check: `GET /health`
- Estado del contenedor: `docker-compose ps`
- Logs en tiempo real: `docker-compose logs -f`

---

**Enciclopedia JCyL** - Explorando los datos abiertos de Castilla y León 🏛️