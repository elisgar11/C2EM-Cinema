import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

_django_app = None
_vercel_prepared = False


def _prepare_vercel_runtime():
    global _vercel_prepared
    if _vercel_prepared or not os.environ.get("VERCEL"):
        return
    from django.core.management import call_command

    call_command("migrate", "--noinput", verbosity=0)
    call_command("ensure_default_admin", verbosity=0)
    _vercel_prepared = True


def application(environ, start_response):
    global _django_app
    if _django_app is None:
        from django.core.wsgi import get_wsgi_application

        _django_app = get_wsgi_application()
    _prepare_vercel_runtime()
    return _django_app(environ, start_response)
