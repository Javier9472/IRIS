"""
Vistas de autenticación: registro, login y logout.
"""

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from ..forms import CustomUserCreationForm


# ============================================================
# REGISTRO
# ============================================================

def register_view(request):

    # Si ya está conectado, vuelve al home
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':

        form = CustomUserCreationForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'Cuenta creada correctamente. Ahora inicia sesión.'
            )

            # IMPORTANTE:
            # NO hacemos login automático.
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

        username = request.POST.get(
            'username',
            ''
        ).strip()

        password = request.POST.get(
            'password',
            ''
        )

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(
                request,
                user
            )

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
