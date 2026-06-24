import os
import tempfile
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.db.models import Q
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from bitacora.models import RegistroBitacora
from rbd.forms import AdminRbdSearchForm, AdminRbdServicioForm
from rbd.models import RbdServicio
from rbd.services.carga_completa import export_carga_completa

from .forms import AdminCargaDatosForm, AdminTutorialDocumentoForm, AdminTutorialForm, AdminUserForm, EnlaceOperativoForm, ProcedimientoForm, SagecSolicitudForm, SicretSolicitudForm
from .models import EnlaceOperativo, Procedimiento, SolicitudSagec, SolicitudSicret
from .permissions import PERFIL_ADMIN, admin_required, es_solo_rbd, etiqueta_perfil_usuario, operador_required, perfil_usuario
from .services.tutoriales_docx import importar_tutoriales_docx


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
    if es_solo_rbd(request.user):
        return redirect("rbd:buscar")
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
        {
            "title": "Enlaces",
            "description": "Repositorio de accesos operativos a plataformas internas y proveedores.",
            "state": "Disponible",
            "url": reverse("enlaces_operativos"),
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


@operador_required
def procedimientos(request):
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
            "documentos": documentos,
            "procedimientos": pendientes,
            "completados": completados[:10],
        },
    )


@_admin_required
def admin_tutoriales(request):
    import_form = AdminTutorialDocumentoForm()
    if request.method == "POST" and request.POST.get("accion") == "importar_docx":
        form = AdminTutorialForm(initial={"activo": True})
        import_form = AdminTutorialDocumentoForm(request.POST, request.FILES)
        if import_form.is_valid():
            try:
                resultado = importar_tutoriales_docx(import_form.cleaned_data["archivo"], request.user)
            except ValueError as exc:
                import_form.add_error("archivo", str(exc))
            else:
                messages.success(
                    request,
                    f"Documento procesado: {resultado['total']} procedimientos, {resultado['creados']} nuevos y {resultado['actualizados']} actualizados.",
                )
                return redirect("admin_tutoriales")
    elif request.method == "POST":
        form = AdminTutorialForm(request.POST, request.FILES)
        if form.is_valid():
            tutorial = form.save(commit=False)
            tutorial.tipo = Procedimiento.TIPO_PROCEDIMIENTO
            tutorial.estado = Procedimiento.ESTADO_PENDIENTE
            tutorial.prioridad = Procedimiento.PRIORIDAD_ALTA
            tutorial.fecha_compromiso = None
            tutorial.resultado = ""
            tutorial.creado_por = request.user
            tutorial.actualizado_por = request.user
            tutorial.responsable = request.user
            tutorial.save()
            messages.success(request, "Procedimiento operativo cargado correctamente.")
            return redirect("admin_tutoriales")
    else:
        form = AdminTutorialForm(initial={"activo": True})

    tutoriales = Procedimiento.objects.filter(
        tipo=Procedimiento.TIPO_PROCEDIMIENTO
    ).order_by("orden", "categoria", "titulo")

    return render(
        request,
        "accounts/admin_tutoriales.html",
        {
            "form": form,
            "import_form": import_form,
            "tutoriales": tutoriales,
        },
    )


@_admin_required
def admin_tutorial_editar(request, tutorial_id):
    tutorial = get_object_or_404(
        Procedimiento,
        pk=tutorial_id,
        tipo=Procedimiento.TIPO_PROCEDIMIENTO,
    )
    if request.method == "POST":
        form = AdminTutorialForm(request.POST, request.FILES, instance=tutorial)
        if form.is_valid():
            tutorial = form.save(commit=False)
            tutorial.tipo = Procedimiento.TIPO_PROCEDIMIENTO
            tutorial.estado = Procedimiento.ESTADO_PENDIENTE
            tutorial.prioridad = Procedimiento.PRIORIDAD_ALTA
            tutorial.fecha_compromiso = None
            tutorial.resultado = ""
            tutorial.actualizado_por = request.user
            if not tutorial.responsable_id:
                tutorial.responsable = request.user
            tutorial.save()
            messages.success(request, "Procedimiento actualizado correctamente.")
            return redirect("admin_tutoriales")
    else:
        form = AdminTutorialForm(instance=tutorial)

    return render(
        request,
        "accounts/admin_tutorial_form.html",
        {
            "form": form,
            "tutorial": tutorial,
        },
    )


