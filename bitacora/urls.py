from django.urls import path

from .views import (
    calendario_bitacora,
    cancelar_bitacora,
    cambiar_estado_llamada,
    crear_bitacora,
    disponibilidad_bitacora,
    editar_bitacora,
)

app_name = "bitacora"

urlpatterns = [
    path("", crear_bitacora, name="crear"),
    path("calendario/", calendario_bitacora, name="calendario"),
    path("disponibilidad/", disponibilidad_bitacora, name="disponibilidad"),
    path("<int:registro_id>/editar/", editar_bitacora, name="editar"),
    path("<int:registro_id>/cancelar/", cancelar_bitacora, name="cancelar"),
    path("<int:registro_id>/llamada/", cambiar_estado_llamada, name="llamada"),
]
