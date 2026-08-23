# AI_CONTEXT.md — Proyecto IRIS

> Documento vivo. Se actualiza al final de cada sesión de trabajo con IA, editando solo la Sección 9.
> Repositorio: https://github.com/Javier9472/IRIS.git

## 1. Identidad del proyecto

**Nombre:** IRIS — Inteligencia para Reconocimiento, Identificación y Seguridad
**Qué es:** Sistema de vigilancia con visión artificial. Uso personal, construido con estándar de portafolio profesional.
**Alcance v1.0 (base, completo):** Detección de armas de fuego, armas blancas y fuego; reconocimiento facial de personas requisitoriadas.
**Alcance activo (Fase 7):** Reporte en PDF automático por incidente — de armas, de rostros requisitoriados, o de eventos correlacionados (arma + rostro) —, almacenado en el proyecto y accesible/descargable desde un apartado nuevo tipo galería.
**Alcance futuro (dejar la arquitectura preparada, NO construir todavía):**
- Identificación de patrones de robo

## 2. Stack y entorno

- Backend: Python 3.11, Django 5.2
- IA: YOLOv11s (Ultralytics) — dataset propio, migración completada en Fase 2
- Reconocimiento facial (Fase 6): InsightFace (ArcFace), embeddings precalculados, similitud coseno
- Generación de PDF (Fase 7): **WeasyPrint** — confirmado. Requiere runtime de GTK3 instalado en Windows además de `pip install weasyprint`.
- Base de datos: SQLite (solo eventos/alertas, sin sistema multiusuario)
- Frontend: HTML + CSS puro, sin frameworks, mobile-first
- Autenticación: `django.contrib.auth`, en transición a un solo Admin
- SO de desarrollo: Windows, con GPU disponible (CUDA)

## 3. Arquitectura actual — NO ROMPER

- `generar_stream()` es la función núcleo: obtiene frames (cámara local, IP, o celular vía QR) y los pasa a `detect_objects()`. Toda fuente de video nueva se integra ahí, sin tocar el motor de detección.
- Vistas modularizadas en `users/views/`: `auth_views.py`, `camera_views.py`, `detection.py`, `facial_views.py`, `test_views.py`. `urls.py` no cambia.
- Modelo `Camera`: ya soporta `intervalo_captura` y `certeza_minima` por cámara. Falta añadir `type` (local, ip, mobile_qr) y `token_auth`.
- Modelo `Alerta`: es el log de eventos (imagen + tipo + fecha por detección) — fuente de datos para el `Incidente`/reporte PDF (Fase 7). No almacena confianza por detección, solo el umbral `certeza_minima` a nivel de cámara.
- Pesos entrenados: `ml_models/weapons_v1/best.pt`. `detection.py` lo resuelve vía `BASE_DIR`, no por ruta hardcodeada — no depende de dónde se ejecute `manage.py`.
- Entrenamiento: `train.py` tiene `DATA_YAML`, `BASE_MODEL` y `PROJECT` anclados a `BASE_DIR` (no rutas relativas ni strings sueltos). Escribe en `training_runs/`; el mejor checkpoint se promueve a producción a mano, no automáticamente.
- Logging real en `logs/iris.log` (rotativo) + consola, vía el módulo `logging`.
- Acceso remoto (Fase 5): Tailscale Funnel, verificado desde celular por datos móviles. No tocar configuración de CORS ni estáticos salvo que se pida explícitamente.
- Pipeline facial (Fase 6): `facial_views.procesar_frame_facial()` se invoca desde dentro de `detect_objects()` (no desde `generar_stream()` directamente), envuelto en `try/except` — un fallo del pipeline facial nunca interrumpe el stream de detección de armas.
- Incidentes/Reportes PDF (Fase 7): el cierre de un incidente (y su generación de PDF) se revisa aprovechando el propio loop de frames ya existente — sin dependencias nuevas tipo Celery/scheduler. No toca `generar_stream()`, `detect_objects()` ni `procesar_frame_facial()` en su forma; se engancha igual que Fase 6, como paso adicional dentro de `detect_objects()`.

## 4. Estructura de carpetas

