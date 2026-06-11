from django.db import models


class RbdServicio(models.Model):
    rbd = models.PositiveIntegerField(unique=True)
    nombre_establecimiento = models.CharField(max_length=255, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    localidad = models.CharField(max_length=120, blank=True)
    region = models.CharField(max_length=120, blank=True)
    lat = models.FloatField(null=True, blank=True)
    long = models.FloatField(null=True, blank=True)
    zona = models.CharField(max_length=40, blank=True)
    zonal = models.CharField(max_length=40, blank=True)
    tecnologia = models.CharField(max_length=120, blank=True)
    tipo = models.CharField(max_length=120, blank=True)
    status_imaster = models.CharField(max_length=80, blank=True)
    fiscalizacion = models.CharField(max_length=80, blank=True)
    vigencia = models.CharField(max_length=80, blank=True)
    matricula = models.CharField(max_length=40, blank=True)
    tipo_ont = models.CharField(max_length=120, blank=True)
    puerta = models.CharField(max_length=120, blank=True)
    nodo = models.CharField(max_length=160, blank=True)
    bw_nacional = models.FloatField(null=True, blank=True)
    bw_internacional = models.FloatField(null=True, blank=True)
    bw = models.FloatField(null=True, blank=True)
    fw_usg = models.CharField(max_length=120, blank=True)
    serie_usg = models.CharField(max_length=120, blank=True)
    codigo_servicio_ncc = models.CharField(max_length=140, blank=True)
    vlan = models.CharField(max_length=40, blank=True)
    codigo_servicio_oss = models.CharField(max_length=140, blank=True)
    ip = models.CharField(max_length=80, blank=True)
    jornada_categoria = models.CharField(max_length=5, blank=True)
    jornada_horario = models.CharField(max_length=220, blank=True)
    jornada_descripcion = models.CharField(max_length=180, blank=True)
    dependencia_mpls = models.CharField(max_length=180, blank=True)
    por = models.CharField(max_length=120, blank=True)
    ont = models.CharField(max_length=120, blank=True)
    tiene_rfs = models.CharField(max_length=40, blank=True)
    rfs = models.CharField(max_length=160, blank=True)
    caja = models.CharField(max_length=120, blank=True)
    fil = models.CharField(max_length=120, blank=True)
    servicio_existente_oss = models.CharField(max_length=140, blank=True)
    tiene_ov = models.CharField(max_length=40, blank=True)
    orden_venta = models.CharField(max_length=120, blank=True)
    estado_ov = models.CharField(max_length=120, blank=True)
    bpi = models.CharField(max_length=200, blank=True)
    datos = models.JSONField(default=dict, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("rbd",)
        verbose_name = "servicio RBD"
        verbose_name_plural = "servicios RBD"

    def __str__(self):
        return f"RBD {self.rbd} - {self.nombre_establecimiento}"

    @property
    def tecnologia_resumen(self):
        return self.tecnologia or self.tipo or "Sin informacion"

    @property
    def tecnologia_corta(self):
        texto = f"{self.tecnologia} {self.tipo}".upper()
        if "MMOO" in texto or "MICRO" in texto:
            return "MMOO"
        if "STAR" in texto or "STLK" in texto:
            return "STLK"
        if "FIBRA" in texto or "FTTH" in texto or "MSAN" in texto:
            return "FTTH"
        return (self.tipo or self.tecnologia or "TEC").split()[0].upper()

    @property
    def identificador_tecnico(self):
        if self.codigo_servicio_oss:
            return f"RBD_{self.codigo_servicio_oss}_{self.tecnologia_corta}"
        return f"RBD_{self.rbd}_{self.tecnologia_corta}"


class RbdContacto(models.Model):
    servicio = models.ForeignKey(
        RbdServicio,
        on_delete=models.CASCADE,
        related_name="contactos",
    )
    orden = models.PositiveSmallIntegerField()
    nombre = models.CharField(max_length=180, blank=True)
    telefono = models.CharField(max_length=80, blank=True)
    celular = models.CharField(max_length=80, blank=True)
    email = models.EmailField(max_length=180, blank=True)
    cargo = models.CharField(max_length=140, blank=True)
    fuente = models.CharField(max_length=120, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("servicio__rbd", "orden")
        constraints = [
            models.UniqueConstraint(
                fields=("servicio", "orden"),
                name="rbd_contacto_unico_por_orden",
            )
        ]
        verbose_name = "contacto RBD"
        verbose_name_plural = "contactos RBD"

    def __str__(self):
        nombre = self.nombre or "Sin nombre"
        return f"RBD {self.servicio.rbd} - Contacto {self.orden}: {nombre}"
