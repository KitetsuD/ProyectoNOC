from django.conf import settings
from django.db import models
from django.utils import timezone


class Procedimiento(models.Model):
    TIPO_PROCEDIMIENTO = "procedimiento"
    TIPO_GESTION = "gestion"
    TIPOS = (
        (TIPO_PROCEDIMIENTO, "Procedimiento"),
        (TIPO_GESTION, "Gestion interna"),
    )

    ESTADO_PENDIENTE = "pendiente"
    ESTADO_EN_PROCESO = "en_proceso"
    ESTADO_COMPLETADO = "completado"
    ESTADOS = (
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_EN_PROCESO, "En proceso"),
        (ESTADO_COMPLETADO, "Completado"),
    )

    PRIORIDAD_BAJA = "baja"
    PRIORIDAD_MEDIA = "media"
    PRIORIDAD_ALTA = "alta"
    PRIORIDADES = (
        (PRIORIDAD_BAJA, "Baja"),
        (PRIORIDAD_MEDIA, "Media"),
        (PRIORIDAD_ALTA, "Alta"),
    )

    titulo = models.CharField(max_length=160)
    tipo = models.CharField(max_length=20, choices=TIPOS, default=TIPO_PROCEDIMIENTO)
    categoria = models.CharField(max_length=80, blank=True)
    descripcion = models.CharField(max_length=260, blank=True)
    contenido = models.TextField(blank=True)
    enlace = models.URLField(max_length=500, blank=True)
    orden = models.PositiveIntegerField(default=0)
    estado = models.CharField(max_length=16, choices=ESTADOS, default=ESTADO_PENDIENTE)
    prioridad = models.CharField(max_length=12, choices=PRIORIDADES, default=PRIORIDAD_MEDIA)
    fecha_compromiso = models.DateField(null=True, blank=True)
    resultado = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="procedimientos_creados",
    )
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="procedimientos_actualizados",
        null=True,
        blank=True,
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="procedimientos_asignados",
        null=True,
        blank=True,
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    completado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("estado", "fecha_compromiso", "-prioridad", "orden", "titulo")
        verbose_name = "procedimiento"
        verbose_name_plural = "procedimientos"

    def __str__(self):
        return self.titulo

    @property
    def pasos_tutorial(self):
        pasos = []
        for linea in self.contenido.splitlines():
            texto = linea.strip()
            if not texto:
                continue
            if ". " in texto[:4]:
                texto = texto.split(". ", 1)[1].strip()
            pasos.append(texto)
        return pasos

    @property
    def esta_vencido(self):
        return (
            self.estado != self.ESTADO_COMPLETADO
            and self.fecha_compromiso is not None
            and self.fecha_compromiso < timezone.localdate()
        )

    @property
    def es_hoy(self):
        return (
            self.estado != self.ESTADO_COMPLETADO
            and self.fecha_compromiso is not None
            and self.fecha_compromiso == timezone.localdate()
        )


class SolicitudSicret(models.Model):
    ESTADO_SICRET_EN_PROCESO = "en_proceso"
    ESTADO_SICRET_TERRENO = "enviado_terreno"
    ESTADO_SICRET_PAUSA = "en_pausa"
    ESTADO_SICRET_CERRADO = "cerrado"
    ESTADOS_SICRET = (
        (ESTADO_SICRET_EN_PROCESO, "En proceso"),
        (ESTADO_SICRET_TERRENO, "Enviado a terreno"),
        (ESTADO_SICRET_PAUSA, "En pausa"),
        (ESTADO_SICRET_CERRADO, "Cerrado"),
    )

    ENLACE_OFFLINE = "offline"
    ENLACE_ONLINE = "online"
    ENLACE_INTERMITENTE = "intermitente"
    ESTADOS_ENLACE = (
        (ENLACE_OFFLINE, "Offline"),
        (ENLACE_ONLINE, "Online"),
        (ENLACE_INTERMITENTE, "Intermitente"),
    )

    FALLA_ENLACE_OFFLINE = "enlace_offline"
    FALLA_ENLACE_INTERMITENTE = "enlace_intermitente"
    FALLA_UPS = "falla_ups"
    FALLA_RACK = "falla_rack"
    FALLA_CLIENTE_PRUEBAS = "cliente_problemas_pruebas"
    FALLA_CLIENTE_EXIGE_VISITA = "cliente_exige_visita"
    FALLA_SWITCH_HUAWEI = "switch_huawei_desconectado"
    FALLA_CORTE_FIBRA = "corte_fibra_optica"
    TIPOS_FALLA = (
        (FALLA_ENLACE_OFFLINE, "Enlace Offline"),
        (FALLA_ENLACE_INTERMITENTE, "Enlace intermitente"),
        (FALLA_UPS, "Falla de UPS"),
        (FALLA_RACK, "Falla en Rack"),
        (FALLA_CLIENTE_PRUEBAS, "Cliente con problemas para realizar pruebas"),
        (FALLA_CLIENTE_EXIGE_VISITA, "Cliente exige visita tecnica"),
        (FALLA_SWITCH_HUAWEI, "Switch Huawei desconectado"),
        (FALLA_CORTE_FIBRA, "Corte de Fibra Optica"),
    )

    ticket_netcracker = models.CharField(max_length=80)
    rbd = models.CharField(max_length=40)
    zona = models.CharField(max_length=80)
    comuna = models.CharField(max_length=120)
    nombre_escuela = models.CharField(max_length=180)
    direccion = models.CharField(max_length=240)
    ip_servicio = models.CharField(max_length=80)
    instancia = models.CharField(max_length=120)
    nombre_contacto = models.CharField(max_length=160)
    telefono = models.CharField(max_length=60)
    correo = models.EmailField(max_length=180)
    estado_enlace = models.CharField(max_length=20, choices=ESTADOS_ENLACE)
    descripcion_falla = models.CharField(max_length=40, choices=TIPOS_FALLA)
    detalle_adicional = models.TextField(blank=True)
    estado_sicret = models.CharField(
        max_length=24,
        choices=ESTADOS_SICRET,
        default=ESTADO_SICRET_EN_PROCESO,
    )
    estado_sicret_actualizado_en = models.DateTimeField(null=True, blank=True)
    estado_sicret_actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="estados_sicret_actualizados",
        null=True,
        blank=True,
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="solicitudes_sicret",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-creado_en",)
        verbose_name = "solicitud SICRET"
        verbose_name_plural = "solicitudes SICRET"

    def __str__(self):
        return f"SICRET {self.ticket_netcracker} - RBD {self.rbd}"
