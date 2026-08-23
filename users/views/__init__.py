from .auth_views import register_view, login_view, logout_view
from .camera_views import (
    home_view,
    qr_code_view,
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
    "home_view", "qr_code_view", "nueva_camara_view", "eliminar_camara_view",
    "galeria_camara_view", "video_feed", "obtener_alerta", "ver_alertas",
    "test_modelo",
]