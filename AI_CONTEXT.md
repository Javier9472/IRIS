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
- IA: YOLO (Ultralytics) — migrando a YOLOv8s/m con dataset propio
- Base de datos: SQLite (solo eventos/alertas, sin sistema multiusuario)
- Frontend: HTML + CSS puro, sin frameworks, mobile-first
- Autenticación: `django.contrib.auth`, en transición a un solo Admin
- SO de desarrollo: Windows, con GPU disponible (CUDA)


## 3. Arquitectura actual — NO ROMPER

- `generar_stream()` es la función núcleo: obtiene frames (cámara local, IP, o próximamente celular) y los pasa a `detect_objects()`. Toda fuente de video nueva se integra ahí, sin tocar el motor de detección.
- Vistas modularizadas en `users/views/`: `auth_views.py`, `camera_views.py`, `detection.py`, `test_views.py`. `urls.py` no cambia.
- Modelo `Camera`: ya soporta `intervalo_captura` y `certeza_minima` por cámara. Falta añadir `type` (local, ip, mobile_qr) y `token_auth`.
- Modelo `Alerta`: es el log de eventos (imagen + tipo + fecha por detección) — es la fuente para el futuro PDF.
- Pesos entrenados: `ml_models/weapons_v1/best.pt` (ruta absoluta).
- Logging real en `logs/iris.log` (rotativo) + consola, vía el módulo `logging`.
- No tocar configuración de CORS, estáticos o red: serán necesarios cuando el sistema se exponga a internet (túnel tipo ngrok / Cloudflare Tunnel).

## 4. Estructura de carpetas

```
IRIS/
├── datasets/
├   ├── IaFinal0.v1i.yolov8 (guarda dentro test, train, valid y data.yaml)
│   ├── Iatest2.v1i.yolov8 (guarda dentro test, train, valid y data.yaml)
├── eye/                  # Config Django
├── logs/
├── media/
├── ml_models/
├── static/css/style.css
├── training_runs/
├── users/
│   ├── templates/users/
│   ├── views/
│   ├── models.py
│   └── urls.py
├── db.sqlite3
├── manage.py
└── requirements.txt
```

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
| 2 | Reentrenar el modelo (dataset propio, limpiar clases sucias `'0'`, `'1'`, `'crash'`, mayor resolución, YOLOv8s/m) | 🔵 Prioridad actual |
| 3 | Refactor UI/CSS mobile-first + autenticación de Admin único | ⏳ Pendiente |
| 4 | Cámara vía celular por QR (token de un solo uso, `getUserMedia`, envío de frames) + explorar acceso remoto por internet sin estar en la misma red Wi-Fi | ⏳ Pendiente |

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

## 9. Estado actual / Misión activa

**Última actualización:** 18/08/26
**Misión de hoy:** Fase 3
**Archivos relevantes para esta misión:** 
**Changelog de la sesión anterior:**  CHANGELOG: train.py — imgsz subido de 640 a 960 (aumento de resolución) y batch ajustado a 8 por el mayor consumo de VRAM.
