import os
import tempfile
from io import StringIO

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from rbd.forms import AdminRbdSearchForm, AdminRbdServicioForm
from rbd.models import RbdServicio
from rbd.services.carga_completa import export_carga_completa

from .forms import AdminCargaDatosForm, AdminUserForm, ProcedimientoForm, SicretSolicitudForm
from .models import Procedimiento, SolicitudSicret
from .permissions import admin_required


_admin_required = admin_required


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


def _build_master_excel_response(filename="ProyectoNOC_Carga_Completa.xlsx"):
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
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
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
            "description": "Procesos y gestiones internas que deben ejecutarse y cerrarse.",
            "state": "Disponible",
            "url": reverse("procedimientos"),
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


@login_required
def procedimientos(request):
    if request.method == "POST":
        form = ProcedimientoForm(request.POST, user=request.user)
        if form.is_valid():
            procedimiento = form.save(commit=False)
            procedimiento.creado_por = request.user
            procedimiento.actualizado_por = request.user
            if not request.user.is_staff:
                procedimiento.responsable = request.user
                procedimiento.activo = True
            if not procedimiento.responsable:
                procedimiento.responsable = request.user
            procedimiento.save()
            messages.success(request, "Tutorial operativo creado correctamente.")
            return redirect("procedimientos")
    else:
        form = ProcedimientoForm(
            initial={"activo": True, "tipo": Procedimiento.TIPO_PROCEDIMIENTO},
            user=request.user,
        )

    listado = Procedimiento.objects.select_related("creado_por", "actualizado_por", "responsable")
    documentos = listado.filter(tipo=Procedimiento.TIPO_PROCEDIMIENTO)
    gestiones = listado.filter(tipo=Procedimiento.TIPO_GESTION)
    if not request.user.is_staff:
        documentos = documentos.filter(activo=True)
        gestiones = gestiones.filter(Q(activo=True), Q(creado_por=request.user) | Q(responsable=request.user))

    documentos = documentos.order_by("orden", "categoria", "titulo")
    gestiones = gestiones.order_by("estado", "fecha_compromiso", "-prioridad", "orden", "titulo")
    pendientes = gestiones.exclude(estado=Procedimiento.ESTADO_COMPLETADO)
    completados = gestiones.filter(estado=Procedimiento.ESTADO_COMPLETADO)

    return render(
        request,
        "accounts/procedimientos.html",
        {
            "form": form,
            "documentos": documentos,
            "procedimientos": pendientes,
            "completados": completados[:10],
        },
    )


@_admin_required
def procedimiento_toggle(request, procedimiento_id):
    procedimiento = get_object_or_404(Procedimiento, pk=procedimiento_id)
    if request.method == "POST":
        procedimiento.activo = not procedimiento.activo
        procedimiento.actualizado_por = request.user
        procedimiento.save(update_fields=["activo", "actualizado_por", "actualizado_en"])
        estado = "publicado" if procedimiento.activo else "ocultado"
        messages.success(request, f"Procedimiento {estado}.")
    return redirect("procedimientos")


@login_required
def sicret(request):
    if request.method == "POST":
        form = SicretSolicitudForm(request.POST)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.creado_por = request.user
            solicitud.save()
            messages.success(request, "Solicitud SICRET registrada correctamente.")
            return redirect("sicret")
    else:
        form = SicretSolicitudForm()

    solicitudes = SolicitudSicret.objects.select_related("creado_por")
    if not request.user.is_staff:
        solicitudes = solicitudes.filter(creado_por=request.user)

    return render(
        request,
        "accounts/sicret.html",
        {
            "form": form,
            "solicitudes": solicitudes[:8],
        },
    )


@login_required
def procedimiento_accion(request, procedimiento_id):
    procedimiento = get_object_or_404(Procedimiento, pk=procedimiento_id)
    if not request.user.is_staff and procedimiento.responsable_id != request.user.id and procedimiento.creado_por_id != request.user.id:
        raise PermissionDenied
    if request.method != "POST":
        return redirect("procedimientos")

    accion = request.POST.get("accion")
    update_fields = ["estado", "actualizado_por", "actualizado_en"]
    procedimiento.actualizado_por = request.user
    if accion == "iniciar":
        procedimiento.estado = Procedimiento.ESTADO_EN_PROCESO
        procedimiento.completado_en = None
        update_fields.append("completado_en")
        messages.success(request, "Gestion marcada en proceso.")
    elif accion == "completar":
        procedimiento.estado = Procedimiento.ESTADO_COMPLETADO
        procedimiento.resultado = (request.POST.get("resultado") or procedimiento.resultado or "Completado").strip()
        procedimiento.completado_en = timezone.now()
        update_fields.extend(["resultado", "completado_en"])
        messages.success(request, "Gestion completada.")
    elif accion == "reabrir":
        procedimiento.estado = Procedimiento.ESTADO_PENDIENTE
        procedimiento.completado_en = None
        update_fields.append("completado_en")
        messages.success(request, "Gestion reabierta.")
    else:
        messages.error(request, "Accion no reconocida.")
        return redirect("procedimientos")

    procedimiento.save(update_fields=update_fields)
    return redirect("procedimientos")


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
def admin_rbd(request):
    form = AdminRbdSearchForm(request.GET or None)
    resultados = RbdServicio.objects.none()
    termino = ""
    titulo_resultados = "Sin busqueda activa"
    if form.is_valid():
        termino = form.cleaned_data["q"].strip()
        if termino:
            resultados = RbdServicio.objects.filter(rbd=int(termino)).order_by("rbd")
            titulo_resultados = f"Resultado para RBD {termino}"

    return render(
        request,
        "accounts/admin_rbd.html",
        {
            "form": form,
            "resultados": resultados,
            "termino": termino,
            "titulo_resultados": titulo_resultados,
            "total_rbd": RbdServicio.objects.count(),
        },
    )


@_admin_required
def admin_rbd_editar(request, servicio_id):
    servicio = get_object_or_404(RbdServicio, pk=servicio_id)
    if request.method == "POST":
        form = AdminRbdServicioForm(request.POST, instance=servicio)
        if form.is_valid():
            form.save()
            messages.success(request, f"RBD {servicio.rbd} actualizado correctamente.")
            return redirect(f"{reverse('admin_rbd')}?q={servicio.rbd}")
    else:
        form = AdminRbdServicioForm(instance=servicio)

    return render(
        request,
        "accounts/admin_rbd_form.html",
        {
            "form": form,
            "servicio": servicio,
        },
    )


@_admin_required
def admin_usuarios(request):
    User = get_user_model()
    usuarios = User.objects.order_by("-is_staff", "-is_active", "username")
    return render(
        request,
        "accounts/admin_user_list.html",
        {"usuarios": usuarios},
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
            if user == request.user and (not nuevo_staff or not nuevo_activo):
                form.add_error(None, "No puedes quitar tu propio acceso ADMIN.")
            elif _is_last_active_admin(user) and (not nuevo_staff or not nuevo_activo):
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
