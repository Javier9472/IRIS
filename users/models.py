from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class Camera(models.Model):
    nombre = models.CharField(max_length=100)
    ip = models.CharField(max_length=255)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    intervalo_captura = models.FloatField(default=1.0, help_text="Intervalo en segundos entre capturas")
    certeza_minima = models.FloatField(default=0.5, help_text="Certeza mínima para detecciones (0.0 - 1.0)")

    def __str__(self):
        return self.nombre


class Alerta(models.Model):
    camara = models.ForeignKey(Camera, on_delete=models.CASCADE)
    tipo_deteccion = models.CharField(max_length=100)
    fecha_deteccion = models.DateTimeField(auto_now_add=True)
    imagen = models.ImageField(upload_to='alertas/')

    def __str__(self):
        return f"{self.tipo_deteccion} - {self.fecha_deteccion.strftime('%Y-%m-%d %H:%M:%S')}"