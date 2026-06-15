from datetime import time

from django import forms

from .models import RegistroBitacora


SLOT_MINUTES = 15
CALENDAR_START = time(8, 0)
CALENDAR_END = time(18, 45)


class RegistroBitacoraForm(forms.ModelForm):
    class Meta:
        model = RegistroBitacora
        fields = (
            "ticket",
            "rbd",
            "vinculo_ticket",
            "dia",
            "hora",
            "es_fin_de_semana",
            "llamada_realizada",
        )
        labels = {
            "ticket": "Ticket",
            "rbd": "RBD",
            "vinculo_ticket": "Vinculo Ticket",
            "dia": "Dia",
            "hora": "Hora",
            "es_fin_de_semana": "Agenda de fin de semana",
            "llamada_realizada": "Llamada realizada",
        }
        widgets = {
            "ticket": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Tu respuesta",
                    "autocomplete": "off",
                }
            ),
            "rbd": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Tu respuesta",
                    "autocomplete": "off",
                }
            ),
            "vinculo_ticket": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Tu respuesta",
                    "autocomplete": "off",
                }
            ),
            "dia": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "hora": forms.TimeInput(
                attrs={
                    "class": "form-control",
                    "type": "time",
                    "step": str(SLOT_MINUTES * 60),
                }
            ),
            "es_fin_de_semana": forms.CheckboxInput(
                attrs={
                    "class": "weekend-checkbox",
                }
            ),
            "llamada_realizada": forms.CheckboxInput(
                attrs={
                    "class": "weekend-checkbox",
                }
            ),
        }

    def clean_hora(self):
        hora = self.cleaned_data.get("hora")
        if hora and (hora.second or hora.microsecond or hora.minute % SLOT_MINUTES):
            raise forms.ValidationError("La hora debe estar en bloques de 15 minutos.")
        if hora and (hora < CALENDAR_START or hora >= CALENDAR_END):
            raise forms.ValidationError("La hora debe estar entre 08:00 y 18:30.")
        return hora

    def clean(self):
        cleaned = super().clean()
        dia = cleaned.get("dia")
        hora = cleaned.get("hora")
        if dia and hora:
            registros = RegistroBitacora.objects.filter(
                dia=dia,
                hora=hora,
                estado=RegistroBitacora.ESTADO_AGENDADA,
            )
            if self.instance and self.instance.pk:
                registros = registros.exclude(pk=self.instance.pk)
            existe = registros.exists()
            if existe:
                self.add_error(
                    "hora",
                    "Ya esta agendada para esta hora. Selecciona otro bloque disponible.",
                )
        return cleaned