IRIS/
├── .env                                # no versionado
├── .env.example
├── .gitignore
├── AI_CONTEXT.md
├── README.md
├── db.sqlite3                          # no versionado
├── manage.py
├── requirements.txt
├── train.py
│                                       
├── datasets/                            # no versionado
│   ├── iris.v1i.yolov11/               # dataset activo: train/, valid/, data.yaml
│   └── merge_and_clean.py
│
├── eye/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── logs/
│   └── iris.log                        # rotativo, no versionado
│
├── media/
│   ├── alertas/                         # no versionado
│   └── reportes/                        # no versionado — PDFs generados (Fase 7)
│
├── ml_models/
│   ├── weapons_v1/best.pt              # producción — sí versionado
│   ├── facial_v1/                      # embeddings de referencia (Fase 6) — no versionado
│   └── pretrained/                     # no versionado
│
├── static/
│   ├── css/style.css
│   └── img/
│
├── training_runs/
│   └── detect/iris_v1_yolo11s_960-2/   # métricas Fase 2, sin weights/
│
└── users/
    ├── __init__.py
    ├── admin.py
    ├── apps.py
    ├── forms.py
    ├── models.py                       # Camera, Alerta, PersonaBuscada, AlertaFacial (Fase 6), Incidente (Fase 7)
    ├── tests.py
    ├── urls.py
    ├── management/commands/
    │   └── limpiar_alertas_vencidas.py
    ├── migrations/
    ├── templates/users/
    │   ├── alertas.html
    │   ├── base.html
    │   ├── cam.html
    │   ├── home.html
    │   ├── login.html
    │   ├── nueva_camara.html
    │   ├── register.html
    │   ├── reportes.html               # Fase 7 — galería de reportes PDF
    │   └── test_model.html
    └── views/
        ├── __init__.py
        ├── auth_views.py
        ├── camera_views.py
        ├── detection.py
        ├── facial_views.py             # Fase 6
        ├── reportes_views.py           # Fase 7
        └── test_views.py


## 5. Convenciones de diseño (UI)

Mobile-first estricto. CSS puro, sin librerías externas.

```css
:root {
  --color-50:  #EFF6FF;
  --color-100: #DBEAFE;
  --color-200: #BEDBFF;
  --color-300: #8EC5FF;
  --color-400: #51A2FF;
  --color-500: #2B7FFF;
  --color-600: #155DFC;
  --color-700: #1447E6;
  --color-800: #193CB8;
  --color-900: #1C398E;
  --color-950: #162456;
}
```
Texto sobre fondo claro → `--color-950`. Texto sobre fondo oscuro → `#FFFFFF` o `--color-50`.

## 6. Roadmap y estado
Fase	Descripción	Estado
1	Reorganización de carpetas/estructura (views modulares, logging, rutas de pesos)	✅ Completada
2	Reentrenar el modelo (dataset propio, limpiar clases sucias '0', '1', 'crash', mayor resolución, YOLOv11s)	✅ Completada
3	Borrar y organizar repositorio de código inútil o restos antiguos	✅ Completada
4	Refactor UI/CSS mobile-first + autenticación de Admin único	✅ Completada
5	Acceso remoto al dashboard vía celular por QR (el celular es solo visor del stream ya procesado, no captura video) usando Tailscale Funnel	✅ Completada
6	Reconocimiento facial de personas buscadas (modelo PersonaBuscada) + correlación con detección de armas + borrado manual de AlertaFacial vía Django Admin	✅ Completada
7	Reporte PDF automático por incidente (armas / rostros requisitoriados / eventos correlacionados) almacenado en el proyecto, con galería de descarga	🔲 Diseño cerrado — lista para implementación

## 7. Decisiones ya tomadas (no volver a preguntar) 
Sin sistema multiusuario: un solo Admin.
El celular se integra como cámara vía QR + navegador (la ruta por app tipo IP Webcam sigue funcionando como fallback, no se elimina).
El acceso remoto sin misma red Wi-Fi requerirá túnel (ngrok/Cloudflare Tunnel) — la config de red y CORS debe quedar lista para eso.
Python 3.11, Django 5.2.

**Fase 6 — decisiones de diseño:**
- Modelo `PersonaBuscada` (nombre, foto de referencia, embedding precalculado), separado de `Camera` y `Alerta` — no las modifica.
- Pipeline: detección de rostro → embedding vía InsightFace (ArcFace) → comparación por similitud coseno contra embeddings de `PersonaBuscada` → umbral configurable (`similitud_minima`, análogo a `certeza_minima` de `Camera`).
- Integración: módulo `users/views/facial_views.py`, invocado desde dentro de `detect_objects()` en `detection.py` (no desde `generar_stream()` directamente), envuelto en `try/except`.
- Correlación arma-persona: si en el mismo frame `detect_objects()` reporta un arma y `facial_views` reporta un match sobre el umbral, se registra un evento combinado.
- Pruebas: solo 2 rostros de prueba consentidos (equipo). RENIEC/PNP no se integran técnicamente en el sistema — quedan únicamente como el caso de uso ideal narrado en el informe/portafolio.

