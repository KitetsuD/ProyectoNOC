from django.urls import path

from .views import buscar_rbd, servicios_baja

app_name = "rbd"

urlpatterns = [
    path("", buscar_rbd, name="buscar"),
    path("bajas/", servicios_baja, name="bajas"),
]
