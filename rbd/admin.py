from django.contrib import admin

from .models import RbdServicio


@admin.register(RbdServicio)
class RbdServicioAdmin(admin.ModelAdmin):
    list_display = (
        "rbd",
        "nombre_establecimiento",
        "tecnologia",
        "zonal",
        "jornada_categoria",
        "status_imaster",
    )
    list_filter = ("tecnologia", "zonal", "jornada_categoria", "status_imaster", "region")
    search_fields = ("rbd", "nombre_establecimiento", "codigo_servicio_oss", "ip")
    ordering = ("rbd",)