@_admin_required
def admin_tutoriales_documento_base(request):
    documento = Path(settings.BASE_DIR) / "docs" / "ProyectoNOC_Procedimientos_Operativos_Base.docx"
    if not documento.exists():
        messages.error(request, "El documento base de procedimientos no esta disponible.")
        return redirect("admin_tutoriales")
    return FileResponse(
        open(documento, "rb"),
        as_attachment=True,
        filename=documento.name,
    )


@operador_required
def procedimiento_archivo(request, procedimiento_id):
    procedimiento = get_object_or_404(Procedimiento, pk=procedimiento_id)
    if not request.user.is_staff and not procedimiento.activo:
        raise PermissionDenied
    if not procedimiento.archivo:
        messages.error(request, "El procedimiento no tiene archivo cargado.")
        return redirect("procedimientos")
    return FileResponse(
        procedimiento.archivo.open("rb"),
        as_attachment=False,
        filename=procedimiento.archivo.name.rsplit("/", 1)[-1],
    )


@operador_required
def enlaces_operativos(request):
    if request.method == "POST":
        if not request.user.is_staff:
            raise PermissionDenied
        form = EnlaceOperativoForm(request.POST)
        if form.is_valid():
            enlace = form.save(commit=False)
            enlace.creado_por = request.user
            enlace.save()
            messages.success(request, "Enlace operativo creado correctamente.")
            return redirect("enlaces_operativos")
    else:
        form = EnlaceOperativoForm(initial={"activo": True})

    enlaces = EnlaceOperativo.objects.all()
    if not request.user.is_staff:
        enlaces = enlaces.filter(activo=True)

    return render(
        request,
        "accounts/enlaces_operativos.html",
        {
            "form": form,
            "enlaces": enlaces,
        },
    )


@_admin_required
def enlace_operativo_toggle(request, enlace_id):
    enlace = get_object_or_404(EnlaceOperativo, pk=enlace_id)
    if request.method == "POST":
        enlace.activo = not enlace.activo
        enlace.save(update_fields=["activo", "actualizado_en"])
        estado = "publicado" if enlace.activo else "ocultado"
        messages.success(request, f"Enlace {estado}.")
    return redirect("enlaces_operativos")


@_admin_required
def enlace_operativo_eliminar(request, enlace_id):
    enlace = get_object_or_404(EnlaceOperativo, pk=enlace_id)
    if request.method == "POST":
        titulo = enlace.titulo
        enlace.delete()
        messages.success(request, f"Enlace {titulo} eliminado correctamente.")
    return redirect("enlaces_operativos")


@_admin_required
def procedimiento_toggle(request, procedimiento_id):
    procedimiento = get_object_or_404(Procedimiento, pk=procedimiento_id)
    if request.method == "POST":
        procedimiento.activo = not procedimiento.activo
        procedimiento.actualizado_por = request.user
        procedimiento.save(update_fields=["activo", "actualizado_por", "actualizado_en"])
        estado = "publicado" if procedimiento.activo else "ocultado"
        messages.success(request, f"Procedimiento {estado}.")
    return redirect("admin_tutoriales")


@operador_required
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
    total_solicitudes = solicitudes.count()

    return render(
        request,
        "accounts/sicret.html",
        {
            "form": form,
            "total_solicitudes": total_solicitudes,
        },
    )


