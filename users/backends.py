from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Backend de autenticación que permite iniciar sesión utilizando
    indistintamente el correo electrónico o el nombre de usuario tradicional.
    La comparación es insensible a mayúsculas/minúsculas.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD) or kwargs.get('email')

        if not username or not password:
            return None

        username = username.strip()

        # Buscar usuarios coincidentes por email o username (case-insensitive)
        usuarios = User.objects.filter(
            Q(email__iexact=username) | Q(username__iexact=username)
        ).distinct()

        for user in usuarios:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user

        return None
