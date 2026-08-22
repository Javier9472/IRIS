# users/views/auth_views.py

"""
Vistas de autenticación: registro (solo bootstrap del Admin único), login y logout.
"""

import logging

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_login_failed
from django.contrib import messages
from django.core.cache import cache
from django.dispatch import receiver
from django.shortcuts import render, redirect

from ..forms import CustomUserCreationForm

security_logger = logging.getLogger('iris.security')


# ============================================================
# REGISTRO — solo habilitado para crear el Admin único (bootstrap)
# ============================================================

def register_view(request):

    if request.user.is_authenticated:
        return redirect('home')

    if User.objects.exists():

        messages.error(
            request,
            'El registro está cerrado: IRIS ya tiene un Admin configurado.'
        )

        return redirect('login')

    if request.method == 'POST':

        form = CustomUserCreationForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'Cuenta creada correctamente. Ahora inicia sesión.'
            )

            return redirect('login')

        messages.error(
            request,
            'Verifica los datos ingresados.'
        )

    else:

        form = CustomUserCreationForm()

    return render(
        request,
        'users/register.html',
        {
            'form': form
        }
    )


# ============================================================
# RATE LIMITING — login (Fase 4). Ver settings.py: CACHES,
# LOGIN_RATE_LIMIT_*, TRUST_PROXY_HEADERS.
# ============================================================

def get_client_ip(request):
    # TRUST_PROXY_HEADERS solo se activa en Fase 5, cuando el túnel
    # sea el único punto de entrada confirmado.
    if getattr(settings, 'TRUST_PROXY_HEADERS', False):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()

    return request.META.get('REMOTE_ADDR')


def _rate_limit_keys(request, username):

    ip = get_client_ip(request)

    return f'login_attempts:ip:{ip}', f'login_attempts:user:{username}'


def _is_rate_limited(key):
    return cache.get(key, 0) >= settings.LOGIN_RATE_LIMIT_ATTEMPTS


def _register_failed_attempt(key):

    cache.add(key, 0, settings.LOGIN_RATE_LIMIT_WINDOW)

    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, settings.LOGIN_RATE_LIMIT_WINDOW)


def _clear_attempts(key):
    cache.delete(key)


@receiver(user_login_failed)
def _on_login_failed(sender, credentials, request, **kwargs):

    if request is None:
        return

    username = credentials.get('username', '')

    ip_key, user_key = _rate_limit_keys(request, username)

    _register_failed_attempt(ip_key)
    _register_failed_attempt(user_key)


# ============================================================
# LOGIN
# ============================================================

def login_view(request):

    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':

        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        ip_key, user_key = _rate_limit_keys(request, username)

        if _is_rate_limited(ip_key) or _is_rate_limited(user_key):

            security_logger.warning(
                'Login bloqueado por rate limit — ip=%s user=%s',
                get_client_ip(request),
                username
            )

            messages.error(
                request,
                'Demasiados intentos fallidos. Intenta de nuevo en unos minutos.'
            )

            return render(request, 'users/login.html')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            _clear_attempts(ip_key)
            _clear_attempts(user_key)

            return redirect('home')

        messages.error(
            request,
            'Usuario o contraseña incorrectos.'
        )

    return render(
        request,
        'users/login.html'
    )


# ============================================================
# LOGOUT
# ============================================================

@login_required(login_url='login')
def logout_view(request):

    logout(request)

    return redirect('login')