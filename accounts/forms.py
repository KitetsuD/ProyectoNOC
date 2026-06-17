import re
from pathlib import Path

from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import EnlaceOperativo, Procedimiento, SolicitudSagec, SolicitudSicret
from .permissions import PERFIL_CHOICES, PERFIL_OPERADOR, aplicar_perfil_usuario, perfil_usuario


def _clean_documento_apoyo(enlace):
    enlace = (enlace or "").strip()
    if not enlace:
        return ""
    if enlace.startswith("/") or enlace.startswith(("http://", "https://")):
        return enlace
    raise forms.ValidationError(
        "Usa una URL completa o una ruta interna que comience con /."
    )


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
        extensiones_validas = {".xlsx", ".xlsm"}
        if extension not in extensiones_validas:
            esperadas = ", ".join(sorted(extensiones_validas))
            raise forms.ValidationError(f"Formato no permitido. Usa: {esperadas}.")
        return archivo


class AdminUserForm(forms.ModelForm):
    perfil = forms.ChoiceField(
        label="Perfil",
        choices=PERFIL_CHOICES,
        initial=PERFIL_OPERADOR,
        widget=forms.Select(attrs={"class": "admin-control"}),
    )
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
        fields = ("username", "first_name", "last_name", "email", "perfil", "is_active")
        labels = {
            "username": "Usuario",
            "first_name": "Nombre",
            "last_name": "Apellido",
            "email": "Email",
            "is_active": "Usuario activo",
        }
        widgets = {
            "username": forms.TextInput(attrs={"class": "admin-control", "autocomplete": "off"}),
            "first_name": forms.TextInput(attrs={"class": "admin-control", "autocomplete": "off"}),
            "last_name": forms.TextInput(attrs={"class": "admin-control", "autocomplete": "off"}),
            "email": forms.EmailInput(attrs={"class": "admin-control", "autocomplete": "off"}),
            "is_active": forms.CheckboxInput(attrs={"class": "admin-check"}),
        }

    def __init__(self, *args, creating=False, **kwargs):
        self.creating = creating
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["perfil"].initial = perfil_usuario(self.instance)
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
        aplicar_perfil_usuario(user, self.cleaned_data.get("perfil") or PERFIL_OPERADOR)
        if commit:
            user.save()
            aplicar_perfil_usuario(user, self.cleaned_data.get("perfil") or PERFIL_OPERADOR)
        return user


