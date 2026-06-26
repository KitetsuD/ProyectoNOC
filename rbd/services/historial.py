from rbd.models import RbdHistorial


SNAPSHOT_FIELDS = (
    "rbd",
    "nombre_establecimiento",
    "direccion",
    "localidad",
    "region",
    "zona",
    "zonal",
    "tecnologia",
    "tipo",
    "bpi",
    "codigo_servicio_oss",
    "codigo_servicio_ncc",
    "ip",
    "vlan",
    "nodo",
    "puerta",
    "dependencia_mpls",
    "bw_nacional",
    "bw_internacional",
    "bw",
    "dado_baja",
    "baja_fecha",
    "baja_partner",
    "baja_observacion_mineduc",
    "baja_decreto",
    "baja_notificacion_fecha",
    "baja_ov",
    "baja_observacion",
)


def _serializable(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def snapshot_rbd(servicio):
    return {
        field: _serializable(getattr(servicio, field, None))
        for field in SNAPSHOT_FIELDS
    }


def registrar_historial_rbd(servicio, accion, usuario=None, detalle=""):
    return RbdHistorial.objects.create(
        accion=accion,
        rbd=servicio.rbd,
        nombre_establecimiento=servicio.nombre_establecimiento or "",
        bpi=servicio.bpi or "",
        codigo_servicio_oss=servicio.codigo_servicio_oss or "",
        ip=servicio.ip or "",
        tecnologia=servicio.tecnologia_resumen,
        zona=servicio.zona or "",
        localidad=servicio.localidad or "",
        region=servicio.region or "",
        detalle=detalle,
        usuario=usuario if getattr(usuario, "is_authenticated", False) else None,
        snapshot=snapshot_rbd(servicio),
    )
