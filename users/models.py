# users/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_delete
from django.dispatch import receiver
import numpy as np

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
    # Política de retención (AI_CONTEXT.md Sección 9): excluye la alerta
    # del borrado automático por TTL — evidencia con denuncia activa.
    relevante = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.tipo_deteccion} - {self.fecha_deteccion.strftime('%Y-%m-%d %H:%M:%S')}"


class PersonaBuscada(models.Model):
    nombre = models.CharField(max_length=150)
    foto_referencia = models.ImageField(upload_to='personas_buscadas/')
    # Vector ArcFace (512d, float32) precalculado desde foto_referencia
    # vía facial_views.precalcular_embedding(). No se recalcula por frame.
    embedding = models.BinaryField(null=True, blank=True)
    fecha_alta = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    def get_embedding(self):
        if not self.embedding:
            return None
        return np.frombuffer(self.embedding, dtype=np.float32)

    def __str__(self):
        return self.nombre


class AlertaFacial(models.Model):
    persona = models.ForeignKey(PersonaBuscada, on_delete=models.PROTECT, related_name='alertas_faciales')
    camara = models.ForeignKey(Camera, on_delete=models.CASCADE)
    # Nulo si no se persistió una Alerta de arma en este frame (p. ej. por
    # el cooldown de intervalo_captura), aunque sí hubo detección — en ese
    # caso confianza_arma igual queda registrada abajo.
    alerta_arma = models.ForeignKey(Alerta, on_delete=models.SET_NULL, null=True, blank=True)
    imagen = models.ImageField(upload_to='alertas_faciales/')
    confianza_facial = models.FloatField(help_text="Similitud coseno del match (0.0 - 1.0)")
    confianza_arma = models.FloatField(null=True, blank=True)
    fecha_deteccion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.persona.nombre} - {self.fecha_deteccion.strftime('%Y-%m-%d %H:%M:%S')}"


@receiver(post_delete, sender=AlertaFacial)
def eliminar_imagen_alerta_facial(sender, instance, **kwargs):
    # Django no borra el archivo del ImageField al borrar la fila (ni en
    # delete individual ni en queryset.delete() del bulk action de Admin).
    # Cubre ambos: post_delete se dispara por instancia en los dos casos.
    if instance.imagen:
        instance.imagen.delete(save=False)