@operador_required
def sicret_tickets(request):
    solicitudes_base = SolicitudSicret.objects.select_related(
        "creado_por",
        "estado_sicret_actualizado_por",
    ).exclude(estado_sicret=SolicitudSicret.ESTADO_SICRET_CERRADO)

    query = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip()
    estados_operativos = [
        (valor, etiqueta)
        for valor, etiqueta in SolicitudSicret.ESTADOS_SICRET
        if valor != SolicitudSicret.ESTADO_SICRET_CERRADO
    ]
    estados_validos = {valor for valor, _ in estados_operativos}

    if query:
        solicitudes_base = solicitudes_base.filter(
            Q(ticket_netcracker__icontains=query)
            | Q(ticket_sicret__icontains=query)
            | Q(rbd__icontains=query)
            | Q(nombre_escuela__icontains=query)
            | Q(ip_servicio__icontains=query)
            | Q(instancia__icontains=query)
            | Q(comentario_encargado__icontains=query)
        )

    resumen_estados = [
        {
            "valor": valor,
            "etiqueta": etiqueta,
            "total": solicitudes_base.filter(estado_sicret=valor).count(),
        }
        for valor, etiqueta in estados_operativos
    ]

    solicitudes = solicitudes_base
    if estado in estados_validos:
        solicitudes = solicitudes.filter(estado_sicret=estado)
    else:
        estado = ""

    total = solicitudes.count()

    return render(
        request,
        "accounts/sicret_tickets.html",
        {
            "solicitudes": solicitudes[:80],
            "total_solicitudes": total,
            "estados_sicret": SolicitudSicret.ESTADOS_SICRET,
            "estados_sicret_filtro": estados_operativos,
            "resumen_estados": resumen_estados,
            "query": query,
            "estado_actual": estado,
        },
    )


@_admin_required
def admin_historial_operativo(request):
    query = (request.GET.get("q") or "").strip()

    sicret_cerrados = SolicitudSicret.objects.select_related(
        "creado_por",
        "estado_sicret_actualizado_por",
    ).filter(estado_sicret=SolicitudSicret.ESTADO_SICRET_CERRADO)

    llamadas_realizadas = RegistroBitacora.objects.select_related("usuario").filter(
        llamada_realizada=True,
    )

    sagec_cerrados = SolicitudSagec.objects.select_related(
        "creado_por",
        "estado_sagec_actualizado_por",
    ).filter(estado_sagec=SolicitudSagec.ESTADO_SAGEC_CERRADO)

    if query:
        sicret_cerrados = sicret_cerrados.filter(
            Q(ticket_netcracker__icontains=query)
            | Q(ticket_sicret__icontains=query)
            | Q(rbd__icontains=query)
            | Q(nombre_escuela__icontains=query)
            | Q(ip_servicio__icontains=query)
            | Q(comentario_encargado__icontains=query)
        )
        llamadas_realizadas = llamadas_realizadas.filter(
            Q(ticket__icontains=query)
            | Q(rbd__icontains=query)
            | Q(vinculo_ticket__icontains=query)
            | Q(usuario__username__icontains=query)
        )
        sagec_cerrados = sagec_cerrados.filter(
            Q(numero_ticket__icontains=query)
            | Q(ticket_sagec__icontains=query)
            | Q(rbd__icontains=query)
            | Q(id_falla_asociada__icontains=query)
            | Q(comentario_encargado__icontains=query)
        )

    total_sicret = sicret_cerrados.count()
    total_llamadas = llamadas_realizadas.count()
    total_sagec = sagec_cerrados.count()

    return render(
        request,
        "accounts/admin_historial_operativo.html",
        {
            "query": query,
            "sicret_cerrados": sicret_cerrados.order_by(
                "-estado_sicret_actualizado_en",
                "-creado_en",
            )[:120],
            "llamadas_realizadas": llamadas_realizadas.order_by(
                "-llamada_actualizada_en",
                "-dia",
                "-hora",
            )[:120],
            "sagec_cerrados": sagec_cerrados.order_by(
                "-estado_sagec_actualizado_en",
                "-creado_en",
            )[:120],
            "total_sicret": total_sicret,
            "total_llamadas": total_llamadas,
            "total_sagec": total_sagec,
        },
    )


