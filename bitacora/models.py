from django.conf import settings
from django.db import models


class RegistroBitacora(models.Model):
    ticket = models.CharField(max_length=80)
    rbd = models.CharField(max_length=40)
    vinculo_ticket = models.CharField(max_length=500)
    dia = models.DateField()
    hora = models.TimeField()
    es_fin_de_semana = models.BooleanField(default=False, verbose_name="agendamiento de fin de semana")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="registros_bitacora",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-dia", "-hora")
        constraints = [
            models.UniqueConstraint(
                fields=("dia", "hora"),
                name="bitacora_unica_por_dia_hora",
                violation_error_message="Ya existe un agendamiento registrado para ese dia y hora.",
            )
        ]
        verbose_name = "registro de bitacora"
        verbose_name_plural = "registros de bitacora"

    def __str__(self):
        hora = self.hora.strftime("%H:%M") if self.hora else ""
        return f"{self.ticket} - {self.dia} {hora}"
