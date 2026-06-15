# ProyectoNOC

Plataforma interna para centralizar la gestion operativa del area NOC Cliente GTD.

ProyectoNOC permite consultar informacion tecnica por RBD, revisar contactos operativos, registrar agendamientos de bitacora sin duplicar horarios y administrar cargas masivas de informacion desde un Excel maestro.

## Stack

- Django 6
- PostgreSQL 16
- Docker Compose

## Ejecutar con Docker

```powershell
docker compose up --build
```

La aplicacion queda disponible en:

```text
http://localhost:8003
```

PostgreSQL queda expuesto localmente en el puerto `5433` para evitar conflictos con otros proyectos.

En produccion el contenedor ejecuta migraciones, recolecta archivos estaticos con `collectstatic` y levanta Django con Gunicorn. Esto permite que `/admin/` cargue correctamente sus CSS y JS con `DEBUG=False`.

## Comandos utiles

```powershell
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py check
docker compose exec web python manage.py cargar_procedimientos_base
```

## Carga de informacion

Los usuarios ADMIN pueden descargar y subir el Excel maestro desde `Carga de datos`. El archivo concentra servicios RBD, contactos y catalogo de jornada en una sola plantilla para poblar o actualizar ambientes productivos.

Los tutoriales operativos base se cargan con `cargar_procedimientos_base`; el comando crea o actualiza las guias paso a paso y enlaza sus PDF desde archivos estaticos del proyecto.

## Configuracion

Las variables principales estan en `.env`. El archivo `.env.example` sirve como referencia para otros ambientes.
