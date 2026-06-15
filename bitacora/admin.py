from django.contrib import admin

from .models import RegistroBitacora


@admin.register(RegistroBitacora)
class RegistroBitacoraAdmin(admin.ModelAdmin):
    list_display = ("ticket", "rbd", "dia", "hora", "estado", "llamada_realizada", "es_fin_de_semana", "usuario", "creado_en")
    list_filter = ("estado", "llamada_realizada", "dia", "es_fin_de_semana", "usuario")
    search_fields = ("ticket", "rbd", "vinculo_ticket", "usuario__username")
    readonly_fields = ("creado_en", "actualizado_en", "cancelado_en", "llamada_actualizada_en")
    ordering = ("-dia", "-hora")
