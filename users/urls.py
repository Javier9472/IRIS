from django.urls import path
from . import views


urlpatterns = [
    path('login/', views.login_view, name='login_page'),
    path('register/', views.register_view, name='register'),

    path('home/', views.home_view, name='home'),

    path(
        'nueva_camara/',
        views.nueva_camara_view,
        name='nueva_camara'
    ),

    path(
        'eliminar_camara/<int:camara_id>/',
        views.eliminar_camara_view,
        name='eliminar_camara'
    ),

    path(
        'galeria/<int:camara_id>/',
        views.galeria_camara_view,
        name='galeria_camara'
    ),

    path(
        'video_feed/<int:camara_id>/',
        views.video_feed,
        name='video_feed'
    ),

    path(
        'alerta/<int:camara_id>/',
        views.obtener_alerta,
        name='obtener_alerta'
    ),

    path(
        'camara/<int:camara_id>/alertas/',
        views.ver_alertas,
        name='ver_alertas'
    ),

    path(
        'test/',
        views.test_modelo,
        name='test_modelo'
    ),
]