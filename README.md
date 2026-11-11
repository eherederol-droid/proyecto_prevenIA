# PrevenIA — Sistema de Prevención de Lesiones Deportivas con IA

> Plataforma full-stack para análisis postural con IA, detección de riesgo de lesiones y seguimiento de atletas deportivos.

---

## 🏗️ Arquitectura del Sistema

```
prevenia/
├── frontend/               ← HTML/CSS/JS (responsive, mobile + desktop)
│   ├── login.html          ← Pantalla de inicio de sesión
│   ├── register.html       ← Registro de profesionales
│   ├── dashboard.html      ← App principal (SPA multi-página)
│   ├── css/
│   │   └── styles.css      ← Design System PrevenIA (#2563EB)
│   └── js/
│       └── api.js          ← Cliente HTTP con JWT auto-refresh
│
├── backend/                ← Django 4.2 + DRF
│   ├── prevenia_api/       ← Configuración principal
│   │   ├── settings.py     ← Config completa (AWS, Celery, JWT, etc.)
│   │   ├── urls.py         ← Rutas globales
│   │   └── celery.py       ← Celery + tareas programadas
│   ├── users/              ← Usuarios con roles (médico, entrenador, atleta)
│   ├── athletes/           ← Gestión completa de atletas
│   ├── assessments/        ← Evaluaciones posturales + IA
│   │   ├── posture_analyzer.py  ← MediaPipe + OpenCV (ángulos articulares)
│   │   ├── models.py       ← PosturalAssessment, JointAngle, Alert
│   │   ├── views.py        ← API endpoints con análisis sync/async
│   │   └── tasks.py        ← Celery: análisis async, notificaciones SES
│   └── reports/            ← Generación de reportes PDF
│
├── docker-compose.yml      ← PostgreSQL + Redis + Django + Nginx + Celery
└── nginx.conf              ← Reverse proxy frontend ↔ backend
```

---

## ⚡ Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| **Frontend** | HTML5, CSS3 (Design System propio), JavaScript ES6+ |
| **Backend** | Django 4.2, Django REST Framework 3.14 |
| **Autenticación** | JWT (SimpleJWT) con auto-refresh |
| **IA / Análisis** | MediaPipe Pose, OpenCV (ángulos articulares, riesgo) |
| **Base de Datos** | PostgreSQL (AWS RDS en producción) |
| **Cola de Tareas** | Celery + Redis |
| **Almacenamiento** | AWS S3 (imágenes, videos, reportes PDF) |
| **Análisis IA Cloud** | AWS Lambda (opcional, para escala) |
| **Email** | AWS SES |
| **Servidor** | Gunicorn + Nginx |
| **Contenedores** | Docker + Docker Compose |

---

## 🚀 Instalación Local (Desarrollo)

### Prerrequisitos
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Git

### 1. Clonar y configurar backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

pip install -r requirements.txt

# Descargar el modelo ligero de MediaPipe para análisis postural
New-Item -ItemType Directory -Force assessments\models | Out-Null
curl.exe -fL "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task" -o assessments\models\pose_landmarker_lite.task

# Copiar variables de entorno
copy .env.example .env
# Editar .env con tus credenciales
```

### 2. Base de datos

```bash
# Crear base de datos PostgreSQL
createdb prevenia_db

# Migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# (Opcional) Cargar datos de ejemplo
python manage.py loaddata fixtures/demo_data.json
```

### 3. Ejecutar servidor

```bash
# Django dev server
python manage.py runserver

# Celery worker (en otra terminal)
celery -A prevenia_api worker --loglevel=info

# Celery beat (tareas programadas)
celery -A prevenia_api beat --loglevel=info
```

### 4. Frontend

No abras los HTML con `file://`: la cámara y las llamadas a la API necesitan un origen web. Desde la raíz del proyecto ejecuta:

```bash
# Python simple server (en otra terminal)
python -m http.server 3000
# Luego abre http://localhost:3000/frontend/login.html
```

En desarrollo, el frontend en `localhost:3000` usa la API de Django en `localhost:8000`. La cámara requiere permiso del navegador; fuera de localhost se necesita HTTPS. En móviles, **Usar cámara trasera** alterna entre las cámaras disponibles en la vista de análisis postural; si no se puede abrir la seleccionada, el sistema intenta recuperar la anterior. Al iniciar la cámara, el esqueleto se actualiza en vivo; las desviaciones se muestran en rojo y al pulsar **Analizar con IA** se guarda la evaluación y se crean las alertas correspondientes.

### Compartir una demostración por Internet

Para compartir una demo temporal con otras personas, instala [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) y ejecuta desde PowerShell, en la raíz del proyecto:

```powershell
winget install --id Cloudflare.cloudflared --exact --source winget
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\share.ps1
```

Si ya descargaste el ejecutable oficial y no lo instalaste, indica su ruta antes de iniciar el script:

```powershell
$env:CLOUDFLARED_PATH = "$env:TEMP\prevenia-demo-share\cloudflared.exe"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\share.ps1
```

El script muestra un enlace HTTPS temporal. Mantén abierta la ventana de PowerShell mientras tus amigos lo usan; `Ctrl+C` cierra los servidores y el enlace. El túnel sirve solo el frontend, la API y archivos multimedia; el backend queda enlazado a `127.0.0.1`, se desactiva el modo de depuración y no se publica el panel administrativo. Usa una base de datos de demostración con datos ficticios: no compartas datos reales de atletas ni credenciales sensibles.

---

## 🐳 Docker (Producción)

```bash
# 1. Configurar .env
copy backend\.env.example backend\.env
# Editar backend/.env

# 2. Levantar todos los servicios
docker-compose up -d

# 3. Migraciones
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser

# App disponible en http://localhost
```

---

## 🔌 API Endpoints

