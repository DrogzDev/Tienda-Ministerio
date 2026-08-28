from rest_framework.permissions import BasePermission


# ============================================================
# ROLES DEL SISTEMA
# ============================================================

ROLE_ADMINISTRADOR = "ADMINISTRADOR"
ROLE_DIRECTOR = "DIRECTOR"
ROLE_ALMACENISTA = "ALMACENISTA"


SYSTEM_ROLES = (
    ROLE_ADMINISTRADOR,
    ROLE_DIRECTOR,
    ROLE_ALMACENISTA,
)


# ============================================================
# HELPERS
# ============================================================

def _is_authenticated_user(user):
    return bool(
        user
        and
        user.is_authenticated
    )


def get_user_roles(user):
    """
    Retorna solamente los roles oficiales del sistema.

    Importante:
    - Un usuario normal debe tener EXACTAMENTE un rol del sistema.
    - El superusuario puede seguir usando el bypass administrativo.
    """

    if not _is_authenticated_user(user):
        return []

    return list(
        user.groups
        .filter(
            name__in=SYSTEM_ROLES
        )
        .order_by(
            "name"
        )
        .values_list(
            "name",
            flat=True,
        )
    )


def get_single_system_role(user):
    """
    Retorna el único rol válido del usuario.

    Si un usuario normal tiene 0 o más de 1 rol oficial,
    retorna None para fallar de forma segura y evitar una
    escalada accidental de privilegios.
    """

    if not _is_authenticated_user(user):
        return None

    if user.is_superuser:
        return ROLE_ADMINISTRADOR

    roles = get_user_roles(user)

    if len(roles) != 1:
        return None

    return roles[0]


def has_valid_system_role(user):
    """
    Indica si el usuario tiene una asignación válida de rol.

    Superusuarios se consideran válidos.
    Usuarios normales deben tener exactamente un rol.
    """

    if not _is_authenticated_user(user):
        return False

    if user.is_superuser:
        return True

    return (
        get_single_system_role(user)
        is not None
    )


def user_has_role(
    user,
    role,
):
    """
    Comprueba si el usuario posee un rol concreto.

    Seguridad:
    - superuser: bypass total.
    - usuario normal con 0 roles: denegado.
    - usuario normal con múltiples roles: denegado.
    - usuario normal con exactamente 1 rol: se evalúa ese rol.
    """

    if not _is_authenticated_user(user):
        return False

    if user.is_superuser:
        return True

    return (
        get_single_system_role(user)
        ==
        role
    )


def user_has_any_role(
    user,
    *roles,
):
    """
    Comprueba si el único rol válido del usuario está
    dentro de los roles permitidos.

    Un usuario normal con múltiples roles oficiales
    NO recibe privilegios acumulados.
    """

    if not _is_authenticated_user(user):
        return False

    if user.is_superuser:
        return True

    current_role = (
        get_single_system_role(user)
    )

    if current_role is None:
        return False

    return (
        current_role
        in
        roles
    )


# ============================================================
# CUALQUIER USUARIO DEL INVENTARIO
# ============================================================

class IsInventoryUser(
    BasePermission
):

    message = (
        "No tienes permisos para acceder "
        "al sistema de inventario o tu usuario "
        "tiene una asignación de rol inválida."
    )

    def has_permission(
        self,
        request,
        view,
    ):

        return user_has_any_role(
            request.user,
            ROLE_ADMINISTRADOR,
            ROLE_DIRECTOR,
            ROLE_ALMACENISTA,
        )


# ============================================================
# ADMINISTRADOR
# ============================================================

class IsAdministrador(
    BasePermission
):

    message = (
        "Esta operación requiere permisos "
        "de administrador."
    )

    def has_permission(
        self,
        request,
        view,
    ):

        return user_has_role(
            request.user,
            ROLE_ADMINISTRADOR,
        )


# ============================================================
# DIRECTOR
# ============================================================

class IsDirector(
    BasePermission
):

    message = (
        "Esta operación requiere permisos "
        "de director."
    )

    def has_permission(
        self,
        request,
        view,
    ):

        return user_has_role(
            request.user,
            ROLE_DIRECTOR,
        )


# ============================================================
# ALMACENISTA
# ============================================================

class IsAlmacenista(
    BasePermission
):

    message = (
        "Esta operación requiere permisos "
        "de almacenista."
    )

    def has_permission(
        self,
        request,
        view,
    ):

        return user_has_role(
            request.user,
            ROLE_ALMACENISTA,
        )


# ============================================================
# ADMINISTRADOR O DIRECTOR
# ============================================================

class IsAdministradorOrDirector(
    BasePermission
):

    message = (
        "Esta operación solo puede realizarla "
        "un administrador o director."
    )

    def has_permission(
        self,
        request,
        view,
    ):

        return user_has_any_role(
            request.user,
            ROLE_ADMINISTRADOR,
            ROLE_DIRECTOR,
        )


# ============================================================
# ADMINISTRADOR O ALMACENISTA
# ============================================================

class IsAdministradorOrAlmacenista(
    BasePermission
):

    message = (
        "Esta operación solo puede realizarla "
        "un administrador o almacenista."
    )

    def has_permission(
        self,
        request,
        view,
    ):

        return user_has_any_role(
            request.user,
            ROLE_ADMINISTRADOR,
            ROLE_ALMACENISTA,
        )