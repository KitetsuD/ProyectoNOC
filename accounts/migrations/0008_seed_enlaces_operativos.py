from django.conf import settings
from django.db import migrations


def seed_enlaces(apps, schema_editor):
    EnlaceOperativo = apps.get_model("accounts", "EnlaceOperativo")
    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(app_label, model_name)
    user = User.objects.filter(is_staff=True, is_active=True).first() or User.objects.filter(is_active=True).first()
    if not user:
        return

    enlaces = [
        {
            "titulo": "Netcracker",
            "categoria": "Plataformas",
            "descripcion": "Acceso referencial para seguimiento de tickets NC.",
            "url": "https://www.netcracker.com",
        },
        {
            "titulo": "Huawei Enterprise",
            "categoria": "Proveedor",
            "descripcion": "Portal de referencia para documentacion y soporte Huawei.",
            "url": "https://e.huawei.com",
        },
    ]
    for data in enlaces:
        EnlaceOperativo.objects.get_or_create(
            titulo=data["titulo"],
            defaults={**data, "activo": True, "creado_por": user},
        )


def remove_seed_enlaces(apps, schema_editor):
    EnlaceOperativo = apps.get_model("accounts", "EnlaceOperativo")
    EnlaceOperativo.objects.filter(titulo__in=["Netcracker", "Huawei Enterprise"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_procedimiento_archivo_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_enlaces, remove_seed_enlaces),
    ]
