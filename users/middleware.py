import traceback
from .utils import registrar_log


class AuditAndErrorLoggingMiddleware:
    """
    Middleware global para captura de excepciones (Errores 500) y monitorización técnica.
    Cualquier error inesperado en vistas se registra en base de datos con traceback completo.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Si la respuesta es un error 500 que no fue lanzado como excepción pero devolvió status 500
        if response.status_code >= 500 and not getattr(request, '_exception_logged', False):
            registrar_log(
                request=request,
                nivel='ERROR',
                tipo='ERROR_500',
                mensaje=f"Respuesta de servidor HTTP {response.status_code} en ruta: {request.path}"
            )

        return response

    def process_exception(self, request, exception):
        """
        Captura excepciones no controladas antes de que Django devuelva la pantalla 500.
        Guarda el traceback, usuario, IP y detalles técnicos en LogActividad.
        """
        request._exception_logged = True
        error_msg = f"{type(exception).__name__}: {str(exception)}"
        tb_str = traceback.format_exc()

        registrar_log(
            request=request,
            nivel='ERROR',
            tipo='ERROR_500',
            mensaje=f"Excepción 500 capturada: {error_msg}",
            traceback_str=tb_str
        )

        # Devolvemos None para que Django continúe con su manejo normal de excepciones
        return None
