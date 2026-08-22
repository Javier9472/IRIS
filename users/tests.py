"""
Tests automatizados — Fase 4, ítem 6 (ver AI_CONTEXT.md, Sección 9).

Cobertura:
- Auth: acceso protegido redirige sin sesión, registro se cierra con Admin
  único, rate limiting de login.
- CRUD de Camera: aislado por usuario (creación, edición, borrado, acceso a
  galería/stream/alertas de cámaras ajenas → 404).
- Validación de modelo: valores por defecto, __str__, y comportamiento de
  CameraForm/CameraSettingsForm.

NOTA CRUCIAL: en auth_views.py los decoradores usan
`login_required(login_url='login')` y `register_view` hace `redirect('login')`,
pero el único name registrado en users/urls.py es 'login_page' (LogoutView sí
usa 'login_page' correctamente). Si 'login' no está definido en el URLconf
raíz (eye/urls.py), los tests de esta clase que dependen de esos redirects
fallarán con NoReverseMatch en vez de validar el redirect — no es un error de
los tests, es la señal de que ese link está roto.
"""

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import CameraForm, CameraSettingsForm
from .models import Alerta, Camera


class RegistroYRedireccionesTests(TestCase):

    PROTECTED_VIEWS = [
        ('home', {}),
        ('nueva_camara', {}),
        ('eliminar_camara', {'camara_id': 999999}),
        ('galeria_camara', {'camara_id': 999999}),
        ('video_feed', {'camara_id': 999999}),
        ('obtener_alerta', {'camara_id': 999999}),
        ('ver_alertas', {'camara_id': 999999}),
    ]

    def setUp(self):
        cache.clear()

    def test_vistas_protegidas_redirigen_sin_sesion(self):
        for url_name, kwargs in self.PROTECTED_VIEWS:
            with self.subTest(vista=url_name):
                url = reverse(url_name, kwargs=kwargs)
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f"{reverse('login_page')}?next={url}",
                    fetch_redirect_response=False,
                )

    def test_registro_disponible_sin_admin(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_registro_crea_admin_unico(self):
        response = self.client.post(reverse('register'), {
            'username': 'admin',
            'email': 'admin@iris.local',
            'password1': 'contraseña-segura-123',
            'password2': 'contraseña-segura-123',
        })
        self.assertTrue(User.objects.filter(username='admin').exists())
        self.assertRedirects(response, reverse('login_page'), fetch_redirect_response=False)

    def test_registro_cerrado_si_ya_existe_admin(self):
        User.objects.create_user(username='admin', password='contraseña-segura-123')
        response = self.client.get(reverse('register'))
        self.assertRedirects(response, reverse('login_page'), fetch_redirect_response=False)

    def test_usuario_autenticado_no_reingresa_a_login(self):
        User.objects.create_user(username='admin', password='contraseña-segura-123')
        self.client.login(username='admin', password='contraseña-segura-123')
        response = self.client.get(reverse('login_page'))
        self.assertRedirects(response, reverse('home'))

    def test_usuario_autenticado_no_reingresa_a_register(self):
        User.objects.create_user(username='admin', password='contraseña-segura-123')
        self.client.login(username='admin', password='contraseña-segura-123')
        response = self.client.get(reverse('register'))
        self.assertRedirects(response, reverse('home'))


class LoginTests(TestCase):

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='admin', password='contraseña-segura-123')

    def test_login_correcto_redirige_a_home(self):
        response = self.client.post(reverse('login_page'), {
            'username': 'admin',
            'password': 'contraseña-segura-123',
        })
        self.assertRedirects(response, reverse('home'))

    def test_login_credenciales_invalidas_no_autentica(self):
        response = self.client.post(reverse('login_page'), {
            'username': 'admin',
            'password': 'incorrecta',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)


@override_settings(
    LOGIN_RATE_LIMIT_ATTEMPTS=3,
    LOGIN_RATE_LIMIT_WINDOW=60,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class LoginRateLimitTests(TestCase):

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='admin', password='contraseña-segura-123')

    def test_bloquea_tras_maximo_de_intentos_fallidos(self):
        for _ in range(3):
            self.client.post(reverse('login_page'), {
                'username': 'admin',
                'password': 'incorrecta',
            })

        response = self.client.post(reverse('login_page'), {
            'username': 'admin',
            'password': 'contraseña-segura-123',
        })

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)


