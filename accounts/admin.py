from django.contrib import admin

from .models import Procedimiento, SolicitudSicret


@admin.register(Procedimiento)
class ProcedimientoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "categoria", "estado", "prioridad", "responsable", "fecha_compromiso", "activo")
    list_filter = ("tipo", "estado", "prioridad", "activo", "categoria", "responsable")
    search_fields = ("titulo", "categoria", "descripcion", "contenido", "resultado")
    readonly_fields = ("creado_en", "actualizado_en", "completado_en")
    ordering = ("estado", "fecha_compromiso", "-prioridad", "titulo")


@admin.register(SolicitudSicret)
class SolicitudSicretAdmin(admin.ModelAdmin):
    list_display = ("ticket_netcracker", "rbd", "nombre_escuela", "estado_sicret", "estado_enlace", "descripcion_falla", "creado_por", "creado_en")
    list_filter = ("estado_sicret", "estado_enlace", "descripcion_falla", "creado_en")
    search_fields = ("ticket_netcracker", "rbd", "nombre_escuela", "comuna", "ip_servicio", "nombre_contacto")
    readonly_fields = ("creado_en", "estado_sicret_actualizado_en")
    ordering = ("-creado_en",)
