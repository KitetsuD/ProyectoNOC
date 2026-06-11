import os
import tempfile
from io import StringIO

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.management import call_command
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from rbd.services.carga_completa import export_carga_completa

from .forms import AdminCargaDatosForm, AdminUserForm


def _admin_required(view_func):
    return login_required(
        user_passes_test(lambda user: user.is_staff, login_url="login")(view_func)
    )


def _active_admins_queryset():
    return get_user_model().objects.filter(is_staff=True, is_active=True)


def _is_last_active_admin(user):
    if not user.is_staff or not user.is_active:
        return False
    return not _active_admins_queryset().exclude(pk=user.pk).exists()


def _save_uploaded_file(uploaded_file):
    suffix = os.path.splitext(uploaded_file.name)[1]
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        for chunk in uploaded_file.chunks():
            temp.write(chunk)
    finally:
        temp.close()
    return temp.name


def _run_import(path):
    output = StringIO()
    call_command("importar_servicios_excel", path=path, stdout=output)
    return output.getvalue().strip()


def _build_master_excel_response():
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    temp_path = temp.name
    temp.close()

    try:
        export_carga_completa(temp_path, include_data=True)
        with open(temp_path, "rb") as excel_file:
            content = excel_file.read()
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass

    response = HttpResponse(
        content,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="ProyectoNOC_Carga_Completa.xlsx"'
    return response


@login_required
def dashboard(request):
    modules = [
        {
            "title": "Clientes y enlaces",
            "description": "Consulta de contactos y enlaces asociados.",
            "state": "Pendiente",
            "url": "",
        },
        {
            "title": "RBD",
            "description": "Busqueda tecnica por numero de RBD, tecnologia, IP y datos del establecimiento.",
            "state": "Disponible",
            "url": reverse("rbd:buscar"),
        },
        {
            "title": "BITACORA",
            "description": "Agendamiento de tickets por dia y hora sin duplicar horarios.",
            "state": "Disponible",
            "url": reverse("bitacora:crear"),
        },
        {
            "title": "Recordatorios",
            "description": "Seguimiento de llamados pendientes y contactos futuros.",
            "state": "Pendiente",
            "url": "",
        },
        {
            "title": "Tickets",
            "description": "Control complementario de casos vinculados a plataformas externas.",
            "state": "Pendiente",
            "url": "",
        },
        {
            "title": "Derivaciones",
            "description": "Acceso centralizado a formularios y derivaciones internas.",
            "state": "Pendiente",
            "url": "",
        },
        {
            "title": "Procedimientos",
            "description": "Repositorio operativo de manuales e instructivos.",
            "state": "Pendiente",
            "url": "",
        },
    ]
    summary = [
        ("Gestiones", "0"),
        ("Pendientes", "0"),
        ("Agendadas", "0"),
        ("Tickets", "0"),
    ]
    return render(
        request,
        "accounts/dashboard.html",
        {
            "modules": modules,
            "summary": summary,
        },
    )


@_admin_required
def admin_carga_datos(request):
    resultado = ""
    if request.method == "POST":
        form = AdminCargaDatosForm(request.POST, request.FILES)
        if form.is_valid():
            temp_path = _save_uploaded_file(form.cleaned_data["archivo"])
            try:
                resultado = _run_import(temp_path)
            except Exception as exc:
                messages.error(request, f"No se pudo cargar el archivo: {exc}")
                resultado = str(exc)
            else:
                messages.success(request, "Carga procesada correctamente.")
            finally:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
    else:
        form = AdminCargaDatosForm()

    return render(
        request,
        "accounts/admin_data_upload.html",
        {"form": form, "resultado": resultado},
    )


@_admin_required
def admin_descargar_plantilla(request):
    return _build_master_excel_response()


@_admin_required
def admin_usuarios(request):
    User = get_user_model()
    usuarios = User.objects.order_by("-is_staff", "-is_active", "username")
    stats = [
        {"label": "Usuarios", "value": User.objects.count()},
        {"label": "Activos", "value": User.objects.filter(is_active=True).count()},
        {"label": "ADMIN", "value": User.objects.filter(is_staff=True).count()},
        {"label": "Inactivos", "value": User.objects.filter(is_active=False).count()},
    ]
    return render(
        request,
        "accounts/admin_user_list.html",
        {"usuarios": usuarios, "stats": stats},
    )


@_admin_required
def admin_usuario_crear(request):
    if request.method == "POST":
        form = AdminUserForm(request.POST, creating=True)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Usuario {user.username} creado correctamente.")
            return redirect("admin_usuarios")
    else:
        form = AdminUserForm(creating=True, initial={"is_active": True})
    return render(
        request,
        "accounts/admin_user_form.html",
        {"form": form, "modo": "Crear usuario", "submit_label": "Crear usuario"},
    )


@_admin_required
def admin_usuario_editar(request, user_id):
    user = get_object_or_404(get_user_model(), pk=user_id)
    if request.method == "POST":
        form = AdminUserForm(request.POST, instance=user)
        if form.is_valid():
            nuevo_staff = form.cleaned_data["is_staff"]
            nuevo_activo = form.cleaned_data["is_active"]
            if _is_last_active_admin(user) and (not nuevo_staff or not nuevo_activo):
                form.add_error(None, "No puedes dejar el sistema sin un ADMIN activo.")
            else:
                form.save()
                messages.success(request, f"Usuario {user.username} actualizado correctamente.")
                return redirect("admin_usuarios")
    else:
        form = AdminUserForm(instance=user)
    return render(
        request,
        "accounts/admin_user_form.html",
        {"form": form, "modo": f"Editar {user.username}", "submit_label": "Guardar cambios", "usuario_editado": user},
    )


@_admin_required
def admin_usuario_accion(request, user_id):
    if request.method != "POST":
        return redirect("admin_usuarios")

    user = get_object_or_404(get_user_model(), pk=user_id)
    accion = request.POST.get("accion")

    if user == request.user and accion in {"desactivar", "eliminar"}:
        messages.error(request, "No puedes desactivar o eliminar tu propio usuario.")
        return redirect("admin_usuarios")

    if accion in {"desactivar", "eliminar"} and _is_last_active_admin(user):
        messages.error(request, "No puedes dejar el sistema sin un ADMIN activo.")
        return redirect("admin_usuarios")

    if accion == "activar":
        user.is_active = True
        user.save(update_fields=["is_active"])
        messages.success(request, f"Usuario {user.username} activado.")
    elif accion == "desactivar":
        user.is_active = False
        user.save(update_fields=["is_active"])
        messages.success(request, f"Usuario {user.username} desactivado.")
    elif accion == "eliminar":
        username = user.username
        user.delete()
        messages.success(request, f"Usuario {username} eliminado.")
    else:
        messages.error(request, "Accion no reconocida.")

    return redirect("admin_usuarios")