class ProcedimientoForm(forms.ModelForm):
    enlace = forms.CharField(
        label="Documento de apoyo externo",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "admin-control",
                "autocomplete": "off",
                "placeholder": "https://... o /static/...",
            }
        ),
    )

    class Meta:
        model = Procedimiento
        fields = (
            "titulo",
            "tipo",
            "categoria",
            "descripcion",
            "contenido",
            "fecha_compromiso",
            "prioridad",
            "responsable",
            "resultado",
            "enlace",
            "archivo",
            "orden",
            "activo",
        )
        labels = {
            "titulo": "Nombre del procedimiento",
            "tipo": "Tipo",
            "categoria": "Caso / categoria",
            "descripcion": "Cuando usarlo",
            "contenido": "Pasos del procedimiento",
            "fecha_compromiso": "Fecha compromiso",
            "prioridad": "Prioridad",
            "responsable": "Responsable",
            "resultado": "Resultado / cierre",
            "enlace": "Documento de apoyo externo",
            "archivo": "Cargar documento",
            "orden": "Orden visual",
            "activo": "Visible para operadores",
        }
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "admin-control", "autocomplete": "off"}),
            "tipo": forms.Select(attrs={"class": "admin-control"}),
            "categoria": forms.TextInput(attrs={"class": "admin-control", "autocomplete": "off"}),
            "descripcion": forms.TextInput(attrs={"class": "admin-control", "autocomplete": "off"}),
            "contenido": forms.Textarea(attrs={"class": "admin-control", "rows": 5}),
            "fecha_compromiso": forms.DateInput(attrs={"class": "admin-control", "type": "date"}),
            "prioridad": forms.Select(attrs={"class": "admin-control"}),
            "responsable": forms.Select(attrs={"class": "admin-control"}),
            "resultado": forms.Textarea(attrs={"class": "admin-control", "rows": 3}),
            "archivo": forms.ClearableFileInput(attrs={"class": "admin-control"}),
            "orden": forms.NumberInput(attrs={"class": "admin-control", "min": 0}),
            "activo": forms.CheckboxInput(attrs={"class": "admin-check"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        usuarios = get_user_model().objects.filter(is_active=True).order_by("username")
        self.fields["responsable"].queryset = usuarios
        self.fields["responsable"].required = False
        self.fields["fecha_compromiso"].initial = timezone.localdate()
        if user and not user.is_staff:
            self.fields["responsable"].queryset = usuarios.filter(pk=user.pk)
            self.fields["responsable"].initial = user
            self.fields["activo"].initial = True

    def clean_archivo(self):
        archivo = self.cleaned_data.get("archivo")
        if not archivo:
            return archivo
        extension = Path(archivo.name).suffix.lower()
        permitidas = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"}
        if extension not in permitidas:
            raise forms.ValidationError("Formato no permitido. Usa PDF, Word, PowerPoint o Excel.")
        return archivo

    def clean_enlace(self):
        return _clean_documento_apoyo(self.cleaned_data.get("enlace"))

    def clean_fecha_compromiso(self):
        fecha = self.cleaned_data.get("fecha_compromiso")
        if fecha and fecha < timezone.localdate():
            raise forms.ValidationError("La fecha compromiso no puede ser anterior a hoy.")
        return fecha


class AdminTutorialForm(forms.ModelForm):
    enlace = forms.CharField(
        label="Documento de apoyo externo",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "admin-control",
                "autocomplete": "off",
                "placeholder": "https://... o /static/...",
            }
        ),
    )

    class Meta:
        model = Procedimiento
        fields = (
            "titulo",
            "categoria",
            "descripcion",
            "contenido",
            "enlace",
            "archivo",
            "orden",
            "activo",
        )
        labels = {
            "titulo": "Nombre del procedimiento",
            "categoria": "Caso / categoria",
            "descripcion": "Cuando usarlo",
            "contenido": "Pasos del procedimiento",
            "enlace": "Documento de apoyo externo",
            "archivo": "Cargar documento",
            "orden": "Orden visual",
            "activo": "Visible para operadores",
        }
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "admin-control", "autocomplete": "off"}),
            "categoria": forms.TextInput(attrs={"class": "admin-control", "autocomplete": "off"}),
            "descripcion": forms.TextInput(attrs={"class": "admin-control", "autocomplete": "off"}),
            "contenido": forms.Textarea(attrs={"class": "admin-control", "rows": 7}),
            "archivo": forms.ClearableFileInput(attrs={"class": "admin-control"}),
            "orden": forms.NumberInput(attrs={"class": "admin-control", "min": 0}),
            "activo": forms.CheckboxInput(attrs={"class": "admin-check"}),
        }

    def clean_archivo(self):
        archivo = self.cleaned_data.get("archivo")
        if not archivo:
            return archivo
        extension = Path(archivo.name).suffix.lower()
        permitidas = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"}
        if extension not in permitidas:
            raise forms.ValidationError("Formato no permitido. Usa PDF, Word, PowerPoint o Excel.")
        return archivo

    def clean_enlace(self):
        return _clean_documento_apoyo(self.cleaned_data.get("enlace"))


class AdminTutorialDocumentoForm(forms.Form):
    archivo = forms.FileField(
        label="Documento base de procedimientos",
        widget=forms.ClearableFileInput(attrs={"class": "admin-file-input", "accept": ".docx"}),
    )

    def clean_archivo(self):
        archivo = self.cleaned_data.get("archivo")
        if not archivo:
            return archivo
        extension = Path(archivo.name).suffix.lower()
        if extension != ".docx":
            raise forms.ValidationError("Formato no permitido. Usa el documento base en formato .docx.")
        return archivo


class EnlaceOperativoForm(forms.ModelForm):
    class Meta:
        model = EnlaceOperativo
        fields = ("titulo", "categoria", "descripcion", "url", "activo")
        labels = {
            "titulo": "Nombre",
            "categoria": "Categoria",
            "descripcion": "Descripcion",
            "url": "URL",
            "activo": "Visible para operadores",
        }
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "admin-control", "autocomplete": "off"}),
            "categoria": forms.TextInput(attrs={"class": "admin-control", "autocomplete": "off", "placeholder": "Ej: Plataformas"}),
            "descripcion": forms.TextInput(attrs={"class": "admin-control", "autocomplete": "off"}),
            "url": forms.URLInput(attrs={"class": "admin-control", "autocomplete": "off", "placeholder": "https://"}),
            "activo": forms.CheckboxInput(attrs={"class": "admin-check"}),
        }


