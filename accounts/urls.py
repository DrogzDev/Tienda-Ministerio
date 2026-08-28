from django.urls import (
    path,
)

from .views import (
    CsrfAPIView,
    LoginAPIView,
    MeAPIView,
    RefreshAPIView,
    HeartbeatAPIView,
    OnlineUsersAPIView,
    LogoutAPIView,
)


urlpatterns = [

    # ========================================================
    # CSRF
    # ========================================================

    path(
        "csrf/",
        CsrfAPIView.as_view(),
        name="csrf",
    ),


    # ========================================================
    # LOGIN
    # ========================================================

    path(
        "login/",
        LoginAPIView.as_view(),
        name="login",
    ),


    # ========================================================
    # USUARIO ACTUAL
    # ========================================================

    path(
        "me/",
        MeAPIView.as_view(),
        name="me",
    ),


    # ========================================================
    # REFRESH
    # ========================================================

    path(
        "refresh/",
        RefreshAPIView.as_view(),
        name="token-refresh",
    ),


    # ========================================================
    # PRESENCIA
    # ========================================================

    path(
        "heartbeat/",
        HeartbeatAPIView.as_view(),
        name="heartbeat",
    ),


    path(
        "online-users/",
        OnlineUsersAPIView.as_view(),
        name="online-users",
    ),


    # ========================================================
    # LOGOUT
    # ========================================================

    path(
        "logout/",
        LogoutAPIView.as_view(),
        name="logout",
    ),

]