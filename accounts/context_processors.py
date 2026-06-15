from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from bitacora.models import RegistroBitacora

from .models import Procedimiento


def notificaciones_operativas(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"notificaciones_pendientes": 0, "notificaciones_resumen": []}

    hoy = timezone.localdate()
    procedimientos = Procedimiento.objects.filter(
        activo=True,
        estado__in=[Procedimiento.ESTADO_PENDIENTE, Procedimiento.ESTADO_EN_PROCESO],
        fecha_compromiso__lte=hoy,
    )
    if any(field.name == "tipo" for field in Procedimiento._meta.fields):
        procedimientos = procedimientos.filter(tipo=getattr(Procedimiento, "TIPO_GESTION", "gestion"))
    agendas = RegistroBitacora.objects.filter(
        estado=RegistroBitacora.ESTADO_AGENDADA,
        dia__gte=hoy,
        dia__lte=hoy + timedelta(days=1),
    )

    if not user.is_staff:
        procedimientos = procedimientos.filter(Q(creado_por=user) | Q(responsable=user))
        agendas = agendas.filter(usuario=user)

    procedimientos_count = procedimientos.count()
    agendas_count = agendas.count()
    return {
        "notificaciones_pendientes": procedimientos_count + agendas_count,
        "notificaciones_resumen": [
            ("Gestiones", procedimientos_count),
            ("Agendas 24h", agendas_count),
        ],
    }
