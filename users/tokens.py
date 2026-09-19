from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    Generador de tokens criptográficos de un solo uso para la activación
    de cuentas y verificación de correo electrónico.
    El hash depende del estado de activación (is_active) y del email:
    tan pronto como la cuenta se activa, el token queda inmediatamente invalidado
    e imposibilita su reutilización.
    """

    def _make_hash_value(self, user, timestamp):
        email_field = user.get_email_field_name()
        email = getattr(user, email_field, '') or ''
        return f"{user.pk}{timestamp}{user.is_active}{email}"


email_verification_token = EmailVerificationTokenGenerator()
