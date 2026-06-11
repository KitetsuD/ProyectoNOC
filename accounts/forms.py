from pathlib import Path

from django import forms
from django.contrib.auth import get_user_model


class AdminCargaDatosForm(forms.Form):
    archivo = forms.FileField(
        label="Excel maestro",
        widget=forms.ClearableFileInput(attrs={"class": "admin-file-input"}),
    )

    def clean_archivo(self):
        archivo = self.cleaned_data.get("archivo")
        if not archivo:
            return archivo

        extension = Path(archivo.name).suffix.lower()
        extensiones_validas = {".xlsx", ".xlsm", ".xls"}
        if extension not in extensiones_validas:
            esperadas = ", ".join(sorted(extensiones_validas))
            raise forms.ValidationError(f"Formato no permitido. Usa: {esperadas}.")
        return archivo


class AdminUserForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Clave",
        required=False,
        widget=forms.PasswordInput(attrs={"class": "admin-control", "autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Repetir clave",
        required=False,
        widget=forms.PasswordInput(attrs={"class": "admin-control", "autocomplete": "new-password"}),
    )

    class Meta:
        model = get_user_model()
        fields = ("username", "first_name", "last_name", "email", "is_active", "is_staff")
        labels = {
            "username": "Usuario",
            "first_name": "Nombre",
            "last_name": "Apellido",
            "email": "Email",
            "is_active": "Usuario activo",
            "is_staff": "Perfil ADMIN",
        }
        widgets = {
            "username": forms.TextInput(attrs={"class": "admin-control", "autocomplete": "off"}),
            "first_name": forms.TextInput(attrs={"class": "admin-control", "autocomplete": "off"}),
            "last_name": forms.TextInput(attrs={"class": "admin-control", "autocomplete": "off"}),
            "email": forms.EmailInput(attrs={"class": "admin-control", "autocomplete": "off"}),
            "is_active": forms.CheckboxInput(attrs={"class": "admin-check"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "admin-check"}),
        }

    def __init__(self, *args, creating=False, **kwargs):
        self.creating = creating
        super().__init__(*args, **kwargs)
        if creating:
            self.fields["password1"].required = True
            self.fields["password2"].required = True

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        qs = get_user_model().objects.filter(username__iexact=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe un usuario con ese nombre.")
        return username

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if self.creating or password1 or password2:
            if not password1:
                self.add_error("password1", "Ingresa una clave.")
            if not password2:
                self.add_error("password2", "Repite la clave.")
            if password1 and password2 and password1 != password2:
                self.add_error("password2", "Las claves no coinciden.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password1")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user