### Autenticación
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/login/` | Iniciar sesión → JWT |
| `POST` | `/api/v1/auth/register/` | Registrar profesional |
| `POST` | `/api/v1/auth/password-reset/` | Solicitar enlace de recuperación por correo |
| `POST` | `/api/v1/auth/password-reset/confirm/` | Cambiar contraseña usando el enlace de un solo uso |
| `POST` | `/api/v1/auth/logout/` | Cerrar sesión |
| `POST` | `/api/v1/auth/refresh/` | Renovar access token |
| `GET/PATCH` | `/api/v1/auth/me/` | Perfil del usuario actual |

La recuperación requiere configurar `FRONTEND_URL` con la URL pública del frontend y los datos SMTP (`EMAIL_HOST_USER` y `EMAIL_HOST_PASSWORD`) en el entorno de despliegue. En desarrollo (`DEBUG=True`) y sin credenciales SMTP, el enlace se escribe en la consola del backend.

### Atletas
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/v1/athletes/` | Listar atletas (filtros: sport, risk_level) |
| `POST` | `/api/v1/athletes/` | Crear atleta |
| `GET` | `/api/v1/athletes/{id}/` | Detalle completo del atleta |
| `GET` | `/api/v1/athletes/{id}/assessments/` | Historial de evaluaciones |
| `GET` | `/api/v1/athletes/{id}/alerts/` | Alertas activas |
| `GET` | `/api/v1/athletes/risk-summary/` | Distribución de riesgo |

### Análisis Postural (IA)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/v1/assessments/analyze-image/` | **Upload imagen → análisis IA inmediato** |
| `POST` | `/api/v1/assessments/pose-preview/` | Analizar fotograma de cámara en vivo sin guardarlo |
| `POST` | `/api/v1/assessments/{id}/analyze/` | Analizar evaluación existente |
| `GET` | `/api/v1/assessments/` | Historial de evaluaciones |
| `GET` | `/api/v1/assessments/{id}/pdf/` | Reporte PDF |
| `POST` | `/api/v1/assessments/alerts/resolve/{id}/` | Resolver alerta |

### Reportes
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/v1/reports/dashboard-stats/` | Stats para el dashboard |
| `POST` | `/api/v1/reports/generate/` | Generar reporte |
| `GET` | `/api/v1/reports/{id}/download/` | Descargar PDF |

**Documentación interactiva:** `http://localhost:8000/api/docs/` (Swagger UI)

---

## 🤖 Motor de IA — Análisis Postural

El analizador usa **MediaPipe Tasks Pose Landmarker** y su modelo ligero oficial para detectar 33 puntos corporales y calcular. El archivo `backend/assessments/models/pose_landmarker_lite.task` debe estar presente para iniciar el análisis; el comando de instalación anterior lo descarga del repositorio oficial de modelos de MediaPipe.

| Métrica | Descripción |
|---------|-------------|
| **Ángulos articulares** | Rodillas (L/R), caderas, hombros, codos, tobillos, columna |
| **Asimetrías** | Diferencia izquierda-derecha en articulaciones pares |
| **Puntuación de riesgo** | 0–100 ponderado por zona y severidad |
| **Nivel de riesgo** | Bajo / Medio / Alto / Crítico |
| **Confianza del modelo** | % de visibilidad de puntos clave |
| **Problemas detectados** | Valgo de rodilla, asimetría pélvica, desviación lateral, etc. |
| **Recomendaciones** | Generadas automáticamente según los hallazgos |
| **Técnica por ejercicio** | Indicaciones visuales por fotograma para sentadilla, zancada, peso muerto, puente de glúteos, elevación de pantorrillas, subida al cajón, salto/aterrizaje, flexión, planchas, burpee, jumping jack, escaladores, press sobre la cabeza, curl de bíceps, remo, fondos, elevación lateral y abdominales; selecciona también la vista adecuada |

La revisión de ejercicios usa reglas geométricas sobre los puntos visibles y ofrece indicaciones orientativas, no diagnóstico clínico ni predicción de lesiones. El análisis es por fotograma: no cuenta repeticiones ni confirma fases rápidas como el aterrizaje sin procesar una secuencia de vídeo. Si la postura o vista no permiten medir una regla, la cámara solicita una posición compatible en vez de inferir un error.

---

## 👥 Roles de Usuario

| Rol | Acceso |
|-----|--------|
| **Administrador** | Todo el sistema |
| **Médico / Fisioterapeuta** | Evaluaciones, atletas, alertas, reportes completos |
| **Entrenador** | Vista de sus atletas asignados, evaluaciones básicas |
| **Atleta** | Su propio perfil e historial |

---

## ☁️ AWS Services

```
S3          → Almacenamiento de imágenes, videos y reportes PDF
RDS         → Base de datos PostgreSQL
Lambda      → Procesamiento IA a escala (opcional)
SES         → Envío de emails y notificaciones
CloudWatch  → Monitoreo y logs
```

---

## 🎨 Design System

- **Color primario:** `#2563EB` (Azul PrevenIA)
- **Fondo:** `#F9FAFB` (Gris claro)
- **Fuente:** Inter (Google Fonts)
- **Responsive:** Mobile-first, breakpoints en 480px, 768px, 1024px
- **Componentes:** Tarjetas, tablas, modales, alertas, badges, gauges de riesgo

---

## 📱 Soporte Multiplataforma

✅ Desktop (1024px+) — Sidebar fija, layout en grid
✅ Tablet (768px–1024px) — Layout adaptado
✅ Móvil (< 768px) — Sidebar deslizable, columna única
✅ PWA-ready (puede agregarse manifest.json)

---

*PrevenIA — Desarrollado para la prevención inteligente de lesiones deportivas.*
# proyecto_prevenIA
# proyecto_prevenIA
