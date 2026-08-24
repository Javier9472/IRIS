# users/admin.py
from django.contrib import admin, messages

from .models import PersonaBuscada, AlertaFacial, Incidente
from .views import facial_views


@admin.register(PersonaBuscada)
class PersonaBuscadaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo', 'fecha_alta', 'tiene_embedding')
    list_filter = ('activo',)
    exclude = ('embedding',)
    actions = ['calcular_embedding']

    @admin.display(boolean=True, description='Embedding calculado')
    def tiene_embedding(self, obj):
        return obj.embedding is not None

    @admin.action(description='Calcular embedding facial (ArcFace) de las seleccionadas')
    def calcular_embedding(self, request, queryset):
        ok = 0
        for persona in queryset:
            try:
                facial_views.precalcular_embedding(persona)
                ok += 1
            except Exception as e:
                self.message_user(request, f"{persona.nombre}: {e}", level=messages.ERROR)
        if ok:
            self.message_user(request, f"Embedding calculado para {ok} persona(s).")


@admin.register(AlertaFacial)
class AlertaFacialAdmin(admin.ModelAdmin):
    list_display = ('persona', 'camara', 'confianza_facial', 'confianza_arma', 'fecha_deteccion')
    list_filter = ('persona', 'camara')
    readonly_fields = [f.name for f in AlertaFacial._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(Incidente)
class IncidenteAdmin(admin.ModelAdmin):
    list_display = ('id', 'camara', 'tipo', 'hora_inicio', 'hora_fin', 'tiene_pdf')
    list_filter = ('tipo', 'camara')
    ordering = ('-hora_inicio',)
    readonly_fields = [f.name for f in Incidente._meta.fields]

    @admin.display(boolean=True, description='PDF generado')
    def tiene_pdf(self, obj):
        return bool(obj.pdf)

    def has_add_permission(self, request):
        return False