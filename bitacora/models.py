from django.conf import settings
from django.db import models
from django.db.models import Q


class RegistroBitacora(models.Model):
    ESTADO_AGENDADA = "agendada"
    ESTADO_CANCELADA = "cancelada"
    ESTADOS = (
        (ESTADO_AGENDADA, "Agendada"),
        (ESTADO_CANCELADA, "Cancelada"),
    )

    ticket = models.CharField(max_length=80)
    rbd = models.CharField(max_length=40)
    vinculo_ticket = models.CharField(max_length=500)
    dia = models.DateField()
    hora = models.TimeField()
    es_fin_de_semana = models.BooleanField(default=False, verbose_name="agendamiento de fin de semana")
    llamada_realizada = models.BooleanField(default=False)
    llamada_actualizada_en = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_AGENDADA)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="registros_bitacora",
    )
    cancelado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="registros_bitacora_cancelados",
        null=True,
        blank=True,
    )
    cancelado_en = models.DateTimeField(null=True, blank=True)
    motivo_cancelacion = models.CharField(max_length=240, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-dia", "-hora")
        constraints = [
            models.UniqueConstraint(
                fields=("dia", "hora"),
                condition=Q(estado="agendada"),
                name="bitacora_unica_por_dia_hora",
                violation_error_message="Ya existe un agendamiento registrado para ese dia y hora.",
            )
        ]
        verbose_name = "registro de bitacora"
        verbose_name_plural = "registros de bitacora"

    def __str__(self):
        hora = self.hora.strftime("%H:%M") if self.hora else ""
        return f"{self.ticket} - {self.dia} {hora}"
