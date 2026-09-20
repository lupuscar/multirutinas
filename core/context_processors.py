from .models import ConfiguracionSitio


def configuracion_sitio(request):
    """
    Inyecta la configuración global del sitio en el contexto de todas las plantillas.
    """
    try:
        config = ConfiguracionSitio.get_config()
    except Exception:
        config = None

    return {
        'config_sitio': config,
    }
