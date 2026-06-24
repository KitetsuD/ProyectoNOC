from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path
from django.views.generic import RedirectView

from . import views


urlpatterns = [
    path("", RedirectView.as_view(pattern_name="rbd:buscar", permanent=False), name="inicio"),
    path("bitacora/", include("bitacora.urls")),
    path("rbd/", include("rbd.urls")),
    path("procedimientos/", views.procedimientos, name="procedimientos"),
    path("procedimientos/<int:procedimiento_id>/archivo/", views.procedimiento_archivo, name="procedimiento_archivo"),
    path("enlaces/", views.enlaces_operativos, name="enlaces_operativos"),
    path("enlaces/<int:enlace_id>/toggle/", views.enlace_operativo_toggle, name="enlace_operativo_toggle"),
    path("enlaces/<int:enlace_id>/eliminar/", views.enlace_operativo_eliminar, name="enlace_operativo_eliminar"),
    path("sicret/", views.sicret, name="sicret"),
    path("sicret/tickets/", views.sicret_tickets, name="sicret_tickets"),
    path("sicret/tickets/<int:solicitud_id>/estado/", views.sicret_ticket_estado, name="sicret_ticket_estado"),
    path("sicret/rbd-info/", views.sicret_rbd_info, name="sicret_rbd_info"),
    path("sagec/", views.sagec, name="sagec"),
    path("sagec/tickets/", views.sagec_tickets, name="sagec_tickets"),
    path("sagec/tickets/<int:solicitud_id>/estado/", views.sagec_ticket_estado, name="sagec_ticket_estado"),
    path("procedimientos/<int:procedimiento_id>/toggle/", views.procedimiento_toggle, name="procedimiento_toggle"),
    path("procedimientos/<int:procedimiento_id>/accion/", views.procedimiento_accion, name="procedimiento_accion"),
    path("administracion/carga/", views.admin_carga_datos, name="admin_carga_datos"),
    path("administracion/carga/plantilla/", views.admin_descargar_plantilla, name="admin_descargar_plantilla"),
    path("administracion/historial/", views.admin_historial_operativo, name="admin_historial_operativo"),
    path("administracion/tutoriales/", views.admin_tutoriales, name="admin_tutoriales"),
    path("administracion/tutoriales/<int:tutorial_id>/editar/", views.admin_tutorial_editar, name="admin_tutorial_editar"),
    path("administracion/tutoriales/documento-base/", views.admin_tutoriales_documento_base, name="admin_tutoriales_documento_base"),
    path("administracion/rbd/", views.admin_rbd, name="admin_rbd"),
    path("administracion/rbd/<int:servicio_id>/editar/", views.admin_rbd_editar, name="admin_rbd_editar"),
    path("administracion/rbd/<int:servicio_id>/eliminar/", views.admin_rbd_eliminar, name="admin_rbd_eliminar"),
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
