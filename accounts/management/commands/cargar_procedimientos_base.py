from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from accounts.models import Procedimiento


PROCEDIMIENTOS = [
    {
        "titulo": "Protocolo de escalamiento GTD - Telnext",
        "categoria": "Escalamiento proveedor",
        "descripcion": "Atencion y escalamiento de incidentes Subtel con proveedor Telnext.",
        "contenido": (
            "1. Detectar alarma en Huawei y confirmar incidente.\n"
            "2. Abrir ticket interno en Netcracker con datos del sitio.\n"
            "3. Contactar al establecimiento para validar energia, equipos y estado local.\n"
            "4. Enviar correo formal a Serviciotecnico@Telnext.cl con la mayor informacion posible.\n"
            "5. Llamar al soporte indicado en el protocolo y usar WhatsApp si no contestan.\n"
            "6. Enviar planilla de casos pendientes dos veces al dia, a las 10:00 y 15:00.\n"
            "7. Cerrar solo cuando exista respuesta del proveedor, validacion en Huawei y validacion con cliente."
        ),
        "enlace": "/static/accounts/procedimientos/telnext_protocolo_escalamiento.pdf",
        "orden": 10,
    },
    {
        "titulo": "Ingreso de ticket GTD / Telnext",
        "categoria": "Ticket proveedor",
        "descripcion": "Guia rapida para crear, escalar y cerrar tickets asociados a Telnext.",
        "contenido": (
            "1. Detectar alerta de caida en Huawei.\n"
            "2. Validar el estado de conexion en el panel Telnext.\n"
            "3. Crear ticket interno NCC al confirmar la caida.\n"
            "4. Contactar al cliente para validar energia y estado de equipos.\n"
            "5. Enviar correo de escalamiento a Telnext.\n"
            "6. Llamar al +56 9 4282 5463 y usar WhatsApp al mismo numero si no responden.\n"
            "7. Registrar solucion, validar recuperacion y cerrar ticket."
        ),
        "enlace": "/static/accounts/procedimientos/telnext_ingreso_ticket.pdf",
        "orden": 20,
    },
    {
        "titulo": "Procedimiento Monitoreo Subtel 2030",
        "categoria": "Monitoreo",
        "descripcion": "Norma el proceso de monitoreo, contacto, pausa, cierre y escalamiento para cliente Subtel.",
        "contenido": (
            "1. Revisar al inicio de jornada los tickets asignados a mi.\n"
            "2. Registrar cada interaccion en la plataforma, aunque el cliente no conteste.\n"
            "3. Ejecutar intentos de contacto por tramo: AM 09:00-11:30, almuerzo 11:31-14:30 y PM 14:31-18:30.\n"
            "4. Si el enlace esta operativo y no hay contacto, cerrar con pruebas adjuntas.\n"
            "5. Si el enlace esta caido y no hay contacto tras los tramos definidos, derivar a terreno o proveedor.\n"
            "6. Para fallas masivas, consultar con COR, crear ticket por colegio afectado y dejar tickets pausados.\n"
            "7. Al finalizar turno, desasignar tickets pendientes."
        ),
        "enlace": "/static/accounts/procedimientos/subtel_monitoreo_clientes.pdf",
        "orden": 30,
    },
    {
        "titulo": "Monitoreo Cliente Subtel SAGEC",
        "categoria": "SAGEC",
        "descripcion": "Creacion de contingencias SAGEC segun gestion y causa raiz informada en Netcracker.",
        "contenido": (
            "1. Identificar numero de ticket en Netcracker.\n"
            "2. Revisar interacciones con cliente para asignar el tipo de contingencia.\n"
            "3. Obtener datos desde Power BI o detalle de indisponibilidad: fecha, hora de inicio y hora de termino.\n"
            "4. Clasificar la contingencia como especifica interna, especifica externa o zonal.\n"
            "5. Enviar correo al cliente indicando el motivo de la contingencia.\n"
            "6. Si no existe informacion del cliente y el servicio retorna sin intervencion, registrar como contingencia especifica interna.\n"
            "7. Usar las plantillas del documento para documentar y comunicar cada evento."
        ),
        "enlace": "/static/accounts/procedimientos/sagec_monitoreo_clientes.pdf",
        "orden": 40,
    },
    {
        "titulo": "Protocolo de escalamiento GTD - Electrored",
        "categoria": "Escalamiento proveedor",
        "descripcion": "Escalamiento de incidentes Subtel asociados a servicios provistos por Electrored.",
        "contenido": (
            "1. Detectar alarma en Huawei y validar estado en panel Electrored.\n"
            "2. Contactar al establecimiento para validar energia, cableado y equipos.\n"
            "3. Enviar correo formal a soporte@electrored.net con los datos completos del sitio.\n"
            "4. Llamar a soporte Electrored en horario lunes a viernes 08:00-18:00.\n"
            "5. Si no responden, enviar WhatsApp al +56 9 9328 6719.\n"
            "6. Esperar respuesta de Electrored y registrar resultado en ticket interno.\n"
            "7. Solicitar formulario de atencion posterior a visita o atencion del proveedor."
        ),
        "enlace": "/static/accounts/procedimientos/electrored_protocolo_escalamiento.pdf",
        "orden": 50,
    },
    {
        "titulo": "Protocolo de escalamiento GTD - Teledata",
        "categoria": "Escalamiento proveedor",
        "descripcion": "Escalamiento de incidentes Subtel asociados a proveedor Teledata.",
        "contenido": (
            "1. Detectar alarma en Huawei y abrir registro interno una vez confirmado el incidente.\n"
            "2. Contactar al establecimiento para validar energia y estado de equipos.\n"
            "3. Enviar correo formal a soporte@teledata.cl con la informacion del sitio.\n"
            "4. Llamar a soporte proveedor si no existe respuesta por correo.\n"
            "5. Usar WhatsApp segun protocolo: +56 9 9172 4177 o +56 9 8158 5538 si no contestan.\n"
            "6. Registrar respuesta, validar recuperacion y cerrar ticket.\n"
            "7. Solicitar formulario de atencion no mas tarde de 24 horas cuando aplique visita o atencion."
        ),
        "enlace": "/static/accounts/procedimientos/teledata_protocolo_escalamiento.pdf",
        "orden": 60,
    },
    {
        "titulo": "Soporte tecnico y red de servicios Mundo",
        "categoria": "Soporte proveedor",
        "descripcion": "Estandariza la comunicacion y resolucion de incidencias con Mundo Empresas.",
        "contenido": (
            "1. Centralizar el escalamiento hacia mesa de Soporte Mundo Empresas.\n"
            "2. Contactar por telefono al 600 9100 200 opcion 2.\n"
            "3. Usar WhatsApp +1 231 570 6871 como soporte digital.\n"
            "4. Enviar antecedentes a soporte.empresas@mundotelecomunicaciones.cl.\n"
            "5. Entregar datos del contacto tecnico: persona que reporta, telefono, movil, correo y horarios de disponibilidad.\n"
            "6. Mantener seguimiento hasta cierre autorizado por contacto tecnico."
        ),
        "enlace": "/static/accounts/procedimientos/mundo_soporte_tecnico_red.pdf",
        "orden": 70,
    },
]


class Command(BaseCommand):
    help = "Carga o actualiza los procedimientos operativos base del proyecto."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="nocadmin")

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        user = User.objects.filter(username=username).first()
        if not user:
            user = User.objects.filter(is_staff=True, is_active=True).order_by("id").first()
        if not user:
            raise CommandError("No existe un usuario staff para asignar los procedimientos.")

        creados = 0
        actualizados = 0
        for item in PROCEDIMIENTOS:
            defaults = {
                **item,
                "tipo": Procedimiento.TIPO_PROCEDIMIENTO,
                "estado": Procedimiento.ESTADO_PENDIENTE,
                "prioridad": Procedimiento.PRIORIDAD_ALTA,
                "fecha_compromiso": None,
                "resultado": "",
                "activo": True,
                "creado_por": user,
                "responsable": user,
                "actualizado_por": user,
            }
            procedimiento, created = Procedimiento.objects.update_or_create(
                titulo=item["titulo"],
                defaults=defaults,
            )
            if created:
                creados += 1
            else:
                actualizados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Procedimientos cargados. Creados: {creados}. Actualizados: {actualizados}."
            )
        )
