from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.permissions import es_solo_rbd

from .forms import RbdSearchForm
from .models import RbdContacto, RbdServicio


def _display(value, default="Sin informacion"):
    if value is None:
        return default
    if isinstance(value, str):
        value = value.strip()
        return value or default
    return value


def _decimal(value, digits=5):
    if value is None:
        return "Sin informacion"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _display(value)
    if number.is_integer():
        return str(int(number))
    text = f"{number:.{digits}f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def _speed(value):
    if value is None:
        return "Sin informacion"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _display(value)
    if number.is_integer():
        return str(int(number))
    return str(number).replace(".", ",")


def _item(label, value):
    return {"label": label, "value": _display(value)}


def _metric(label, value):
    return {"label": label, "value": value}


def _colegio_especial(servicio):
    nombre = (servicio.nombre_establecimiento or "").upper()
    return "SI" if "ESPECIAL" in nombre else "NO"


def _jornada_clase(servicio):
    categoria = (servicio.jornada_categoria or "").strip().lower()[:1]
    if categoria in {"a", "b", "c", "d", "e"}:
        return f"jornada-{categoria}"
    return ""


def _zona_corta(zona):
    zona = str(zona or "").strip().upper()
    if zona.startswith("ZONA"):
        return f"Z{zona.replace('ZONA', '', 1).strip()}"
    return zona or "Z0"


def _plain(value, default="0"):
    if value is None:
        return default
    value = str(value).strip()
    return value or default


def _copy_value(value):
    if value is None:
        return ""
    value = str(value).strip()
    if value.lower() in {"0", "0.0", "0,0", "none", "null"}:
        return ""
    return value


def _rbd_zona_tecnologia(servicio):
    zona = _copy_value(servicio.zona)
    tecnologia = _copy_value(servicio.tecnologia or servicio.tipo)
    tecnologia_corta = _copy_value(servicio.tecnologia_corta)
    if not zona or not tecnologia or tecnologia_corta == "TEC":
        return ""
    return f"RBD_{servicio.rbd}_{_zona_corta(zona)}_{tecnologia_corta}"


def _contact_copy_text(contacto, orden):
    rows = [
        (f"NOMBRE CT{orden}", _copy_value(contacto.get("nombre"))),
        (f"TELEFONO CT{orden}", _copy_value(contacto.get("telefono"))),
        (f"CELULAR CT{orden}", _copy_value(contacto.get("celular"))),
        (f"MAIL CT{orden}", _copy_value(contacto.get("email"))),
        (f"CARGO CT{orden}", _copy_value(contacto.get("cargo"))),
    ]
    return "\n".join(f"{label}\t{value}" for label, value in rows if value)


def _empty_contact(orden):
    contacto = {
        "orden": orden,
        "role": f"Contacto {orden}",
        "nombre": "",
        "telefono": "",
        "celular": "",
        "email": "",
        "cargo": "",
        "items": [
            _item("Nombre", ""),
            _item("Telefono", ""),
            _item("Celular", ""),
            _item("Email", ""),
            _item("Cargo", ""),
        ],
    }
    contacto["copy_text"] = _contact_copy_text(contacto, orden)
    return contacto


def _contact_from_model(contacto, orden):
    if not contacto:
        return _empty_contact(orden)
    contacto_data = {
        "orden": orden,
        "role": f"Contacto {orden}",
        "nombre": contacto.nombre,
        "telefono": contacto.telefono,
        "celular": contacto.celular,
        "email": contacto.email,
        "cargo": contacto.cargo,
        "items": [
            _item("Nombre", contacto.nombre),
            _item("Telefono", contacto.telefono),
            _item("Celular", contacto.celular),
            _item("Email", contacto.email),
            _item("Cargo", contacto.cargo),
        ],
    }
    contacto_data["copy_text"] = _contact_copy_text(contacto_data, orden)
    return contacto_data


def _contacts_for_service(servicio):
    contactos = {contacto.orden: contacto for contacto in servicio.contactos.all()}
    return [_contact_from_model(contactos.get(orden), orden) for orden in range(1, 5)]


def _full_copy_rows(servicio, contactos):
    def append_if_value(rows, label, value):
        value = _copy_value(value)
        if value:
            rows.append((label, value))

    def append_gap(rows):
        if rows and rows[-1] != ("", ""):
            rows.append(("", ""))

    rows = []
    append_if_value(rows, "RBD/ZONA/TECNOLOGIA", _rbd_zona_tecnologia(servicio))
    append_if_value(rows, "NOMBRE", servicio.nombre_establecimiento)
    append_if_value(rows, "DIRECCION", servicio.direccion)
    append_if_value(rows, "COMUNA", servicio.localidad)
    append_if_value(rows, "REGION", servicio.region)
    append_gap(rows)
    append_if_value(rows, "MOTIVO", "SIN SERVICIO")

    for contacto in contactos:
        contacto_rows = []
        append_if_value(contacto_rows, f"NOMBRE CT{contacto['orden']}", contacto["nombre"])
        append_if_value(contacto_rows, f"TELEFONO CT{contacto['orden']}", contacto["telefono"])
        append_if_value(contacto_rows, f"CELULAR CT{contacto['orden']}", contacto["celular"])
        append_if_value(contacto_rows, f"MAIL CT{contacto['orden']}", contacto["email"])
        append_if_value(contacto_rows, f"CARGO CT{contacto['orden']}", contacto["cargo"])
        if contacto_rows:
            append_gap(rows)
            rows.extend(contacto_rows)

    if rows and rows[-1] == ("", ""):
        rows.pop()
    return [{"label": label, "value": value} for label, value in rows]


