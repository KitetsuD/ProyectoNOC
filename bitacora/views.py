import calendar
import json
from datetime import date, datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.permissions import puede_gestionar_bitacora

from .forms import RegistroBitacoraForm
from .models import RegistroBitacora


CALENDAR_START = time(8, 0)
CALENDAR_END = time(18, 45)
SLOT_MINUTES = 15


def _parse_date(value):
    if not value:
        return timezone.localdate()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return timezone.localdate()


def _parse_time(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        return None


def _slots_for_day(day, exclude_id=None):
    queryset = RegistroBitacora.objects.select_related("usuario").filter(
        dia=day,
        estado=RegistroBitacora.ESTADO_AGENDADA,
    )
    if exclude_id:
        queryset = queryset.exclude(pk=exclude_id)
    registros = {
        registro.hora.strftime("%H:%M"): registro
        for registro in queryset
    }
    slots = []
    current = datetime.combine(day, CALENDAR_START)
    end = datetime.combine(day, CALENDAR_END)
    while current < end:
        label = current.strftime("%H:%M")
        registro = registros.get(label)
        slots.append(
            {
                "hora": label,
                "estado": "agendada" if registro else "disponible",
                "registro": registro,
                "url_agendar": f"{reverse('bitacora:crear')}?dia={day:%Y-%m-%d}&hora={label}",
            }
        )
        current += timedelta(minutes=SLOT_MINUTES)
    return slots


def _agenda_context(day):
    slots = _slots_for_day(day)
    ocupadas = sum(1 for slot in slots if slot["registro"])
    disponibles = len(slots) - ocupadas
    siguientes = [slot for slot in slots if not slot["registro"]][:3]
    registros_dia = [
        slot["registro"]
        for slot in slots
        if slot["registro"]
    ]
    return {
        "dia_calendario": day,
        "dia_calendario_iso": day.strftime("%Y-%m-%d"),
        "slots": slots,
        "slots_ocupados": ocupadas,
        "slots_disponibles": disponibles,
        "slots_total": len(slots),
        "siguientes_slots": siguientes,
        "registros_dia": registros_dia,
    }


def _occupied_hours(day, exclude_id=None):
    queryset = RegistroBitacora.objects.filter(
        dia=day,
        estado=RegistroBitacora.ESTADO_AGENDADA,
    )
    if exclude_id:
        queryset = queryset.exclude(pk=exclude_id)
    return list(queryset.order_by("hora").values_list("hora", flat=True))


def _month_context(selected_day):
    first_day = selected_day.replace(day=1)
    _, month_days = calendar.monthrange(first_day.year, first_day.month)
    last_day = first_day.replace(day=month_days)
    grid_start = first_day - timedelta(days=first_day.weekday())
    grid_end = grid_start + timedelta(days=41)
    registros = RegistroBitacora.objects.select_related("usuario").filter(
        dia__gte=grid_start,
        dia__lte=grid_end,
        estado=RegistroBitacora.ESTADO_AGENDADA,
    ).order_by("dia", "hora")
    registros_por_dia = {}
    for registro in registros:
        registros_por_dia.setdefault(registro.dia, []).append(registro)

    weeks = []
    current = grid_start
    total_slots = len(_slots_for_day(selected_day))
    while current <= grid_end:
        week = []
        for _ in range(7):
            day_records = registros_por_dia.get(current, [])
            has_weekend_bookings = any(registro.es_fin_de_semana for registro in day_records)
            ocupadas = len(day_records)
            disponibles = max(total_slots - ocupadas, 0)
            week.append(
                {
                    "date": current,
                    "iso": current.strftime("%Y-%m-%d"),
                    "day": current.day,
                    "is_current_month": current.month == first_day.month,
                    "is_today": current == timezone.localdate(),
                    "is_selected": current == selected_day,
                    "records": day_records,
                    "has_weekend_bookings": has_weekend_bookings,
                    "ocupadas": ocupadas,
                    "disponibles": disponibles,
                    "modal_id": f"agenda-dia-{current:%Y%m%d}",
                    "url_agendar": f"{reverse('bitacora:crear')}?dia={current:%Y-%m-%d}",
                }
            )
            current += timedelta(days=1)
        weeks.append(week)

    prev_month = first_day - timedelta(days=1)
    next_month = last_day + timedelta(days=1)
    return {
        "month_weeks": weeks,
        "weekdays": ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"],
        "month_label": first_day,
        "prev_month_iso": prev_month.strftime("%Y-%m-%d"),
        "next_month_iso": next_month.strftime("%Y-%m-%d"),
    }


@login_required
def crear_bitacora(request):
    if request.method == "POST":
        form = RegistroBitacoraForm(request.POST)
        dia_calendario = _parse_date(request.POST.get("dia"))
        if form.is_valid():
            registro = form.save(commit=False)
            registro.usuario = request.user
            try:
                registro.save()
            except IntegrityError:
                form.add_error("hora", "Ya esta agendada para esta hora.")
            else:
                messages.success(request, "Agendamiento registrado correctamente.")
                return redirect(f"{reverse('bitacora:calendario')}?dia={registro.dia:%Y-%m-%d}")
    else:
        dia_calendario = _parse_date(request.GET.get("dia"))
        hora_inicial = _parse_time(request.GET.get("hora"))
        initial = {"dia": dia_calendario, "es_fin_de_semana": dia_calendario.weekday() >= 5}
        if hora_inicial:
            initial["hora"] = hora_inicial
        form = RegistroBitacoraForm(initial=initial)

    registros = RegistroBitacora.objects.select_related("usuario").filter(
        estado=RegistroBitacora.ESTADO_AGENDADA,
    ).order_by("-dia", "-hora")[:8]
    usuario_contacto = request.user.email or request.user.username
    agenda = _agenda_context(dia_calendario)

    return render(
        request,
        "bitacora/formulario.html",
        {
            "form": form,
            "registros": registros,
            "modo_formulario": "Nueva agenda",
            "submit_label": "Agendar",
            "registro_editado": None,
            "usuario_contacto": usuario_contacto,
            **agenda,
            "horas_ocupadas_json": json.dumps([value.strftime("%H:%M") for value in _occupied_hours(dia_calendario)]),
        },
    )


@login_required
def editar_bitacora(request, registro_id):
    registro = get_object_or_404(RegistroBitacora, pk=registro_id)
    if not puede_gestionar_bitacora(request.user, registro):
        raise PermissionDenied
    if registro.estado != RegistroBitacora.ESTADO_AGENDADA:
        messages.error(request, "No se puede editar una agenda cancelada.")
        return redirect("bitacora:calendario")

    if request.method == "POST":
        form = RegistroBitacoraForm(request.POST, instance=registro)
        dia_calendario = _parse_date(request.POST.get("dia"))
        if form.is_valid():
            try:
                form.save()
            except IntegrityError:
                form.add_error("hora", "Ya esta agendada para esta hora.")
            else:
                messages.success(request, "Agendamiento actualizado correctamente.")
                return redirect(f"{reverse('bitacora:calendario')}?dia={registro.dia:%Y-%m-%d}")
    else:
        dia_calendario = registro.dia
        form = RegistroBitacoraForm(instance=registro)

    agenda = _agenda_context(dia_calendario)
    registros = RegistroBitacora.objects.select_related("usuario").filter(
        estado=RegistroBitacora.ESTADO_AGENDADA,
    ).order_by("-dia", "-hora")[:8]
    return render(
        request,
        "bitacora/formulario.html",
        {
            "form": form,
            "registros": registros,
            "modo_formulario": "Editar agenda",
            "submit_label": "Guardar cambios",
            "registro_editado": registro,
            "usuario_contacto": request.user.email or request.user.username,
            **agenda,
            "horas_ocupadas_json": json.dumps(
                [value.strftime("%H:%M") for value in _occupied_hours(dia_calendario, exclude_id=registro.pk)]
            ),
        },
    )


@login_required
def cancelar_bitacora(request, registro_id):
    registro = get_object_or_404(RegistroBitacora, pk=registro_id)
    if not puede_gestionar_bitacora(request.user, registro):
        raise PermissionDenied
    if request.method != "POST":
        return redirect(f"{reverse('bitacora:calendario')}?dia={registro.dia:%Y-%m-%d}")

    if registro.estado == RegistroBitacora.ESTADO_CANCELADA:
        messages.info(request, "La agenda ya estaba cancelada.")
    else:
        registro.estado = RegistroBitacora.ESTADO_CANCELADA
        registro.cancelado_por = request.user
        registro.cancelado_en = timezone.now()
        registro.motivo_cancelacion = (request.POST.get("motivo_cancelacion") or "").strip()
        registro.save(update_fields=["estado", "cancelado_por", "cancelado_en", "motivo_cancelacion", "actualizado_en"])
        messages.success(request, "Agendamiento cancelado correctamente.")

    return redirect(f"{reverse('bitacora:calendario')}?dia={registro.dia:%Y-%m-%d}")


@login_required
def cambiar_estado_llamada(request, registro_id):
    registro = get_object_or_404(RegistroBitacora, pk=registro_id)
    if not puede_gestionar_bitacora(request.user, registro):
        raise PermissionDenied
    if request.method != "POST":
        return redirect(f"{reverse('bitacora:calendario')}?dia={registro.dia:%Y-%m-%d}")

    registro.llamada_realizada = not registro.llamada_realizada
    registro.llamada_actualizada_en = timezone.now()
    registro.save(update_fields=["llamada_realizada", "llamada_actualizada_en", "actualizado_en"])
    estado = "realizada" if registro.llamada_realizada else "pendiente"
    messages.success(request, f"Llamada marcada como {estado}.")
    return redirect(f"{reverse('bitacora:calendario')}?dia={registro.dia:%Y-%m-%d}")


@login_required
def calendario_bitacora(request):
    dia_calendario = _parse_date(request.GET.get("dia"))
    proximos = RegistroBitacora.objects.select_related("usuario").filter(
        dia__gte=timezone.localdate(),
        estado=RegistroBitacora.ESTADO_AGENDADA,
    ).order_by("dia", "hora")[:12]
    lista_agendas = RegistroBitacora.objects.select_related("usuario").filter(
        estado=RegistroBitacora.ESTADO_AGENDADA,
    ).order_by("dia", "hora")[:40]
    agenda = _agenda_context(dia_calendario)
    month = _month_context(dia_calendario)
    return render(
        request,
        "bitacora/calendario.html",
        {"proximos": proximos, "lista_agendas": lista_agendas, **agenda, **month},
    )


@login_required
def disponibilidad_bitacora(request):
    dia = _parse_date(request.GET.get("dia"))
    excluir = request.GET.get("excluir")
    try:
        exclude_id = int(excluir) if excluir else None
    except (TypeError, ValueError):
        exclude_id = None
    ocupadas = [value.strftime("%H:%M") for value in _occupied_hours(dia, exclude_id=exclude_id)]
    return JsonResponse({"dia": dia.strftime("%Y-%m-%d"), "ocupadas": ocupadas})
