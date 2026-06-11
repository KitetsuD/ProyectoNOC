from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from rbd.services.carga_completa import import_carga_completa


class Command(BaseCommand):
    help = "Importa el Excel maestro completo de ProyectoNOC."

    def add_arguments(self, parser):
        parser.add_argument("--path", required=True, help="Ruta al Excel maestro completo.")

    def handle(self, *args, **options):
        source = Path(options["path"])
        if not source.exists():
            raise CommandError(f"No existe el archivo: {source}")

        try:
            summary = import_carga_completa(source)
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Carga completa procesada: "
                f"{summary['created']} servicios nuevos, "
                f"{summary['updated']} servicios actualizados, "
                f"{summary['contacts']} contactos cargados. "
                f"Servicios omitidos: {summary['skipped_services']}. "
                f"Contactos omitidos: {summary['skipped_contacts']}."
            )
        )
