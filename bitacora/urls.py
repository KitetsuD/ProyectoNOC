from django.urls import path

from .views import calendario_bitacora, crear_bitacora, disponibilidad_bitacora

app_name = "bitacora"

urlpatterns = [
    path("", crear_bitacora, name="crear"),
    path("calendario/", calendario_bitacora, name="calendario"),
    path("disponibilidad/", disponibilidad_bitacora, name="disponibilidad"),
]