class SicretSolicitudForm(forms.ModelForm):
    class Meta:
        model = SolicitudSicret
        fields = (
            "ticket_netcracker",
            "rbd",
            "zona",
            "comuna",
            "nombre_escuela",
            "direccion",
            "ip_servicio",
            "instancia",
            "nombre_contacto",
            "telefono",
            "correo",
            "estado_enlace",
            "descripcion_falla",
            "detalle_adicional",
        )
        labels = {
            "ticket_netcracker": "Ticket Netcracker",
            "rbd": "RBD",
            "zona": "Zona",
            "comuna": "Comuna",
            "nombre_escuela": "Nombre de escuela",
            "direccion": "Direccion",
            "ip_servicio": "IP de servicio",
            "instancia": "Instancia",
            "nombre_contacto": "Nombre contacto",
            "telefono": "Telefono",
            "correo": "Correo",
            "estado_enlace": "Estado actual del enlace",
            "descripcion_falla": "Descripcion falla",
            "detalle_adicional": "Detalle adicional",
        }
        widgets = {
            "ticket_netcracker": forms.TextInput(attrs={"class": "sicret-control", "autocomplete": "off"}),
            "rbd": forms.TextInput(attrs={"class": "sicret-control", "autocomplete": "off"}),
            "zona": forms.TextInput(attrs={"class": "sicret-control", "autocomplete": "off"}),
            "comuna": forms.TextInput(attrs={"class": "sicret-control", "autocomplete": "off"}),
            "nombre_escuela": forms.TextInput(attrs={"class": "sicret-control", "autocomplete": "off"}),
            "direccion": forms.TextInput(attrs={"class": "sicret-control", "autocomplete": "off"}),
            "ip_servicio": forms.TextInput(attrs={"class": "sicret-control", "autocomplete": "off"}),
            "instancia": forms.TextInput(attrs={"class": "sicret-control", "autocomplete": "off"}),
            "nombre_contacto": forms.TextInput(attrs={"class": "sicret-control", "autocomplete": "off"}),
            "telefono": forms.TextInput(attrs={"class": "sicret-control", "autocomplete": "off"}),
            "correo": forms.EmailInput(attrs={"class": "sicret-control", "autocomplete": "off"}),
            "estado_enlace": forms.RadioSelect(attrs={"class": "sicret-radio-list"}),
            "descripcion_falla": forms.Select(attrs={"class": "sicret-control"}),
            "detalle_adicional": forms.Textarea(attrs={"class": "sicret-control", "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["descripcion_falla"].choices = [("", "Elige"), *SolicitudSicret.TIPOS_FALLA]


class SagecSolicitudForm(forms.ModelForm):
    class Meta:
        model = SolicitudSagec
        fields = (
            "fecha_caida",
            "rbd",
            "motivo_ingreso",
            "numero_ticket",
            "motivo_falla_terceros",
            "id_falla_asociada",
        )
        labels = {
            "fecha_caida": "Fecha de caida",
            "rbd": "RBD con problemas",
            "motivo_ingreso": "Motivo de ingreso",
            "numero_ticket": "Numero de ticket",
            "motivo_falla_terceros": "Motivo de falla terceros",
            "id_falla_asociada": "ID de falla asociada",
        }
        widgets = {
            "fecha_caida": forms.DateInput(attrs={"class": "sicret-control", "type": "date"}),
            "rbd": forms.TextInput(attrs={"class": "sicret-control", "autocomplete": "off", "placeholder": "Escriba su respuesta"}),
            "motivo_ingreso": forms.RadioSelect(attrs={"class": "sicret-radio-list"}),
            "numero_ticket": forms.TextInput(attrs={"class": "sicret-control", "autocomplete": "off", "placeholder": "Ej: 2025 123456"}),
            "motivo_falla_terceros": forms.RadioSelect(attrs={"class": "sicret-radio-list"}),
            "id_falla_asociada": forms.TextInput(attrs={"class": "sicret-control", "autocomplete": "off", "placeholder": "Solo el numero, si aplica"}),
        }

    def clean_rbd(self):
        rbd = (self.cleaned_data.get("rbd") or "").strip()
        if not rbd.isdigit():
            raise forms.ValidationError("El RBD debe ser numerico.")
        return rbd

    def clean_numero_ticket(self):
        numero_ticket = (self.cleaned_data.get("numero_ticket") or "").strip()
        if not re.match(r"^\d{4}\s+\d{5,}$", numero_ticket):
            raise forms.ValidationError("Respeta el formato: 2025 123456.")
        return numero_ticket
