# Iris

**I**nteligencia para **R**econocimiento, **I**dentificación y **S**eguridad.

Sistema de vigilancia con visión artificial. **Iris 1.0** se enfoca en un solo
objetivo: detectar armas de fuego, armas blancas y fuego/humo en video en
vivo, y dejar registro de cada detección con imagen, cámara, hora y
confianza. Reconocimiento facial y patrones de robo quedan para versiones
futuras — el motor de detección (`users/views/detection.py`) ya está
separado como para sumarlos sin reescribir el proyecto.

## Estructura del proyecto

```
IRIS/
├── manage.py
├── requirements.txt
├── .gitignore
├── db.sqlite3                  # no versionado (ver "Puesta en marcha")
│
├── eye/                        # configuración del proyecto Django
│   ├── settings.py             #   incluye el logging (ver logs/)
│   ├── urls.py
│   ├── asgi.py / wsgi.py
│
├── users/                      # única app Django del proyecto
│   ├── models.py                #   Camera, CameraImage, Alerta
│   ├── forms.py
│   ├── urls.py
│   ├── admin.py
│   ├── migrations/
│   ├── templates/users/         #   login, home, cam, galeria, alertas...
│   ├── management/commands/
│   │   └── entrenar_modelo.py   #   `python manage.py entrenar_modelo`
│   └── views/                   #   antes un único views.py de ~830 líneas
│       ├── __init__.py          #     re-exporta todo, nada más se rompe
│       ├── auth_views.py        #     login / registro / logout
│       ├── camera_views.py      #     alta, baja y panel de cámaras
│       ├── detection.py         #     motor de visión: YOLO, streaming,
│       │                        #     procesar imagen/video de prueba
│       └── test_views.py        #     subir imagen/video y ver resultado
│
├── ml_models/                  # pesos entrenados que la app usa en vivo
│   └── weapons_v1/
│       └── best.pt             #   SÍ se versiona (pesa ~6 MB)
│
├── training_runs/              # antes 'runs/' -- salida de entrenamientos
│   └── weapons_v1/              #   gráficas, métricas, args.yaml
│       └── weights/              #   (no versionado, se regenera entrenando)
│
├── datasets/                   # datasets de Roboflow (no versionados)
│   ├── IaFinal0.v1i.yolov8/
│   └── Iatest2.v1i.yolov8/
│
├── static/                     # CSS/imágenes de la interfaz
├── media/                       # alertas capturadas + temporales (no versionado)
└── logs/
    └── iris.log                 # rotativo, 5 MB x 3 archivos (no versionado)
```

## Qué cambió en esta reorganización y por qué

| Antes | Ahora | Por qué |
|---|---|---|
| `views.py` (830 líneas: login + cámaras + YOLO mezclados) | `views/` con 4 módulos | separar autenticación, CRUD de cámaras y el motor de visión facilita tocar una cosa sin arriesgar las otras |
| `print()` sueltos | `logging` con archivo rotativo en `logs/` | quedan registrados con fecha/nivel, no se pierden al cerrar la consola |
| `DEVICE = "cpu"` fijo | detecta CUDA solo | usa la GPU si está disponible |
| `YOLO("runs/detect/train27/weights/best.pt")` (ruta relativa, dependía de desde dónde corrías `manage.py`) | `ml_models/weapons_v1/best.pt` (ruta absoluta vía `BASE_DIR`) | funciona sin importar el directorio de trabajo |
| `yolo11n.pt`, `yolov8n.pt` sueltos en la raíz | eliminados | no los usaba nada del código (ultralytics descarga `yolov8n.pt` solo cuando `entrenar_modelo` lo necesita) |
| 2 datasets de Roboflow sueltos en la raíz | `datasets/` | separa datos de código |
| `runs/` en la raíz | `training_runs/` | mismo contenido, nombre más claro junto a `ml_models/` |
| `entrenar_modelo` escribía en un `runs/` nuevo cada vez y no tocaba el modelo en producción | escribe en `training_runs/weapons_v1/` y copia el mejor checkpoint a `ml_models/weapons_v1/best.pt` al terminar | reentrenar ya no requiere mover archivos a mano |

**Nota sobre `.git`:** la carpeta `.git` de este proyecto pesa ~392 MB —
casi seguro porque los datasets y/o pesos quedaron commiteados en el
historial en algún momento. El `.gitignore` nuevo evita que esto siga
creciendo hacia adelante, pero **no achica lo que ya está en el historial**.
Si te importa el tamaño del repo para el portafolio, la opción es reescribir
el historial (por ejemplo con [`git filter-repo`](https://github.com/newren/git-filter-repo))
o, más simple, empezar un historial nuevo (`rm -rf .git && git init`) ahora
que el `.gitignore` ya está bien — perdés el historial de commits viejo, pero
para un proyecto heredado que estás relanzando puede ser lo más práctico.

## Puesta en marcha (Windows)

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Base de datos limpia (db.sqlite3 no se versiona)
python manage.py migrate
python manage.py createsuperuser

python manage.py runserver
```

Si `torch.cuda.is_available()` da `False` a pesar de tener GPU NVIDIA, ver
la nota sobre CUDA en `requirements.txt`.

## Reentrenar el modelo

```powershell
python manage.py entrenar_modelo
```

Entrena desde `datasets/IaFinal0.v1i.yolov8/`, guarda resultados en
`training_runs/weapons_v1/` y copia el mejor checkpoint a
`ml_models/weapons_v1/best.pt` (el que usa la app) automáticamente.
