from django.urls import path

from .views import buscar_rbd

app_name = "rbd"

urlpatterns = [
    path("", buscar_rbd, name="buscar"),
]
