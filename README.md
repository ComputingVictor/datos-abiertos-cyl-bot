# 🏛️ Datos Abiertos CyL - Bot de Telegram

**Tu asistente inteligente para explorar los datos abiertos de Castilla y León**

[![Telegram](https://img.shields.io/badge/Telegram-@cyl__asistente__bot-blue?logo=telegram)](https://t.me/cyl_asistente_bot)
[![Website](https://img.shields.io/badge/Website-Visitar-brightgreen?logo=github)](https://computingvictor.github.io/datos-abiertos-cyl-bot/)
[![License](https://img.shields.io/badge/License-MIT-yellow?logo=opensourceinitiative)](LICENSE)

## 🚀 Inicio Rápido

**👉 [Abrir bot en Telegram](https://t.me/cyl_asistente_bot) 👈**

**💻 [Visitar web oficial](https://computingvictor.github.io/datos-abiertos-cyl-bot/)**

## ✨ Características

- 🔍 **Búsqueda inteligente** con sinónimos en +400 datasets oficiales
- 📱 **Acceso móvil 24/7** desde Telegram
- 🔔 **Alertas automáticas** de actualizaciones
- 💾 **Descargas directas** en Excel, CSV, JSON
- ⭐ **Favoritos** para acceso rápido
- 📊 **Resúmenes diarios** automáticos de datasets nuevos

## 📊 Datos Disponibles

| Categoría | Contenido |
|-----------|-----------|
| 🏥 **Salud** | Hospitales, centros de salud, estadísticas sanitarias |
| 🎓 **Educación** | Centros educativos, becas, estadísticas académicas |
| 🏨 **Turismo** | Alojamientos, rutas, patrimonio, puntos de interés |
| 🌱 **Medio Ambiente** | Calidad del aire, espacios naturales, energías |
| 👥 **Demografía** | Población por municipios, censos, estadísticas |
| 💼 **Economía** | Empresas, comercio, indicadores, presupuestos |
| 🚌 **Transporte** | Líneas de autobús, estaciones, infraestructuras |
| 🏠 **Vivienda** | Precios, alquileres, promociones públicas |

## 📱 Comandos Principales

| Comando | Función |
|---------|---------|
| `/start` | Ver todas las categorías |
| `/buscar [término]` | Buscar datasets |
| `/favoritos` | Tus datasets guardados |
| `/mis_alertas` | Gestionar suscripciones |
| `/recientes` | Datasets actualizados |
| `/resumen_diario` | Datasets nuevos por día |
| `/catalogo` | Descargar catálogo completo Excel |
| `/alertas_palabras` | Alertas personalizadas |
| `/estadisticas` | Resumen del portal |

## 🔔 Sistema de Alertas

- **Categorías**: Suscríbete a temas completos (salud, educación...)
- **Datasets específicos**: Avisos de actualizaciones concretas
- **Palabras clave**: Alertas personalizadas `/alertas_palabras hospital`
- **Resúmenes automáticos**: Datasets nuevos cada día a las 9:00 AM

## 🛠️ Instalación y Despliegue

### Railway (Recomendado)

1. Fork este repositorio
2. Conecta tu GitHub con [Railway](https://railway.app)
3. Configura las variables de entorno:
   ```bash
   TELEGRAM_BOT_TOKEN=tu_token_aqui
   JCYL_API_BASE_URL=https://analisis.datosabiertos.jcyl.es
   ALERTS_ENABLED=true
   ```
4. Railway desplegará automáticamente usando el Dockerfile

### Docker Local

```bash
git clone https://github.com/computingvictor/datos-abiertos-cyl-bot
cd DATOS-ABIERTOS-CYL-BOT
cp .env.example .env  # Configura tu TELEGRAM_BOT_TOKEN
docker-compose up -d
```

### Ejecución Directa

```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="tu_token"
export DATABASE_URL="sqlite:///bot.db"
python main.py
```

## 🔧 Configuración

### Variables de Entorno

| Variable | Descripción | Requerida |
|----------|-------------|-----------|
| `TELEGRAM_BOT_TOKEN` | Token del bot | ✅ |
| `DATABASE_URL` | URL de base de datos | ❌ |
| `JCYL_API_BASE_URL` | API de datos JCyL | ❌ |
| `ALERTS_ENABLED` | Activar alertas | ❌ |
| `ALERTS_CHECK_INTERVAL_HOURS` | Frecuencia alertas (2h) | ❌ |

### Arquitectura

```
Telegram API ←→ FastAPI ←→ JCYL API
                    ↓
               PostgreSQL/SQLite
```

## 📊 Monitoreo

- **Health check**: `GET /health`
- **Test API**: `GET /debug/themes`
- **Webhook**: `POST /webhook`

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -m 'Añadir nueva funcionalidad'`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Abre un Pull Request

## 📞 Soporte

- 🤖 **Bot**: Usa `/help`
- 🐛 **Issues**: [GitHub Issues](https://github.com/computingvictor/datos-abiertos-cyl-bot/issues)

## 🏛️ Datos Oficiales

- **Portal**: [analisis.datosabiertos.jcyl.es](https://analisis.datosabiertos.jcyl.es)
- **Transparencia**: [gobiernoabierto.jcyl.es](https://gobiernoabierto.jcyl.es/web/es/transparencia.html)
- **Junta CyL**: [jcyl.es](https://www.jcyl.es)

## 👨‍💻 Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy
- **Bot**: python-telegram-bot
- **DB**: PostgreSQL/SQLite
- **Deploy**: Docker, Railway
- **Frontend**: HTML/CSS/JS (GitHub Pages)

## 📄 Licencia

MIT License - ver [LICENSE](LICENSE)

---

<div align="center">

**Desarrollado por [Víctor Viloria](https://github.com/ComputingVictor)**

*Haciendo la información pública más accesible para todos*

**[🚀 Usar bot](https://t.me/cyl_asistente_bot)** • **[💻 Código](https://github.com/computingvictor/datos-abiertos-cyl-bot)** • **[🌐 Web](https://computingvictor.github.io/datos-abiertos-cyl-bot/)**

</div>