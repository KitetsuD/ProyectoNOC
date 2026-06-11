from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from rbd.services.carga_completa import export_carga_completa


class Command(BaseCommand):
    help = "Exporta el Excel maestro completo de ProyectoNOC."

    def add_arguments(self, parser):
        parser.add_argument("--path", required=True, help="Ruta de salida del Excel maestro.")
        parser.add_argument(
            "--empty",
            action="store_true",
            help="Genera solo la plantilla con encabezados, sin datos.",
        )

    def handle(self, *args, **options):
        target = Path(options["path"])
        try:
            summary = export_carga_completa(target, include_data=not options["empty"])
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Excel maestro generado: "
                f"{summary['path']} "
                f"({summary['servicios']} servicios, {summary['contactos']} contactos)."
            )
        )
