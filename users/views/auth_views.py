"""
Vistas de autenticación: registro (solo bootstrap del Admin único), login y logout.
"""

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect

from ..forms import CustomUserCreationForm


# ============================================================
# REGISTRO — solo habilitado para crear el Admin único (bootstrap)
# ============================================================

def register_view(request):

    if request.user.is_authenticated:
        return redirect('home')

    # IRIS no es multiusuario: una vez que existe un Admin,
    # el registro público queda cerrado.
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
# LOGIN
# ============================================================

def login_view(request):

    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':

        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

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