class CamaraCRUDTests(TestCase):

    def setUp(self):
        cache.clear()
        self.owner = User.objects.create_user(username='dueño', password='contraseña-segura-123')
        self.otro = User.objects.create_user(username='otro', password='contraseña-segura-123')

        self.camara = Camera.objects.create(
            nombre='Patio',
            ip='192.168.1.50',
            usuario=self.owner,
        )

        self.client.login(username='dueño', password='contraseña-segura-123')

    def test_home_lista_solo_camaras_propias(self):
        Camera.objects.create(nombre='Ajena', ip='10.0.0.5', usuario=self.otro)

        response = self.client.get(reverse('home'))

        self.assertEqual(list(response.context['camaras']), [self.camara])

    def test_crear_camara_asigna_usuario_autenticado(self):
        response = self.client.post(reverse('nueva_camara'), {
            'nombre': 'Garage',
            'ip': '192.168.1.60',
            'intervalo_captura': 1.0,
            'certeza_minima': 0.6,
        })

        self.assertRedirects(response, reverse('home'))
        camara = Camera.objects.get(nombre='Garage')
        self.assertEqual(camara.usuario, self.owner)

    def test_actualizar_configuracion_camara_propia(self):
        response = self.client.post(reverse('galeria_camara', kwargs={'camara_id': self.camara.id}), {
            'nombre': 'Patio actualizado',
            'ip': self.camara.ip,
            'intervalo_captura': 2.0,
            'certeza_minima': 0.8,
        })

        self.assertRedirects(response, reverse('galeria_camara', kwargs={'camara_id': self.camara.id}))
        self.camara.refresh_from_db()
        self.assertEqual(self.camara.nombre, 'Patio actualizado')
        self.assertEqual(self.camara.intervalo_captura, 2.0)

    def test_eliminar_camara_propia(self):
        response = self.client.get(reverse('eliminar_camara', kwargs={'camara_id': self.camara.id}))

        self.assertRedirects(response, reverse('home'))
        self.assertFalse(Camera.objects.filter(id=self.camara.id).exists())

    def test_eliminar_camara_ajena_devuelve_404(self):
        ajena = Camera.objects.create(nombre='Ajena', ip='10.0.0.5', usuario=self.otro)

        response = self.client.get(reverse('eliminar_camara', kwargs={'camara_id': ajena.id}))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Camera.objects.filter(id=ajena.id).exists())

    def test_galeria_camara_ajena_devuelve_404(self):
        ajena = Camera.objects.create(nombre='Ajena', ip='10.0.0.5', usuario=self.otro)

        response = self.client.get(reverse('galeria_camara', kwargs={'camara_id': ajena.id}))

        self.assertEqual(response.status_code, 404)

    def test_video_feed_propio_devuelve_stream(self):
        # No se consume streaming_content a propósito: iterarlo dispararía
        # generar_stream() intentando abrir la cámara real.
        response = self.client.get(reverse('video_feed', kwargs={'camara_id': self.camara.id}))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Type'].startswith('multipart/x-mixed-replace'))

    def test_video_feed_ajeno_devuelve_404(self):
        ajena = Camera.objects.create(nombre='Ajena', ip='10.0.0.5', usuario=self.otro)

        response = self.client.get(reverse('video_feed', kwargs={'camara_id': ajena.id}))

        self.assertEqual(response.status_code, 404)

    def test_obtener_alerta_devuelve_ultima_deteccion(self):
        Alerta.objects.create(
            camara=self.camara,
            tipo_deteccion='arma_fuego',
            imagen='alertas/dummy.jpg',
        )

        response = self.client.get(reverse('obtener_alerta', kwargs={'camara_id': self.camara.id}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'alerta': 'arma_fuego'})

    def test_obtener_alerta_sin_detecciones(self):
        response = self.client.get(reverse('obtener_alerta', kwargs={'camara_id': self.camara.id}))

        self.assertEqual(response.json(), {'alerta': 'Sin detecciones'})

    def test_obtener_alerta_ajena_devuelve_404(self):
        ajena = Camera.objects.create(nombre='Ajena', ip='10.0.0.5', usuario=self.otro)

        response = self.client.get(reverse('obtener_alerta', kwargs={'camara_id': ajena.id}))

        self.assertEqual(response.status_code, 404)

    def test_ver_alertas_propia_ok(self):
        Alerta.objects.create(
            camara=self.camara,
            tipo_deteccion='fuego',
            imagen='alertas/dummy.jpg',
        )

        response = self.client.get(reverse('ver_alertas', kwargs={'camara_id': self.camara.id}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['alertas']), 1)

    def test_ver_alertas_ajena_devuelve_404(self):
        ajena = Camera.objects.create(nombre='Ajena', ip='10.0.0.5', usuario=self.otro)

        response = self.client.get(reverse('ver_alertas', kwargs={'camara_id': ajena.id}))

        self.assertEqual(response.status_code, 404)


class ModeloYFormulariosTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='dueño', password='contraseña-segura-123')

    def test_valores_por_defecto_de_camera(self):
        camara = Camera.objects.create(nombre='Patio', ip='192.168.1.50', usuario=self.user)

        self.assertEqual(camara.intervalo_captura, 1.0)
        self.assertEqual(camara.certeza_minima, 0.5)

    def test_str_de_camera(self):
        camara = Camera.objects.create(nombre='Patio', ip='192.168.1.50', usuario=self.user)
        self.assertEqual(str(camara), 'Patio')

    def test_str_de_alerta_incluye_tipo_y_fecha(self):
        camara = Camera.objects.create(nombre='Patio', ip='192.168.1.50', usuario=self.user)
        alerta = Alerta.objects.create(camara=camara, tipo_deteccion='cuchillo', imagen='alertas/dummy.jpg')

        self.assertTrue(str(alerta).startswith('cuchillo -'))

    def test_camera_form_valido_con_datos_completos(self):
        form = CameraForm(data={
            'nombre': 'Patio',
            'ip': '192.168.1.50',
            'intervalo_captura': 1.5,
            'certeza_minima': 0.7,
        })
        self.assertTrue(form.is_valid())

    def test_camera_form_invalido_sin_nombre_ni_ip(self):
        form = CameraForm(data={
            'intervalo_captura': 1.0,
            'certeza_minima': 0.5,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('nombre', form.errors)
        self.assertIn('ip', form.errors)

    def test_camera_settings_form_valido(self):
        form = CameraSettingsForm(data={
            'nombre': 'Patio actualizado',
            'ip': '192.168.1.51',
            'intervalo_captura': 2.0,
            'certeza_minima': 0.9,
        })
        self.assertTrue(form.is_valid())

    def test_certeza_minima_fuera_de_rango_no_es_rechazada(self):
        """
        GAP conocido: Camera.certeza_minima no tiene MinValueValidator ni
        MaxValueValidator, así que el form acepta valores fuera de [0.0, 1.0]
        aunque el widget lo sugiera como rango. Este test documenta el
        comportamiento actual, no lo valida como correcto.
        """
        form = CameraForm(data={
            'nombre': 'Patio',
            'ip': '192.168.1.50',
            'intervalo_captura': 1.0,
            'certeza_minima': 5.0,
        })
        self.assertTrue(form.is_valid())