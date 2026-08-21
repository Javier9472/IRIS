# AI_CONTEXT.md — Proyecto IRIS

> Documento vivo. Se actualiza al final de cada sesión de trabajo con IA, editando solo la Sección 9.
> Repositorio: https://github.com/Javier9472/IRIS.git

## 1. Identidad del proyecto

**Nombre:** IRIS — Inteligencia para Reconocimiento, Identificación y Seguridad
**Qué es:** Sistema de vigilancia con visión artificial. Uso personal, construido con estándar de portafolio profesional.
**Alcance v1.0 (prioridad actual):** Detección de armas de fuego, armas blancas y fuego.
**Alcance futuro (dejar la arquitectura preparada, NO construir todavía):**
- Reconocimiento facial (búsqueda y captura)
- Identificación de patrones de robo
- Reporte final en PDF para entrega a servicios policiales

## 2. Stack y entorno

- Backend: Python 3.11, Django 5.2
- IA: YOLOv11s (Ultralytics) — dataset propio, migración completada en Fase 2
- Base de datos: SQLite (solo eventos/alertas, sin sistema multiusuario)
- Frontend: HTML + CSS puro, sin frameworks, mobile-first
- Autenticación: `django.contrib.auth`, en transición a un solo Admin
- SO de desarrollo: Windows, con GPU disponible (CUDA)

## 3. Arquitectura actual — NO ROMPER

- `generar_stream()` es la función núcleo: obtiene frames (cámara local, IP, o próximamente celular) y los pasa a `detect_objects()`. Toda fuente de video nueva se integra ahí, sin tocar el motor de detección.
- Vistas modularizadas en `users/views/`: `auth_views.py`, `camera_views.py`, `detection.py`, `test_views.py`. `urls.py` no cambia.
- Modelo `Camera`: ya soporta `intervalo_captura` y `certeza_minima` por cámara. Falta añadir `type` (local, ip, mobile_qr) y `token_auth`.
- Modelo `Alerta`: es el log de eventos (imagen + tipo + fecha por detección) — es la fuente para el futuro PDF. No almacena confianza por detección, solo el umbral `certeza_minima` a nivel de cámara.
- Pesos entrenados: `ml_models/weapons_v1/best.pt`. `detection.py` lo resuelve vía `BASE_DIR`, no por ruta hardcodeada — no depende de dónde se ejecute `manage.py`.
- Entrenamiento: `train.py` tiene `DATA_YAML`, `BASE_MODEL` y `PROJECT` anclados a `BASE_DIR` (no rutas relativas ni strings sueltos). Escribe en `training_runs/`; el mejor checkpoint se promueve a producción a mano, no automáticamente.
- Logging real en `logs/iris.log` (rotativo) + consola, vía el módulo `logging`.
- No tocar configuración de CORS, estáticos o red: serán necesarios cuando el sistema se exponga a internet (túnel tipo ngrok / Cloudflare Tunnel).

## 4. Estructura de carpetas

IRIS/
├── .gitignore
├── AI_CONTEXT.md
├── README.md
├── db.sqlite3 # no versionado
├── manage.py
├── requirements.txt
├── train.py
├── yolo26n.pt # origen sin confirmar (Sección 9)
│
├── datasets/
│ ├── iris.v1i.yolov11/ # dataset activo: train/, valid/, data.yaml
│ └── merge_and_clean.py
│
├── eye/
│ ├── init.py
│ ├── settings.py
│ ├── urls.py
│ ├── asgi.py
│ └── wsgi.py
│
├── logs/
│ └── iris.log # rotativo, no versionado
│
├── media/ # no versionado
│
├── ml_models/
│ ├── weapons_v1/best.pt # producción — SÍ versionado
│ └── pretrained/yolo11s.pt # checkpoint base — no versionado
│
├── static/
│ ├── css/style.css
│ └── img/
│
├── training_runs/
│ └── detect/iris_v1_yolo11s_960-2/ # métricas Fase 2, sin weights/
│
└── users/
├── init.py
├── admin.py
├── apps.py
├── forms.py
├── models.py # Camera, Alerta
├── tests.py
├── urls.py
├── management/commands/ # vacío — entrenar_modelo.py eliminado
├── migrations/
├── templates/users/
│ ├── alertas.html
│ ├── cam.html
│ ├── home.html
│ ├── login.html
│ ├── nueva_camara.html
│ ├── register.html
│ └── test_model.html
└── views/
├── init.py
├── auth_views.py
├── camera_views.py
├── detection.py
└── test_views.py


