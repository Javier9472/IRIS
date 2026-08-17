from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

from users.views import login_view


urlpatterns = [
    path('admin/', admin.site.urls),

    # LOGIN PRINCIPAL
    path('', login_view, name='login'),

    # Resto de la aplicación
    path('users/', include('users.urls')),
]


urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)