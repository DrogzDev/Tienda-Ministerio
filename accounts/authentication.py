from rest_framework.authentication import (
    CSRFCheck,
)

from rest_framework.exceptions import (
    PermissionDenied,
)

from rest_framework_simplejwt.authentication import (
    JWTAuthentication,
)

from django.conf import settings


SAFE_METHODS = (
    "GET",
    "HEAD",
    "OPTIONS",
)


def enforce_csrf(
    request,
):

    check = CSRFCheck(
        lambda request: None
    )


    check.process_request(
        request
    )


    reason = (
        check.process_view(
            request,
            None,
            (),
            {},
        )
    )


    if reason:

        raise PermissionDenied(
            f"CSRF Failed: {reason}"
        )


class CookieJWTAuthentication(
    JWTAuthentication
):

    def authenticate(
        self,
        request,
    ):

        raw_token = (
            request.COOKIES.get(
                settings.JWT_ACCESS_COOKIE
            )
        )


        if not raw_token:

            return None


        validated_token = (
            self.get_validated_token(
                raw_token
            )
        )


        user = (
            self.get_user(
                validated_token
            )
        )


        if (
            request.method
            not in SAFE_METHODS
        ):

            enforce_csrf(
                request
            )


        return (
            user,
            validated_token,
        )