@operador_required
def sicret_ticket_estado(request, solicitud_id):
    if request.method != "POST":
        return redirect("sicret_tickets")

    solicitud = get_object_or_404(SolicitudSicret, pk=solicitud_id)

    estado = (request.POST.get("estado_sicret") or "").strip()
    estados_validos = {valor for valor, _ in SolicitudSicret.ESTADOS_SICRET}
    if estado not in estados_validos:
        messages.error(request, "Estado SICRET no valido.")
        return redirect("sicret_tickets")

    update_fields = [
        "estado_sicret",
        "estado_sicret_actualizado_por",
        "estado_sicret_actualizado_en",
    ]

    solicitud.estado_sicret = estado
    if "ticket_sicret" in request.POST:
        solicitud.ticket_sicret = (request.POST.get("ticket_sicret") or "").strip()
        update_fields.append("ticket_sicret")
    if "comentario_encargado" in request.POST:
        solicitud.comentario_encargado = (request.POST.get("comentario_encargado") or "").strip()
        update_fields.append("comentario_encargado")
    solicitud.estado_sicret_actualizado_por = request.user
    solicitud.estado_sicret_actualizado_en = timezone.now()
    solicitud.save(update_fields=update_fields)
    messages.success(request, f"Ticket {solicitud.ticket_netcracker} actualizado.")
    return redirect("sicret_tickets")


@operador_required
def sicret_rbd_info(request):
    rbd = (request.GET.get("rbd") or "").strip()
    if not rbd:
        return JsonResponse(
            {"encontrado": False, "mensaje": "Ingresa un RBD."},
            status=400,
        )
    if not rbd.isdigit():
        return JsonResponse(
            {"encontrado": False, "mensaje": "El RBD debe ser numerico."},
            status=400,
        )

    servicio = RbdServicio.objects.filter(rbd=int(rbd)).first()
    if not servicio:
        return JsonResponse(
            {"encontrado": False, "mensaje": "No se encontro informacion para ese RBD."},
            status=404,
        )

    return JsonResponse(
        {
            "encontrado": True,
            "rbd": str(servicio.rbd),
            "zona": servicio.zona or servicio.zonal or "",
            "comuna": servicio.localidad or "",
            "nombre_escuela": servicio.nombre_establecimiento or "",
            "direccion": servicio.direccion or "",
            "ip_servicio": servicio.ip or "",
            "instancia": (
                servicio.codigo_servicio_oss
                or servicio.codigo_servicio_ncc
                or servicio.identificador_tecnico
            ),
        }
    )


@operador_required
def sagec(request):
    if request.method == "POST":
        form = SagecSolicitudForm(request.POST)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.creado_por = request.user
            solicitud.save()
            messages.success(request, "Solicitud SAGEC registrada correctamente.")
            return redirect("sagec")
    else:
        form = SagecSolicitudForm()

    total_solicitudes = SolicitudSagec.objects.count()

    return render(
        request,
        "accounts/sagec.html",
        {
            "form": form,
            "total_solicitudes": total_solicitudes,
        },
    )


