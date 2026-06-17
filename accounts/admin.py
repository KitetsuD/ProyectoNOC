from django.contrib import admin

from .models import EnlaceOperativo, Procedimiento, SolicitudSagec, SolicitudSicret


@admin.register(Procedimiento)
class ProcedimientoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "categoria", "estado", "prioridad", "responsable", "fecha_compromiso", "activo")
    list_filter = ("tipo", "estado", "prioridad", "activo", "categoria", "responsable")
    search_fields = ("titulo", "categoria", "descripcion", "contenido", "resultado")
    readonly_fields = ("creado_en", "actualizado_en", "completado_en")
    ordering = ("estado", "fecha_compromiso", "-prioridad", "titulo")


@admin.register(SolicitudSicret)
class SolicitudSicretAdmin(admin.ModelAdmin):
    list_display = ("ticket_netcracker", "ticket_sicret", "rbd", "nombre_escuela", "estado_sicret", "estado_enlace", "descripcion_falla", "creado_por", "creado_en")
    list_filter = ("estado_sicret", "estado_enlace", "descripcion_falla", "creado_en")
    search_fields = ("ticket_netcracker", "ticket_sicret", "rbd", "nombre_escuela", "comuna", "ip_servicio", "nombre_contacto")
    readonly_fields = ("creado_en", "estado_sicret_actualizado_en")
    ordering = ("-creado_en",)


@admin.register(SolicitudSagec)
class SolicitudSagecAdmin(admin.ModelAdmin):
    list_display = ("numero_ticket", "ticket_sagec", "rbd", "fecha_caida", "motivo_ingreso", "motivo_falla_terceros", "estado_sagec", "creado_por", "creado_en")
    list_filter = ("estado_sagec", "motivo_ingreso", "motivo_falla_terceros", "fecha_caida", "creado_en")
    search_fields = ("numero_ticket", "ticket_sagec", "rbd", "id_falla_asociada", "comentario_encargado")
    readonly_fields = ("creado_en", "estado_sagec_actualizado_en")
    ordering = ("-creado_en",)


@admin.register(EnlaceOperativo)
class EnlaceOperativoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "categoria", "activo", "creado_por", "creado_en")
    list_filter = ("activo", "categoria")
    search_fields = ("titulo", "categoria", "descripcion", "url")
    readonly_fields = ("creado_en", "actualizado_en")
    ordering = ("categoria", "titulo")
