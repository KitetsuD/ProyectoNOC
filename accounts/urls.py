from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path
from django.views.generic import RedirectView

from . import views


urlpatterns = [
    path("", RedirectView.as_view(pattern_name="rbd:buscar", permanent=False), name="inicio"),
    path("bitacora/", include("bitacora.urls")),
    path("rbd/", include("rbd.urls")),
    path("procedimientos/", views.procedimientos, name="procedimientos"),
    path("sicret/", views.sicret, name="sicret"),
    path("procedimientos/<int:procedimiento_id>/toggle/", views.procedimiento_toggle, name="procedimiento_toggle"),
    path("procedimientos/<int:procedimiento_id>/accion/", views.procedimiento_accion, name="procedimiento_accion"),
    path("administracion/carga/", views.admin_carga_datos, name="admin_carga_datos"),
    path("administracion/carga/plantilla/", views.admin_descargar_plantilla, name="admin_descargar_plantilla"),
    path("administracion/rbd/", views.admin_rbd, name="admin_rbd"),
    path("administracion/rbd/<int:servicio_id>/editar/", views.admin_rbd_editar, name="admin_rbd_editar"),
    path("administracion/usuarios/", views.admin_usuarios, name="admin_usuarios"),
    path("administracion/usuarios/nuevo/", views.admin_usuario_crear, name="admin_usuario_crear"),
    path("administracion/usuarios/<int:user_id>/editar/", views.admin_usuario_editar, name="admin_usuario_editar"),
    path("administracion/usuarios/<int:user_id>/accion/", views.admin_usuario_accion, name="admin_usuario_accion"),
    path(
        "login/",
        LoginView.as_view(
            template_name="accounts/login_propuesta_4.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path(
        "login/propuesta-2/",
        LoginView.as_view(
            template_name="accounts/login_propuesta_2.html",
            redirect_authenticated_user=True,
        ),
        name="login_propuesta_2",
    ),
    path(
        "login/propuesta-3/",
        LoginView.as_view(
            template_name="accounts/login_propuesta_3.html",
            redirect_authenticated_user=True,
        ),
        name="login_propuesta_3",
    ),
    path(
        "login/propuesta-4/",
        LoginView.as_view(
            template_name="accounts/login_propuesta_4.html",
            redirect_authenticated_user=True,
        ),
        name="login_propuesta_4",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
]