@operador_required
def sagec_tickets(request):
    solicitudes_base = SolicitudSagec.objects.select_related(
        "creado_por",
        "estado_sagec_actualizado_por",
    ).exclude(estado_sagec=SolicitudSagec.ESTADO_SAGEC_CERRADO)

    query = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip()
    estados_operativos = [
        (valor, etiqueta)
        for valor, etiqueta in SolicitudSagec.ESTADOS_SAGEC
        if valor != SolicitudSagec.ESTADO_SAGEC_CERRADO
    ]
    estados_validos = {valor for valor, _ in estados_operativos}

    if query:
        solicitudes_base = solicitudes_base.filter(
            Q(numero_ticket__icontains=query)
            | Q(ticket_sagec__icontains=query)
            | Q(rbd__icontains=query)
            | Q(id_falla_asociada__icontains=query)
            | Q(comentario_encargado__icontains=query)
        )

    resumen_estados = [
        {
            "valor": valor,
            "etiqueta": etiqueta,
            "total": solicitudes_base.filter(estado_sagec=valor).count(),
        }
        for valor, etiqueta in estados_operativos
    ]

    solicitudes = solicitudes_base
    if estado in estados_validos:
        solicitudes = solicitudes.filter(estado_sagec=estado)
    else:
        estado = ""

    total = solicitudes.count()

    return render(
        request,
        "accounts/sagec_tickets.html",
        {
            "solicitudes": solicitudes[:80],
            "total_solicitudes": total,
            "estados_sagec": SolicitudSagec.ESTADOS_SAGEC,
            "estados_sagec_filtro": estados_operativos,
            "resumen_estados": resumen_estados,
            "query": query,
            "estado_actual": estado,
        },
    )


@operador_required
def sagec_ticket_estado(request, solicitud_id):
    if request.method != "POST":
        return redirect("sagec_tickets")

    solicitud = get_object_or_404(SolicitudSagec, pk=solicitud_id)

    estado = (request.POST.get("estado_sagec") or "").strip()
    estados_validos = {valor for valor, _ in SolicitudSagec.ESTADOS_SAGEC}
    if estado not in estados_validos:
        messages.error(request, "Estado SAGEC no valido.")
        return redirect("sagec_tickets")

    update_fields = [
        "estado_sagec",
        "estado_sagec_actualizado_por",
        "estado_sagec_actualizado_en",
    ]

    solicitud.estado_sagec = estado
    if "ticket_sagec" in request.POST:
        solicitud.ticket_sagec = (request.POST.get("ticket_sagec") or "").strip()
        update_fields.append("ticket_sagec")
    if "comentario_encargado" in request.POST:
        solicitud.comentario_encargado = (request.POST.get("comentario_encargado") or "").strip()
        update_fields.append("comentario_encargado")
    solicitud.estado_sagec_actualizado_por = request.user
    solicitud.estado_sagec_actualizado_en = timezone.now()
    solicitud.save(update_fields=update_fields)
    messages.success(request, f"Ticket {solicitud.numero_ticket} actualizado.")
    return redirect("sagec_tickets")


@operador_required
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
            resultados = RbdServicio.objects.filter(Q(bpi__icontains=termino)).order_by("rbd")
            if termino.isdigit():
                resultados = RbdServicio.objects.filter(
                    Q(rbd=int(termino)) | Q(bpi__icontains=termino)
                ).order_by("rbd")
            titulo_resultados = f'Resultados para "{termino}"'

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
def admin_rbd_eliminar(request, servicio_id):
    servicio = get_object_or_404(RbdServicio, pk=servicio_id)
    if request.method != "POST":
        messages.error(request, "La eliminacion de un RBD debe realizarse desde el formulario de confirmacion.")
        return redirect(f"{reverse('admin_rbd')}?q={servicio.rbd}")

    rbd = servicio.rbd
    nombre = servicio.nombre_establecimiento or "Sin nombre"
    contactos = servicio.contactos.count()
    servicio.delete()
    detalle_contactos = f" y {contactos} contacto(s)" if contactos else ""
    messages.success(request, f"RBD {rbd} - {nombre} eliminado correctamente{detalle_contactos}.")
    return redirect("admin_rbd")


@_admin_required
def admin_usuarios(request):
    User = get_user_model()
    usuarios = list(User.objects.prefetch_related("groups").order_by("-is_staff", "-is_active", "username"))
    for usuario in usuarios:
        usuario.perfil_valor = perfil_usuario(usuario)
        usuario.perfil_etiqueta = etiqueta_perfil_usuario(usuario)
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
            nuevo_staff = form.cleaned_data["perfil"] == PERFIL_ADMIN
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
