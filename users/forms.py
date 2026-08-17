from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Correo electrónico...'
        })
    )

    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Contraseña...'
        })
    )

    password2 = forms.CharField(
        label="Confirmar Contraseña",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirmar contraseña...'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'placeholder': 'Nombre de usuario...'
            })
        }


from .models import Camera, CameraImage

class CameraForm(forms.ModelForm):
    class Meta:
        model = Camera
        fields = ['nombre', 'ip', 'intervalo_captura', 'certeza_minima']
        widgets = {
            'intervalo_captura': forms.NumberInput(attrs={'step': 0.1, 'min': 0.1}),
            'certeza_minima': forms.NumberInput(attrs={'step': 0.1, 'min': 0.0, 'max': 1.0}),
        }

class CameraImageForm(forms.ModelForm):
    class Meta:
        model = CameraImage
        fields = ['imagen']

class CameraSettingsForm(forms.ModelForm):
    class Meta:
        model = Camera
        fields = ['nombre', 'ip', 'intervalo_captura', 'certeza_minima']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'ip': forms.TextInput(attrs={'class': 'form-control'}),
            'intervalo_captura': forms.NumberInput(attrs={'step': '0.1', 'min': '0', 'class': 'form-control'}),
            'certeza_minima': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '1', 'class': 'form-control'}),
        }