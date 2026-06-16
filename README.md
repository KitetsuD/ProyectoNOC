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

Los tutoriales operativos se cargan desde `ADMIN > Tutoriales Admin`. Ese apartado permite importar automaticamente el documento base `.docx`, crear tutoriales visibles para operadores, asociar un documento completo y publicar u ocultar cada registro.

El respaldo inicial de los tutoriales actuales queda en `docs/ProyectoNOC_Tutoriales_Operativos_Base.docx`; la pantalla `Tutoriales Admin` tambien permite descargarlo como documento base.

## Configuracion

Las variables principales estan en `.env`. El archivo `.env.example` sirve como referencia para otros ambientes.
