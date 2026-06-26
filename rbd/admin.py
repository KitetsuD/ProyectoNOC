from django.contrib import admin

from .models import RbdHistorial, RbdServicio


@admin.register(RbdServicio)
class RbdServicioAdmin(admin.ModelAdmin):
    list_display = (
        "rbd",
        "nombre_establecimiento",
        "tecnologia",
        "zonal",
        "jornada_categoria",
        "status_imaster",
        "dado_baja",
    )
    list_filter = ("dado_baja", "tecnologia", "zonal", "jornada_categoria", "status_imaster", "region")
    search_fields = ("rbd", "nombre_establecimiento", "codigo_servicio_oss", "ip")
    ordering = ("rbd",)


@admin.register(RbdHistorial)
class RbdHistorialAdmin(admin.ModelAdmin):
    list_display = (
        "creado_en",
        "accion",
        "rbd",
        "nombre_establecimiento",
        "usuario",
    )
    list_filter = ("accion", "creado_en")
    search_fields = ("rbd", "nombre_establecimiento", "bpi", "codigo_servicio_oss", "ip", "usuario__username")
    ordering = ("-creado_en",)