## 5. Convenciones de diseño (UI)

Mobile-first estricto. CSS puro, sin librerías externas.

```css
:root {
  --color-50: #EFF6FF;
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

| Fase | Descripción | Estado |
|---|---|---|
| 1 | Reorganización de carpetas/estructura (views modulares, logging, rutas de pesos) | ✅ Completada |
| 2 | Reentrenar el modelo (dataset propio, limpiar clases sucias `'0'`, `'1'`, `'crash'`, mayor resolución, YOLOv11s) | ✅ Completada |
| 3 | Borrar y organizar repositorio de código inútil o restos antiguos | ✅ Completada |
| 4 | Refactor UI/CSS mobile-first + autenticación de Admin único | ⏳ Pendiente |
| 5 | Cámara vía celular por QR (token de un solo uso, `getUserMedia`, envío de frames) + explorar acceso remoto por internet sin estar en la misma red Wi-Fi | ⏳ Pendiente |

## 7. Decisiones ya tomadas (no volver a preguntar)

- Sin sistema multiusuario: un solo Admin.
- El celular se integra como cámara vía **QR + navegador** (la ruta por app tipo IP Webcam sigue funcionando como fallback, no se elimina).
- El acceso remoto sin misma red Wi-Fi requerirá túnel (ngrok/Cloudflare Tunnel) — la config de red y CORS debe quedar lista para eso.
- Python 3.11, Django 5.2.

## 8. Reglas de trabajo para la IA

- Actúa como Ingeniero de Software Senior y Arquitecto de Sistemas.
- Regla de tokens (cero yapping): responde ÚNICAMENTE con el código modificado o solicitado. Cero saludos, cero explicación fuera del código. Usa comentarios dentro del código solo para lo crucial.
- Excepción única: al final de tu respuesta, agrega una línea de changelog con este formato exacto:
  `CHANGELOG: <archivo(s)> — <qué cambió, en una frase>`
- No toques la Sección 3 (arquitectura núcleo) sin que se te pida explícitamente.
- Trabaja solo sobre la misión activa descrita en la Sección 9. No adelantes fases futuras.
- Pide los archivos que necesitas.

## 9. Estado actual / Misión activa

**Última actualización:** 20/08/26
**Misión de hoy:** Fase 3 — cerrada

**Pendiente: **

CHANGELOG: static/css/style.css — reescrito completo mobile-first (base = mobile, min-width breakpoints) con la paleta --color-50..950 de la Sección 5 en lugar de amarillo/rojo/skyblue; eliminado bloque .login-div duplicado y @import de fuente redundante. | users/templates/users/base.html — nuevo template base (nav + bloques title/content) que elimina el boilerplate repetido. | home.html, cam.html, nueva_camara.html, alertas.html, test_model.html — migrados a extends de base.html, lang="es" y títulos reales vía base; alertas.html pasa a usar sus propias clases .alertas-div/.galeria/.alerta en vez de las de home; test_model.html ahora muestra {{ error }}; cam.html saca el <title> inválido del body. | login.html — quitado el panel de registro promocionado (Admin único) y ahora renderiza los messages de error del login, que antes no se mostraban. | register.html — layout de tarjeta única, sigue accesible solo para el bootstrap del Admin. | users/views/auth_views.py — register_view cierra el registro público una vez que existe un usuario.