def _build_detail(servicio):
    contactos = _contacts_for_service(servicio)
    colegio = [
        _item("RBD", servicio.rbd),
        _item("Nombre", servicio.nombre_establecimiento),
        _item("Direccion", servicio.direccion),
        _item("Localidad", servicio.localidad),
        _item("Region", servicio.region),
        _item("Zona", servicio.zona),
        _item("Zonal", servicio.zonal),
        _item("Matricula", servicio.matricula),
        _metric("Latitud", _decimal(servicio.lat)),
        _metric("Longitud", _decimal(servicio.long)),
        _item("Colegio Especial", _colegio_especial(servicio)),
    ]

    servicio_items = [
        _item("Tecnologia Actual", servicio.tecnologia),
        _item("Tipo Tecnologia", servicio.tipo),
        _item("Nodo", servicio.nodo),
        _item("VLAN", servicio.vlan),
        _item("Puerta", servicio.puerta),
        _item("Dependencia MPLS", servicio.dependencia_mpls),
        _metric("BW Nacional", _speed(servicio.bw_nacional)),
        _metric("BW Internacional", _speed(servicio.bw_internacional)),
        _metric("BW bajada", _speed(servicio.bw)),
        _item("Codigo OSS", servicio.codigo_servicio_oss),
    ]
    servicio_texto = "\n".join(f"{item['label']}\t{item['value']}" for item in servicio_items)
    copiar_completo = _full_copy_rows(servicio, contactos)

    return {
        "colegio": colegio,
        "servicio": servicio_items,
        "servicio_texto": servicio_texto,
        "contactos": contactos,
        "jornada_clase": _jornada_clase(servicio),
        "copiar_completo": copiar_completo,
        "copiar_completo_texto": "\n".join(f"{row['label']}\t{row['value']}" for row in copiar_completo),
    }


def _guardar_contactos(request, servicio):
    campos = ("nombre", "telefono", "celular", "email", "cargo")
    contactos = []
    errores = []

    for orden in range(1, 5):
        defaults = {
            campo: (request.POST.get(f"contacto_{orden}_{campo}") or "").strip()
            for campo in campos
        }
        email = defaults["email"]
        if email:
            try:
                validate_email(email)
            except ValidationError:
                errores.append(f"Contacto {orden}: ingresa un email valido.")
        contactos.append((orden, defaults))

    if errores:
        return errores

    with transaction.atomic():
        for orden, defaults in contactos:
            tiene_datos = any(defaults[campo] for campo in campos)
            if not tiene_datos:
                RbdContacto.objects.filter(servicio=servicio, orden=orden).delete()
                continue

            defaults["fuente"] = "Edicion manual"
            RbdContacto.objects.update_or_create(
                servicio=servicio,
                orden=orden,
                defaults=defaults,
            )

    return []


@login_required
def buscar_rbd(request):
    if request.method == "POST" and request.POST.get("accion") == "guardar_contactos":
        servicio = get_object_or_404(RbdServicio, rbd=request.POST.get("rbd"))
        errores = _guardar_contactos(request, servicio)
        if errores:
            for error in errores:
                messages.error(request, error)
        else:
            messages.success(request, "Contactos actualizados correctamente.")
        return redirect(f"{reverse('rbd:buscar')}?rbd={servicio.rbd}#contactos")

    raw_rbd = request.GET.get("rbd") or request.GET.get("q") or ""
    form = RbdSearchForm(request.GET or None)
    resultado = None
    detail = {
        "colegio": [],
        "servicio": [],
        "servicio_texto": "",
        "contactos": [_empty_contact(1), _empty_contact(2), _empty_contact(3), _empty_contact(4)],
        "jornada_clase": "",
        "copiar_completo": [],
        "copiar_completo_texto": "",
    }

    if raw_rbd and form.is_valid():
        resultado = RbdServicio.objects.filter(rbd=form.cleaned_data["rbd"], dado_baja=False).first()
        if resultado:
            detail = _build_detail(resultado)

    context = {
        "base_template": "accounts/base_rbd_only.html" if es_solo_rbd(request.user) else "accounts/base_panel.html",
        "form": form,
        "resultado": resultado,
        "busqueda_realizada": bool(raw_rbd),
        "rbd_consultado": raw_rbd,
        "total_rbd": RbdServicio.objects.filter(dado_baja=False).count(),
        "puede_editar_contactos": True,
        **detail,
    }
    return render(request, "rbd/buscar.html", context)


@login_required
def servicios_baja(request):
    termino = (request.GET.get("q") or "").strip()
    servicios = RbdServicio.objects.filter(dado_baja=True).select_related("baja_por").order_by("-baja_fecha", "rbd")
    if termino:
        filtros = (
            Q(nombre_establecimiento__icontains=termino)
            | Q(bpi__icontains=termino)
            | Q(codigo_servicio_oss__icontains=termino)
            | Q(ip__icontains=termino)
        )
        if termino.isdigit():
            filtros |= Q(rbd=int(termino))
        servicios = servicios.filter(filtros)

    context = {
        "base_template": "accounts/base_rbd_only.html" if es_solo_rbd(request.user) else "accounts/base_panel.html",
        "servicios": servicios[:300],
        "termino": termino,
        "total_bajas": RbdServicio.objects.filter(dado_baja=True).count(),
        "total_resultados": servicios.count(),
    }
    return render(request, "rbd/bajas.html", context)
