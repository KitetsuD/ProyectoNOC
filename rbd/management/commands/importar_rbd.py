import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from rbd.models import RbdServicio


class Command(BaseCommand):
    help = "Importa registros RBD desde un JSON normalizado."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=str(Path(__file__).resolve().parents[2] / "data" / "rbd_servicios.json"),
            help="Ruta al archivo JSON normalizado.",
        )

    def handle(self, *args, **options):
        source = Path(options["path"])
        if not source.exists():
            raise CommandError(f"No existe el archivo de datos: {source}")

        with source.open("r", encoding="utf-8") as file:
            records = json.load(file)

        created = 0
        updated = 0

        with transaction.atomic():
            for item in records:
                defaults = {
                    "nombre_establecimiento": item.get("nombre_establecimiento", ""),
                    "direccion": item.get("direccion", ""),
                    "localidad": item.get("localidad", ""),
                    "region": item.get("region", ""),
                    "lat": item.get("lat"),
                    "long": item.get("long"),
                    "zona": item.get("zona", ""),
                    "zonal": item.get("zonal", ""),
                    "tecnologia": item.get("tecnologia", ""),
                    "tipo": item.get("tipo", ""),
                    "status_imaster": item.get("status_imaster", ""),
                    "fiscalizacion": item.get("fiscalizacion", ""),
                    "vigencia": item.get("vigencia", ""),
                    "matricula": item.get("matricula", ""),
                    "tipo_ont": item.get("tipo_ont", ""),
                    "puerta": item.get("puerta", ""),
                    "nodo": item.get("nodo", ""),
                    "bw_nacional": item.get("bw_nacional"),
                    "bw_internacional": item.get("bw_internacional"),
                    "bw": item.get("bw"),
                    "fw_usg": item.get("fw_usg", ""),
                    "serie_usg": item.get("serie_usg", ""),
                    "codigo_servicio_ncc": item.get("codigo_servicio_ncc", ""),
                    "vlan": item.get("vlan", ""),
                    "codigo_servicio_oss": item.get("codigo_servicio_oss", ""),
                    "ip": item.get("ip", ""),
                    "dependencia_mpls": item.get("dependencia_mpls", ""),
                    "por": item.get("por", ""),
                    "ont": item.get("ont", ""),
                    "tiene_rfs": item.get("tiene_rfs", ""),
                    "rfs": item.get("rfs", ""),
                    "caja": item.get("caja", ""),
                    "fil": item.get("fil", ""),
                    "servicio_existente_oss": item.get("servicio_existente_oss", ""),
                    "tiene_ov": item.get("tiene_ov", ""),
                    "orden_venta": item.get("orden_venta", ""),
                    "estado_ov": item.get("estado_ov", ""),
                    "bpi": item.get("bpi", ""),
                    "datos": item.get("datos", {}),
                }
                _, was_created = RbdServicio.objects.update_or_create(
                    rbd=item["rbd"],
                    defaults=defaults,
                )
                created += int(was_created)
                updated += int(not was_created)

        self.stdout.write(self.style.SUCCESS(f"Importados {created} nuevos y {updated} actualizados."))
