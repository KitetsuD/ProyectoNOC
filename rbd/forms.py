from django import forms

from .models import RbdServicio


class RbdSearchForm(forms.Form):
    rbd = forms.IntegerField(
        label="RBD",
        min_value=1,
        widget=forms.NumberInput(
            attrs={
                "class": "rbd-input",
                "placeholder": "4190",
                "autocomplete": "off",
            }
        ),
    )


class AdminRbdSearchForm(forms.Form):
    q = forms.CharField(
        label="Buscar por RBD o BPI",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "admin-control",
                "placeholder": "Ej: 4190 o Internet EES",
                "autocomplete": "off",
            }
        ),
    )

    def clean_q(self):
        value = (self.cleaned_data.get("q") or "").strip()
        return value


class AdminBajasUploadForm(forms.Form):
    archivo = forms.FileField(
        label="Excel de bajas",
        widget=forms.ClearableFileInput(attrs={"class": "admin-file-input"}),
    )

    def clean_archivo(self):
        archivo = self.cleaned_data.get("archivo")
        if not archivo:
            return archivo
        nombre = archivo.name.lower()
        if not nombre.endswith((".xlsx", ".xlsm")):
            raise forms.ValidationError("Formato no permitido. Usa un archivo .xlsx o .xlsm.")
        return archivo


class AdminRbdServicioForm(forms.ModelForm):
    class Meta:
        model = RbdServicio
        fields = (
            "rbd",
            "bpi",
            "codigo_servicio_oss",
            "ip",
            "nombre_establecimiento",
            "direccion",
            "localidad",
            "region",
            "zona",
            "zonal",
            "matricula",
            "lat",
            "long",
            "tecnologia",
            "tipo",
            "vlan",
            "puerta",
            "nodo",
            "dependencia_mpls",
            "bw_nacional",
            "bw_internacional",
            "bw",
            "codigo_servicio_ncc",
            "jornada_categoria",
            "jornada_horario",
            "jornada_descripcion",
        )
        labels = {
            "rbd": "RBD",
            "nombre_establecimiento": "Nombre establecimiento",
            "direccion": "Direccion",
            "localidad": "Comuna",
            "region": "Region",
            "zona": "Zona",
            "zonal": "Zonal",
            "matricula": "Matricula",
            "lat": "Latitud",
            "long": "Longitud",
            "bpi": "BPI",
            "codigo_servicio_oss": "EF",
            "ip": "IP",
            "tecnologia": "Tecnologia actual",
            "tipo": "Tipo tecnologia",
            "vlan": "VLAN",
            "puerta": "Puerta",
            "nodo": "Nodo",
            "dependencia_mpls": "Dependencia MPLS",
            "bw_nacional": "BW nacional",
            "bw_internacional": "BW internacional",
            "bw": "BW bajada",
            "codigo_servicio_ncc": "Codigo NCC",
            "jornada_categoria": "Categoria jornada",
            "jornada_horario": "Horario jornada",
            "jornada_descripcion": "Descripcion jornada",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "admin-control")
            field.widget.attrs.setdefault("autocomplete", "off")
