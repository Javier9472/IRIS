# Iris

**I**nteligencia para **R**econocimiento, **I**dentificación y **S**eguridad.

Sistema de vigilancia con visión artificial, de uso personal, construido con estándar de portafolio profesional. **Iris 1.0** se enfoca en un solo objetivo: detectar armas de fuego, armas blancas y fuego en video en vivo, dejando registro de cada detección (imagen, cámara, tipo y hora). Reconocimiento facial, identificación de patrones de robo y reporte PDF quedan para versiones futuras — el motor de detección (`users/views/detection.py`) ya está separado del resto de la app para poder sumarlos sin reescribir el proyecto.

## Estructura del proyecto

IRIS/
├── .gitignore
├── AI_CONTEXT.md
├── README.md
├── db.sqlite3 # no versionado
├── manage.py
├── requirements.txt
├── train.py # entrenamiento (ver "Reentrenar el modelo")
├── yolo26n.pt # origen sin confirmar — ver AI_CONTEXT.md Sección 9
│
├── datasets/
│ ├── iris.v1i.yolov11/ # dataset activo (train/, valid/, data.yaml)
│ └── merge_and_clean.py # unifica y limpia el dataset antes de entrenar
│
├── eye/ # configuración del proyecto Django
│ ├── settings.py # incluye logging (ver logs/)
│ ├── urls.py
│ └── asgi.py / wsgi.py
│
├── logs/
│ └── iris.log # rotativo (5 MB x 3), no versionado
│
├── media/ # capturas de alertas + temporales, no versionado
│
├── ml_models/ # ver "Arquitectura de modelos"
│ ├── weapons_v1/best.pt # modelo en producción — SÍ versionado
│ └── pretrained/yolo11s.pt # checkpoint base para entrenar — no versionado
│
├── static/
│ ├── css/style.css
│ └── img/
│
├── training_runs/ # ver "Arquitectura de modelos"
│ └── detect/iris_v1_yolo11s_960-2/ # métricas del entrenamiento vigente (sin pesos)
│
└── users/ # única app Django
├── models.py # Camera, Alerta
├── forms.py
├── urls.py
├── admin.py
├── migrations/
├── templates/users/ # login, register, home, cam, alertas, test_model
└── views/ # antes un único views.py de ~830 líneas
├── init.py # re-exporta todo, nada se rompe fuera de aquí
├── auth_views.py # login / registro / logout
├── camera_views.py # alta, baja y panel de cámaras
├── detection.py # motor de visión: YOLO, streaming, pruebas
└── test_views.py # subir imagen/video y ver resultado


## Arquitectura de modelos

Tres carpetas relacionadas con Machine Learning, cada una con un rol distinto:

- **`ml_models/weapons_v1/best.pt`** — el modelo que la app carga en runtime (`detection.py`). Es el único peso versionado en git a propósito: así el proyecto funciona recién clonado, sin depender de que exista una carpeta de entrenamiento local. No se sobreescribe automáticamente al reentrenar — hay que copiarlo a mano (ver más abajo).
- **`training_runs/`** — salida de cada corrida de `train.py`. Se versionan las métricas de cada run (`results.csv`, curvas, `args.yaml`); los pesos (`weights/`) quedan fuera de git a propósito, porque se regeneran entrenando y pesan varios MB por corrida.
- **`ml_models/pretrained/`** — checkpoints base (ej. `yolo11s.pt`) que `train.py` usa como punto de partida. No se versionan; si no están, Ultralytics los descarga solos la primera vez.

`runs/` (carpeta default de Ultralytics cuando no se ancla `project` a una ruta absoluta) no debería volver a aparecer: `train.py` fija `DATA_YAML`, `BASE_MODEL` y `PROJECT` con rutas absolutas vía `BASE_DIR`, así que el resultado no depende de desde dónde se ejecute el script.

## Puesta en marcha (Windows)

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser

python manage.py runserver
```

Si `torch.cuda.is_available()` da `False` a pesar de tener GPU NVIDIA, ver la nota sobre CUDA en `requirements.txt`. Para probar el modelo con un video (`/test/`), hace falta `ffmpeg` instalado y en el PATH.

## Reentrenar el modelo

```powershell
python train.py
```

Entrena YOLOv11s desde `datasets/iris.v1i.yolov11/data.yaml` y guarda resultados en `training_runs/<nombre_de_run>/`. **No** copia el resultado a producción automáticamente — hay que promoverlo a mano una vez validado:

```powershell
Copy-Item "training_runs\<nombre_de_run>\weights\best.pt" "ml_models\weapons_v1\best.pt" -Force
```

## Nota sobre el tamaño de `.git`

La carpeta `.git` de este proyecto es considerablemente más pesada de lo que el código fuente explicaría — probablemente porque datasets y/o pesos quedaron commiteados en el historial antes de que existiera el `.gitignore` actual. Las reglas vigentes evitan que esto siga creciendo, pero no reducen lo que ya está en el historial. Si el tamaño del repo importa para el portafolio, la opción es reescribir el historial (p. ej. [`git filter-repo`](https://github.com/newren/git-filter-repo)) o empezar un historial nuevo (`rm -rf .git && git init`) ahora que el `.gitignore` está al día.

## Roadmap

Ver `AI_CONTEXT.md` — Sección 6.