**Fase 7 — decisiones de diseño (todas confirmadas):**
- **Generación automática**, no manual: el sistema arma y guarda el PDF solo, sin que el usuario tenga que pedirlo desde la galería.
- **Un PDF por incidente/momento continuo**, no uno por cada `Alerta`/`AlertaFacial` individual: si la misma amenaza sigue detectándose de forma continua en una cámara, todas esas detecciones se agrupan en un solo reporte.
- **Modelo nuevo `Incidente`** en `users/models.py`: `camara` (FK), `tipo` (arma / rostro / correlacionado — se recalcula según qué eventos contiene), `hora_inicio`, `hora_fin` (nulo mientras sigue abierto), `pdf` (FileField, se llena al cerrarse), relación a las `Alerta` y `AlertaFacial` ocurridas dentro de la ventana. No modifica `Alerta` ni `AlertaFacial` existentes.
- **Ventana de inactividad: 30 segundos** (`INCIDENTE_TIMEOUT_SECONDS = 30`). Mientras sigan llegando detecciones (arma y/o rostro) en esa cámara dentro de esos 30s, se suman al mismo `Incidente` abierto; pasado ese tiempo sin nuevas detecciones, se cierra.
- **Revisión del cierre**: aprovechando que `detect_objects()` ya corre en cada frame del stream, ahí mismo se revisa si hay incidentes abiertos de esa cámara que ya superaron los 30s; si sí, se cierran y se dispara la generación del PDF con las `Alerta`/`AlertaFacial` acumuladas. Caveat conocido y aceptado: si el stream se corta antes de cumplirse el timeout, el incidente queda "abierto" hasta que vuelvan a llegar frames de esa cámara.
- **Biblioteca de PDF: WeasyPrint** — reutiliza los templates HTML y la paleta de colores de la Sección 5. Requiere runtime de GTK3 instalado en Windows.
- **Nuevo módulo** `users/views/reportes_views.py` + template `reportes.html`: galería con lista de `Incidente`s cerrados (badge de tipo, fecha/hora, botón de descarga del PDF), mismo patrón mobile-first de `alertas.html`.
- **Almacenamiento**: `media/reportes/`, no versionado (mismo criterio que `media/alertas/`).

## 8. Reglas de trabajo para la IA

- Actúa como Ingeniero de Software Senior y Arquitecto de Sistemas.
- Regla de tokens (cero yapping): responde ÚNICAMENTE con el código modificado o solicitado. Cero saludos, cero explicación fuera del código. Usa comentarios dentro del código solo para lo crucial.
- Excepción única: al final de tu respuesta, agrega una línea de changelog con este formato exacto:
  `CHANGELOG: <archivo(s)> — <qué cambió, en una frase>`
- No toques la Sección 3 (arquitectura núcleo) sin que se te pida explícitamente.
- Trabaja solo sobre la misión activa descrita en la Sección 9. No adelantes fases futuras.
- Pide los archivos que necesitas.

## 9. Estado actual / Misión activa
Última actualización: 23/08/26

Fase 5: ✅ Completada y probada (celular como visor vía Tailscale Funnel). Pendiente aparte: desactivar el Funnel (`tailscale funnel off` / `tailscale down`) al terminar el uso (~1 mes desde el 22/08/26).

Fase 6: ✅ Completada y cerrada. Reconocimiento facial completo, enganche confirmado en `detection.py` — verificado en producción local.

**Fase 7 (MISIÓN ACTIVA): Reporte PDF automático por incidente + galería de descarga**

Diseño completo y confirmado (ver Sección 7): modelo `Incidente`, ventana de 30s de inactividad para cerrar el incidente y disparar el PDF, WeasyPrint como motor de generación, galería nueva vía `reportes_views.py` + `reportes.html`.

**Todavía no se escribió código de esta fase.** Siguiente paso: implementación.

Archivos que se van a necesitar para arrancar (pedir al usuario antes de escribir código, por la regla de la Sección 8):
- `users/models.py` (para agregar `Incidente` sin romper `Camera`, `Alerta`, `PersonaBuscada`, `AlertaFacial`)
- `users/views/detection.py` (para enganchar la revisión de cierre de incidentes — ya se tiene la versión actual de la sesión pasada, pero conviene reconfirmar si no ha cambiado)
- `eye/settings.py` (confirmar `MEDIA_ROOT`, `INSTALLED_APPS`, y dónde agregar la config de WeasyPrint si aplica)
- `requirements.txt` (para agregar `weasyprint`)
- `users/urls.py` y `users/templates/users/base.html` (para saber cómo están armadas las rutas y el menú de navegación actuales, y agregar el link a la nueva galería de reportes de forma consistente)