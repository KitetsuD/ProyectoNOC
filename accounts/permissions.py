from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def es_admin(user):
    return bool(user and user.is_authenticated and user.is_staff)


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not es_admin(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapper


def puede_gestionar_contactos(user):
    return es_admin(user)


def puede_gestionar_bitacora(user, registro):
    return es_admin(user) or registro.usuario_id == user.id


def puede_ver_recordatorio(user, recordatorio):
    return es_admin(user) or recordatorio.creado_por_id == user.id or recordatorio.asignado_a_id == user.id
