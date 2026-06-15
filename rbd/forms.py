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
        label="Buscar por RBD",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "admin-control",
                "placeholder": "Ej: 4190",
                "autocomplete": "off",
                "inputmode": "numeric",
            }
        ),
    )

    def clean_q(self):
        value = (self.cleaned_data.get("q") or "").strip()
        if value and not value.isdigit():
            raise forms.ValidationError("Ingresa solo numeros de RBD.")
        return value


class AdminRbdServicioForm(forms.ModelForm):
    class Meta:
        model = RbdServicio
        fields = (
            "rbd",
            "nombre_establecimiento",
            "direccion",
            "localidad",
            "region",
            "zona",
            "zonal",
            "matricula",
            "lat",
            "long",
            "bpi",
            "tecnologia",
            "tipo",
            "ip",
            "vlan",
            "puerta",
            "nodo",
            "dependencia_mpls",
            "bw_nacional",
            "bw_internacional",
            "bw",
            "codigo_servicio_oss",
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
            "tecnologia": "Tecnologia actual",
            "tipo": "Tipo tecnologia",
            "ip": "IP",
            "vlan": "VLAN",
            "puerta": "Puerta",
            "nodo": "Nodo",
            "dependencia_mpls": "Dependencia MPLS",
            "bw_nacional": "BW nacional",
            "bw_internacional": "BW internacional",
            "bw": "BW bajada",
            "codigo_servicio_oss": "Codigo OSS",
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
