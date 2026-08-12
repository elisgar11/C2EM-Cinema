# Cine privado

Aplicación web autohospedada para usar una sala de cine personal como un pequeño cine real: cartelera, sesiones, reserva de butacas, palomitas/packs, entradas digitales y anuncios creados por los amigos.

## Estado

MVP funcional implementado:

- Cartelera y detalle de películas.
- Varias salas y mapa de butacas configurable.
- Sesiones con precio y horario.
- Reserva visual de butacas.
- Prevención de doble reserva en base de datos.
- Productos y packs configurables.
- Checkout sin pago real.
- Entrada digital con QR.
- Búsqueda de entradas mediante código de reserva.
- Check-in de entradas para administradores.
- Escáner QR para staff con fallback manual.
- Pre-show por sesión con anuncios y cuenta atrás.
- Cancelación administrativa que libera las butacas.
- Publicidad programable por ubicación.
- Branding del cine.
- Django Admin para toda la gestión.
- Datos de demostración.
- Docker + SQLite persistente.
- Tests de la lógica crítica.

## Arranque con Docker

```bash
cp .env.example .env
docker compose up --build -d
```

Abrir `http://localhost:8000/`.

El contenedor ejecuta automáticamente migraciones y `collectstatic` al arrancar.

## Crear administrador

```bash
docker compose exec web python manage.py createsuperuser
```

Después abrir `http://localhost:8000/admin/`.

## Cargar una demo

```bash
docker compose exec web python manage.py seed_demo
```

Crea una sala con 30 butacas, 3 películas, 6 sesiones futuras, 5 productos, 2 packs, butacas VIP y anuncios de ejemplo, incluido uno para el pre-show.

## Crear butacas rápidamente

Primero crea la sala desde el admin. Después:

```bash
docker compose exec web python manage.py create_seats "Sala Principal" A B C D E --count 6
```

El comando no duplica butacas ya existentes.

## Flujo de uso

1. En `/admin/`, configura branding, películas, sala, sesiones, productos, packs y anuncios.
2. Un amigo entra en `/` y selecciona una película y sesión.
3. Elige butacas disponibles.
4. Añade extras opcionalmente.
5. Confirma con su nombre.
6. Obtiene una entrada digital con QR.
7. La reserva aparece en el admin.
8. El amigo puede recuperar la entrada desde `Buscar entrada` usando su código `CINE-XXXXXX`.
9. Un administrador puede validar la entrada desde el propio ticket o desde el escáner de staff.
10. Si el administrador cancela la reserva, sus butacas vuelven a quedar disponibles.

## Check-in

El QR de la entrada sigue apuntando a la URL pública de esa entrada. Si un administrador autenticado abre esa misma URL, aparece un control adicional para validar el acceso.

El check-in:

- solo está disponible para usuarios staff;
- queda registrado con fecha y hora;
- es idempotente: validar dos veces no crea dos accesos;
- no se permite en reservas canceladas.

También puede realizarse en lote desde la lista de reservas de Django Admin.

## Escáner de entradas

Los usuarios staff ven el enlace `Escanear` en la navegación. La ruta es `/staff/scanner/`.

El escáner acepta:

- el QR generado por la aplicación;
- la URL completa de una entrada;
- el UUID de una entrada;
- el código `CINE-XXXXXX`.

Cuando el navegador dispone de `BarcodeDetector` y acceso a cámara, puede leer el QR directamente. El acceso a cámara normalmente requiere HTTPS o `localhost`; si no está disponible, el formulario manual sigue funcionando.

## Pre-show

Cada sesión muestra un enlace `Pre-show` en Django Admin. La vista está protegida para staff y está pensada para abrirse en la pantalla/proyector de la sala.

El pre-show:

- rota los anuncios activos de ubicación `Pre-show`;
- respeta fechas de inicio/fin y prioridad;
- termina mostrando película, sala, hora y una cuenta atrás;
- dispone de botón de pantalla completa y avance manual.

## Publicidad

Los anuncios se crean en `Administración > Anuncios` y pueden colocarse en:

- Portada.
- Detalle de película.
- Checkout.
- Entrada.
- Pre-show.

Se pueden programar con fecha de inicio/fin y prioridad. Imagen/GIF y enlace son opcionales.

## Verificación

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py test
docker compose exec web python manage.py makemigrations --check --dry-run
```

## Datos persistentes

- Base de datos: `./data/db.sqlite3`
- Archivos subidos: `./media/`

Para un backup básico, copia ambos.

## Configuración

Variables disponibles en `.env`:

```env
SECRET_KEY=replace-with-a-long-random-value
DEBUG=false
ALLOWED_HOSTS=localhost,127.0.0.1
TIME_ZONE=Europe/Madrid
CSRF_TRUSTED_ORIGINS=
```

Para acceder desde otros equipos de la red, añade el nombre/IP del servidor a `ALLOWED_HOSTS`. Si lo publicas detrás de HTTPS con un proxy y un dominio propio, añade el origen completo (por ejemplo, `https://cine.example.com`) a `CSRF_TRUSTED_ORIGINS`.

## Desarrollo sin Docker

Requiere Python 3.13 o compatible con Django 5.2.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver
```

## Estructura

Se mantiene deliberadamente una única app Django (`core`) para evitar arquitectura innecesaria en un proyecto privado de este tamaño. La lógica de confirmación de reservas está aislada en `core/services.py` y el resto usa Django Admin, ORM, sesiones y templates estándar.

## Decisiones del MVP

- Sin pagos reales.
- Sin cuentas para los invitados.
- Sin bloqueos temporales de butacas.
- Sin WebSockets.
- Sin SPA/React/Vue.
- Sin servicios externos para metadatos de películas.
- SQLite como base por defecto y un worker Gunicorn para reducir contención de escritura.

La disponibilidad se vuelve a comprobar en el servidor al confirmar y una restricción parcial en la base de datos impide dos ocupaciones activas de la misma butaca para la misma sesión.
