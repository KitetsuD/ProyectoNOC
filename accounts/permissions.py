from functools import wraps

from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


PERFIL_ADMIN = "admin"
PERFIL_OPERADOR = "operador"
PERFIL_RBD = "rbd"
GRUPO_SOLO_RBD = "Perfil RBD"

PERFIL_CHOICES = (
    (PERFIL_OPERADOR, "Operador"),
    (PERFIL_RBD, "Solo RBD"),
    (PERFIL_ADMIN, "ADMIN"),
)


def _grupo_solo_rbd():
    grupo, _ = Group.objects.get_or_create(name=GRUPO_SOLO_RBD)
    return grupo


def es_admin(user):
    return bool(user and user.is_authenticated and user.is_staff)


def es_solo_rbd(user):
    return bool(
        user
        and user.is_authenticated
        and not user.is_staff
        and user.groups.filter(name=GRUPO_SOLO_RBD).exists()
    )


def perfil_usuario(user):
    if es_admin(user):
        return PERFIL_ADMIN
    if es_solo_rbd(user):
        return PERFIL_RBD
    return PERFIL_OPERADOR


def etiqueta_perfil_usuario(user):
    return dict(PERFIL_CHOICES).get(perfil_usuario(user), "Operador")


def aplicar_perfil_usuario(user, perfil):
    grupo_rbd = _grupo_solo_rbd()
    user.is_staff = perfil == PERFIL_ADMIN
    if not user.pk:
        return
    user.groups.remove(grupo_rbd)
    if perfil == PERFIL_RBD:
        user.groups.add(grupo_rbd)


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not es_admin(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapper


def operador_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if es_solo_rbd(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapper


def puede_gestionar_contactos(user):
    return bool(user and user.is_authenticated)


def puede_gestionar_bitacora(user, registro):
    return bool(user and user.is_authenticated and not es_solo_rbd(user))


def puede_ver_recordatorio(user, recordatorio):
    return es_admin(user) or recordatorio.creado_por_id == user.id or recordatorio.asignado_a_id == user.id
