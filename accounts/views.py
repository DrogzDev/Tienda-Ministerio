from datetime import timedelta

from django.conf import settings

from django.contrib.auth import (
    get_user_model,
)

from django.middleware.csrf import (
    get_token,
)

from django.utils import timezone

from django.utils.decorators import (
    method_decorator,
)

from django.views.decorators.csrf import (
    csrf_protect,
    ensure_csrf_cookie,
)

from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)

from rest_framework.response import (
    Response,
)

from rest_framework.views import (
    APIView,
)

from rest_framework_simplejwt.authentication import (
    JWTAuthentication,
)

from rest_framework_simplejwt.tokens import (
    RefreshToken,
)

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
)

from .models import (
    UserPresence,
)

from .permissions import (
    IsAdministradorOrDirector,
    SYSTEM_ROLES,
    get_user_roles,
)

from .serializers import (
    CustomTokenObtainPairSerializer,
)


User = get_user_model()


# ============================================================
# HELPERS COOKIES
# ============================================================

def set_auth_cookie(
    response,
    *,
    key,
    value,
    max_age,
):

    response.set_cookie(
        key=key,
        value=value,

        max_age=max_age,

        httponly=True,

        secure=settings.JWT_COOKIE_SECURE,

        samesite=settings.JWT_COOKIE_SAMESITE,

        path="/",
    )


def delete_auth_cookies(
    response,
):

    response.delete_cookie(
        settings.JWT_ACCESS_COOKIE,
        path="/",
        samesite=settings.JWT_COOKIE_SAMESITE,
    )

    response.delete_cookie(
        settings.JWT_REFRESH_COOKIE,
        path="/",
        samesite=settings.JWT_COOKIE_SAMESITE,
    )


# ============================================================
# CSRF
# ============================================================

@method_decorator(
    ensure_csrf_cookie,
    name="dispatch",
)
class CsrfAPIView(
    APIView
):

    permission_classes = [
        AllowAny,
    ]

    authentication_classes = []


    def get(
        self,
        request,
    ):

        token = get_token(
            request
        )


        return Response({
            "detail":
                "CSRF configurado.",

            "csrfToken":
                token,
        })


# ============================================================
# LOGIN
# ============================================================

@method_decorator(
    csrf_protect,
    name="dispatch",
)
class LoginAPIView(
    TokenObtainPairView
):

    permission_classes = [
        AllowAny,
    ]

    authentication_classes = []

    serializer_class = (
        CustomTokenObtainPairSerializer
    )


    def post(
        self,
        request,
        *args,
        **kwargs,
    ):

        serializer = (
            self.get_serializer(
                data=request.data
            )
        )


        serializer.is_valid(
            raise_exception=True
        )


        data = dict(
            serializer.validated_data
        )


        access = data.pop(
            "access"
        )

        refresh = data.pop(
            "refresh"
        )


        response = Response(
            data
        )


        set_auth_cookie(
            response,

            key=(
                settings
                .JWT_ACCESS_COOKIE
            ),

            value=access,

            max_age=(
                8
                *
                60
                *
                60
            ),
        )


        set_auth_cookie(
            response,

            key=(
                settings
                .JWT_REFRESH_COOKIE
            ),

            value=refresh,

            max_age=(
                8
                *
                60
                *
                60
            ),
        )


        return response


# ============================================================
# USUARIO ACTUAL
# ============================================================

class MeAPIView(
    APIView
):

    permission_classes = [
        IsAuthenticated,
    ]


    def get(
        self,
        request,
    ):

        user = request.user


        return Response({

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
                get_user_roles(
                    user
                ),

            "is_staff":
                user.is_staff,

            "is_superuser":
                user.is_superuser,

        })


# ============================================================
# REFRESH
# ============================================================

@method_decorator(
    csrf_protect,
    name="dispatch",
)
class RefreshAPIView(
    APIView
):

    permission_classes = [
        AllowAny,
    ]

    authentication_classes = []


    def post(
        self,
        request,
    ):

        raw_refresh = (
            request.COOKIES.get(
                settings.JWT_REFRESH_COOKIE
            )
        )


        if not raw_refresh:

            return Response(
                {
                    "detail":
                        "No existe un refresh token."
                },
                status=401,
            )


        try:

            refresh_token = (
                RefreshToken(
                    raw_refresh
                )
            )


            access_token = str(
                refresh_token.access_token
            )


        except Exception:

            response = Response(
                {
                    "detail":
                        "La sesión ha expirado."
                },
                status=401,
            )


            delete_auth_cookies(
                response
            )


            return response


        response = Response({
            "detail":
                "Token renovado correctamente."
        })


        set_auth_cookie(
            response,

            key=(
                settings.JWT_ACCESS_COOKIE
            ),

            value=access_token,

            max_age=(
                8
                *
                60
                *
                60
            ),
        )


        return response


# ============================================================
# HEARTBEAT
# ============================================================

class HeartbeatAPIView(
    APIView
):

    permission_classes = [
        IsAuthenticated,
    ]


    def post(
        self,
        request,
    ):

        now = timezone.now()


        UserPresence.objects.update_or_create(
            user=request.user,

            defaults={
                "online":
                    True,

                "last_seen":
                    now,
            },
        )


        return Response({
            "online":
                True,

            "last_seen":
                now,
        })


# ============================================================
# USUARIOS ONLINE
# ============================================================

class OnlineUsersAPIView(
    APIView
):

    permission_classes = [
        IsAdministradorOrDirector,
    ]


    def get(
        self,
        request,
    ):

        limit = (
            timezone.now()
            -
            timedelta(
                minutes=2
            )
        )


        users = (
            User.objects
            .filter(
                is_active=True,

                presence__online=True,

                presence__last_seen__gte=limit,

                groups__name__in=(
                    SYSTEM_ROLES
                ),
            )
            .select_related(
                "presence"
            )
            .prefetch_related(
                "groups"
            )
            .distinct()
            .order_by(
                "first_name",
                "last_name",
                "username",
            )
        )


        results = []


        for user in users:

            results.append({

                "id":
                    user.id,

                "username":
                    user.username,

                "first_name":
                    user.first_name
                    or "",

                "last_name":
                    user.last_name
                    or "",

                "email":
                    user.email
                    or "",

                "roles":
                    get_user_roles(
                        user
                    ),

                "online":
                    True,

                "last_seen":
                    user.presence.last_seen,

            })


        return Response({

            "count":
                len(results),

            "users":
                results,

        })


# ============================================================
# LOGOUT
# ============================================================

@method_decorator(
    csrf_protect,
    name="dispatch",
)
class LogoutAPIView(
    APIView
):

    # Lo dejamos público porque incluso si el
    # access token ya venció debemos poder
    # eliminar las cookies del navegador.

    permission_classes = [
        AllowAny,
    ]

    authentication_classes = []


    def post(
        self,
        request,
    ):

        raw_access = (
            request.COOKIES.get(
                settings.JWT_ACCESS_COOKIE
            )
        )


        # Intentamos identificar al usuario
        # para marcarlo offline.

        if raw_access:

            try:

                jwt_auth = (
                    JWTAuthentication()
                )


                validated_token = (
                    jwt_auth
                    .get_validated_token(
                        raw_access
                    )
                )


                user = (
                    jwt_auth
                    .get_user(
                        validated_token
                    )
                )


                UserPresence.objects.filter(
                    user=user
                ).update(
                    online=False,
                    last_seen=timezone.now(),
                )


            except Exception:
                pass


        response = Response({
            "detail":
                "Sesión cerrada correctamente."
        })


        delete_auth_cookies(
            response
        )


        return response