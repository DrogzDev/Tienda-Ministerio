from django.utils import timezone

from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
)

from .models import (
    UserPresence,
)

from .permissions import (
    get_user_roles,
)


class CustomTokenObtainPairSerializer(
    TokenObtainPairSerializer
):

    # ========================================================
    # TOKEN
    # ========================================================

    @classmethod
    def get_token(
        cls,
        user,
    ):

        token = super().get_token(
            user
        )


        roles = get_user_roles(
            user
        )


        # ====================================================
        # DATOS DEL USUARIO DENTRO DEL JWT
        # ====================================================

        token["username"] = (
            user.username
        )

        token["email"] = (
            user.email
            or ""
        )

        token["first_name"] = (
            user.first_name
            or ""
        )

        token["last_name"] = (
            user.last_name
            or ""
        )


        # ====================================================
        # ROLES
        # ====================================================

        token["roles"] = roles


        # ====================================================
        # FLAGS DJANGO
        # ====================================================

        token["is_staff"] = (
            user.is_staff
        )

        token["is_superuser"] = (
            user.is_superuser
        )


        return token


    # ========================================================
    # LOGIN RESPONSE
    # ========================================================

    def validate(
        self,
        attrs,
    ):

        data = super().validate(
            attrs
        )


        user = self.user


        # ====================================================
        # MARCAR ONLINE
        # ====================================================

        UserPresence.objects.update_or_create(
            user=user,
            defaults={
                "online": True,
                "last_seen": timezone.now(),
            },
        )


        roles = get_user_roles(
            user
        )


        # ====================================================
        # RESPUESTA AL FRONTEND
        # ====================================================

        data["user"] = {

            "id":
                user.id,

            "username":
                user.username,

            "email":
                user.email
                or "",

            "first_name":
                user.first_name
                or "",

            "last_name":
                user.last_name
                or "",

            "roles":
                roles,

            "is_staff":
                user.is_staff,

            "is_superuser":
                user.is_superuser,
        }


        return data