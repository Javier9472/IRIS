"""
Antes 'views.py' era un solo archivo de ~830 líneas mezclando
autenticación, CRUD de cámaras y el motor de visión (YOLO).

Ahora está separado en:

- auth_views.py    -> login / registro / logout
- camera_views.py  -> alta, baja y panel de cámaras
- detection.py     -> motor de visión (modelo YOLO, streaming, procesamiento)
- test_views.py    -> vista de prueba del modelo con imagen/video subido

Este __init__.py re-exporta todo para que el resto del proyecto
(users/urls.py, eye/urls.py) no tenga que cambiar ni una línea:
`from . import views` seguido de `views.login_view(...)`, o
`from users.views import login_view`, siguen funcionando exactamente
igual que antes de este cambio.
"""

from .auth_views import register_view, login_view, logout_view
from .camera_views import (
    home_view,
    nueva_camara_view,
    eliminar_camara_view,
    galeria_camara_view,
    video_feed,
    obtener_alerta,
    ver_alertas,
)
from .test_views import test_modelo

__all__ = [
    "register_view", "login_view", "logout_view",
    "home_view", "nueva_camara_view", "eliminar_camara_view",
    "galeria_camara_view", "video_feed", "obtener_alerta", "ver_alertas",
    "test_modelo",
]
