# AI_CONTEXT.md — Proyecto IRIS

> Documento vivo. Se actualiza al final de cada sesión de trabajo con IA, editando solo la Sección 9.
> Repositorio: https://github.com/Javier9472/IRIS.git

## 1. Identidad del proyecto

**Nombre:** IRIS — Inteligencia para Reconocimiento, Identificación y Seguridad
**Qué es:** Sistema de vigilancia con visión artificial. Uso personal, construido con estándar de portafolio profesional.
**Alcance v1.0 (prioridad actual):** Detección de armas de fuego, armas blancas y fuego.
**Alcance futuro (dejar la arquitectura preparada, NO construir todavía):**
- Identificación de patrones de robo
- Reporte final en PDF para entrega a servicios policiales

## 2. Stack y entorno

- Backend: Python 3.11, Django 5.2
- IA: YOLOv11s (Ultralytics) — dataset propio, migración completada en Fase 2
- Reconocimiento facial (Fase 6): InsightFace (ArcFace), embeddings precalculados, similitud coseno
- Base de datos: SQLite (solo eventos/alertas, sin sistema multiusuario)
- Frontend: HTML + CSS puro, sin frameworks, mobile-first
- Autenticación: `django.contrib.auth`, en transición a un solo Admin
- SO de desarrollo: Windows, con GPU disponible (CUDA)

## 3. Arquitectura actual — NO ROMPER

- `generar_stream()` es la función núcleo: obtiene frames (cámara local, IP, o celular vía QR) y los pasa a `detect_objects()`. Toda fuente de video nueva se integra ahí, sin tocar el motor de detección.
- Vistas modularizadas en `users/views/`: `auth_views.py`, `camera_views.py`, `detection.py`, `facial_views.py`, `test_views.py`. `urls.py` no cambia.
- Modelo `Camera`: ya soporta `intervalo_captura` y `certeza_minima` por cámara. Falta añadir `type` (local, ip, mobile_qr) y `token_auth`.
- Modelo `Alerta`: es el log de eventos (imagen + tipo + fecha por detección) — es la fuente para el futuro PDF. No almacena confianza por detección, solo el umbral `certeza_minima` a nivel de cámara.
- Pesos entrenados: `ml_models/weapons_v1/best.pt`. `detection.py` lo resuelve vía `BASE_DIR`, no por ruta hardcodeada — no depende de dónde se ejecute `manage.py`.
- Entrenamiento: `train.py` tiene `DATA_YAML`, `BASE_MODEL` y `PROJECT` anclados a `BASE_DIR` (no rutas relativas ni strings sueltos). Escribe en `training_runs/`; el mejor checkpoint se promueve a producción a mano, no automáticamente.
- Logging real en `logs/iris.log` (rotativo) + consola, vía el módulo `logging`.
- Acceso remoto (Fase 5): Tailscale Funnel, verificado desde celular por datos móviles. No tocar configuración de CORS ni estáticos salvo que se pida explícitamente.
- Pipeline facial (Fase 6): `facial_views.procesar_frame_facial()` se invoca desde dentro de `detect_objects()` (no desde `generar_stream()` directamente), envuelto en `try/except` — un fallo del pipeline facial (import, sin GPU, sin rostro) nunca interrumpe el stream de detección de armas.

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
│   └── alertas/                        # no versionado
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
    ├── models.py                       # Camera, Alerta, PersonaBuscada, AlertaFacial (Fase 6)
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
    │   └── test_model.html
    └── views/
        ├── __init__.py
        ├── auth_views.py
        ├── camera_views.py
        ├── detection.py
        ├── facial_views.py             # Fase 6
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

## 7. Decisiones ya tomadas (no volver a preguntar) 
Sin sistema multiusuario: un solo Admin.
El celular se integra como cámara vía QR + navegador (la ruta por app tipo IP Webcam sigue funcionando como fallback, no se elimina).
El acceso remoto sin misma red Wi-Fi requerirá túnel (ngrok/Cloudflare Tunnel) — la config de red y CORS debe quedar lista para eso.
Python 3.11, Django 5.2.

**Fase 6 — decisiones de diseño:**
- Modelo nuevo `PersonaBuscada` (nombre, foto de referencia, embedding precalculado), separado de `Camera` y `Alerta` — no las modifica.
- Pipeline: detección de rostro → embedding vía InsightFace (ArcFace) → comparación por similitud coseno contra embeddings de `PersonaBuscada` → umbral configurable (`similitud_minima`, análogo a `certeza_minima` de `Camera`).
- Integración: módulo `users/views/facial_views.py`, invocado desde dentro de `detect_objects()` en `detection.py` (no desde `generar_stream()` directamente), envuelto en `try/except` para que un fallo del pipeline facial nunca interrumpa el stream de detección de armas.
- Correlación arma-persona: si en el mismo frame `detect_objects()` reporta un arma y `facial_views` reporta un match sobre el umbral, se registra un evento combinado.
- Pruebas: solo 2 rostros de prueba consentidos (equipo). RENIEC/PNP no se integran técnicamente en el sistema — quedan únicamente como el caso de uso ideal narrado en el informe/portafolio.

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

**Fase 5:** ✅ Completada y probada (login, cámaras y galería verificados desde celular por datos móviles vía Tailscale Funnel).
Pendiente aparte: al terminar el uso (~1 mes desde el 22/08/26), desactivar el Funnel (`tailscale funnel off` / `tailscale down`) — sin costo ni compromiso de continuidad.

**Fase 6:** ✅ Completada por completo, cierre confirmado en esta sesión.

1. **Modelo `PersonaBuscada`** — ✅ en `users/models.py`.
2. **Pipeline facial** (`facial_views.py`: `precalcular_embedding` + `procesar_frame_facial`) — ✅ implementado, con cooldown `FACIAL_COOLDOWN_SECONDS` por persona+cámara.
3. **Enganche en el loop de frames** — ✅ confirmado en `detection.py`: `procesar_frame_facial` se llama dentro de `detect_objects()` (invocado en cada frame por `generar_stream()`), envuelto en `try/except` para que un fallo del pipeline facial no interrumpa el stream de armas.
4. **Registro de eventos** (`AlertaFacial`, con correlación a `Alerta` de arma) — ✅ en `users/models.py`.
5. **Alcance de pruebas**: solo 2 rostros de prueba consentidos (equipo real); sin integración técnica a RENIEC/PNP.
6. **Borrado de `AlertaFacial`**: únicamente manual (sin limpieza automática por TTL), individual y en lote, gestionado exclusivamente desde el panel de Django Admin. Signal `post_delete` en `models.py` borra también el archivo de imagen en disco al eliminar. **Verificado funcionando en producción local por el usuario.**

Nota técnica observada en `detection.py` (no crítica, ninguna acción tomada — queda para una futura sesión si se decide limpiar): `MODEL_PATH` y `model = YOLO(MODEL_PATH)` aparecen duplicados al inicio del módulo, cargando el modelo dos veces al importar.

Siguiente paso: ninguno pendiente para cerrar Fase 6. Próxima misión activa por definir por el usuario — candidatos según Sección 1 (alcance futuro): identificación de patrones de robo, o reporte final en PDF. No se adelanta ninguna sin instrucción explícita.