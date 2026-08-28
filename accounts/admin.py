from django import forms

from django.contrib import admin

from django.contrib.auth import (
    get_user_model,
)

from django.contrib.auth.admin import (
    UserAdmin,
)

from django.contrib.auth.forms import (
    UserChangeForm,
    UserCreationForm,
)

from django.contrib.auth.models import (
    Group,
)

from .models import (
    UserPresence,
)


User = get_user_model()


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
# FORMULARIO - EDITAR USUARIO
# ============================================================

class SystemUserChangeForm(
    UserChangeForm
):

    role = forms.ModelChoiceField(
        label="Rol del sistema",
        queryset=Group.objects.none(),
        required=True,
        help_text=(
            "Selecciona el rol principal "
            "del usuario dentro del sistema."
        ),
    )


    class Meta(
        UserChangeForm.Meta
    ):
        model = User

        fields = "__all__"


    def __init__(
        self,
        *args,
        **kwargs,
    ):

        super().__init__(
            *args,
            **kwargs,
        )


        self.fields[
            "role"
        ].queryset = (
            Group.objects
            .filter(
                name__in=SYSTEM_ROLES
            )
            .order_by(
                "name"
            )
        )


        if (
            self.instance
            and
            self.instance.pk
        ):

            current_role = (
                self.instance.groups
                .filter(
                    name__in=SYSTEM_ROLES
                )
                .first()
            )


            if current_role:

                self.fields[
                    "role"
                ].initial = (
                    current_role
                )


# ============================================================
# FORMULARIO - CREAR USUARIO
# ============================================================

class SystemUserCreationForm(
    UserCreationForm
):

    role = forms.ModelChoiceField(
        label="Rol del sistema",
        queryset=Group.objects.none(),
        required=True,
        help_text=(
            "Selecciona el rol que tendrá "
            "este usuario."
        ),
    )


    email = forms.EmailField(
        required=False,
    )


    first_name = forms.CharField(
        label="Nombre",
        required=False,
    )


    last_name = forms.CharField(
        label="Apellido",
        required=False,
    )


    class Meta(
        UserCreationForm.Meta
    ):

        model = User

        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
        )


    def __init__(
        self,
        *args,
        **kwargs,
    ):

        super().__init__(
            *args,
            **kwargs,
        )


        self.fields[
            "role"
        ].queryset = (
            Group.objects
            .filter(
                name__in=SYSTEM_ROLES
            )
            .order_by(
                "name"
            )
        )


# ============================================================
# PRESENCIA INLINE
# ============================================================

class UserPresenceInline(
    admin.StackedInline
):

    model = UserPresence

    extra = 0

    can_delete = False

    readonly_fields = (
        "online",
        "last_seen",
        "updated_at",
    )


    fieldsets = (

        (
            "Presencia",
            {
                "fields": (
                    "online",
                    "last_seen",
                    "updated_at",
                )
            },
        ),

    )


# ============================================================
# USER ADMIN
# ============================================================

class SystemUserAdmin(
    UserAdmin
):

    form = SystemUserChangeForm

    add_form = SystemUserCreationForm


    # ========================================================
    # LISTADO
    # ========================================================

    list_display = (
        "username",
        "full_name_display",
        "email",
        "role_display",
        "online_display",
        "last_seen_display",
        "is_active",
        "is_staff",
    )


    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "groups",
    )


    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
    )


    ordering = (
        "username",
    )


    list_per_page = 50


    # ========================================================
    # EDITAR
    # ========================================================

    fieldsets = (

        (
            "Cuenta",
            {
                "fields": (
                    "username",
                    "password",
                )
            },
        ),

        (
            "Información personal",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                )
            },
        ),

        (
            "Rol del sistema",
            {
                "fields": (
                    "role",
                ),

                "description": (
                    "Cada usuario debe tener "
                    "un único rol principal."
                ),
            },
        ),

        (
            "Estado",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                )
            },
        ),

        (
            "Administración avanzada",
            {
                "classes": (
                    "collapse",
                ),

                "fields": (
                    "is_superuser",
                    "user_permissions",
                ),
            },
        ),

        (
            "Fechas",
            {
                "classes": (
                    "collapse",
                ),

                "fields": (
                    "last_login",
                    "date_joined",
                ),
            },
        ),

    )


    # ========================================================
    # CREAR
    # ========================================================

    add_fieldsets = (

        (
            "Crear usuario",
            {
                "classes": (
                    "wide",
                ),

                "fields": (
                    "username",
                    "first_name",
                    "last_name",
                    "email",
                    "role",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                ),
            },
        ),

    )


    readonly_fields = (
        "last_login",
        "date_joined",
    )


    inlines = (
        UserPresenceInline,
    )


    # ========================================================
    # GUARDAR ROL
    # ========================================================

    def save_related(
        self,
        request,
        form,
        formsets,
        change,
    ):

        super().save_related(
            request,
            form,
            formsets,
            change,
        )


        role = (
            form.cleaned_data
            .get(
                "role"
            )
        )


        if not role:
            return


        user = form.instance


        # Elimina cualquiera de nuestros
        # roles anteriores.

        user.groups.remove(
            *Group.objects.filter(
                name__in=SYSTEM_ROLES
            )
        )


        # Asigna exclusivamente el nuevo.

        user.groups.add(
            role
        )


    # ========================================================
    # COLUMNAS
    # ========================================================

    @admin.display(
        description="Nombre",
    )
    def full_name_display(
        self,
        obj,
    ):

        full_name = (
            obj.get_full_name()
            .strip()
        )


        return (
            full_name
            or
            "—"
        )


    @admin.display(
        description="Rol",
    )
    def role_display(
        self,
        obj,
    ):

        if obj.is_superuser:
            return "SUPERUSUARIO"


        role = (
            obj.groups
            .filter(
                name__in=SYSTEM_ROLES
            )
            .values_list(
                "name",
                flat=True,
            )
            .first()
        )


        return (
            role
            or
            "SIN ROL"
        )


    @admin.display(
        boolean=True,
        description="Online",
    )
    def online_display(
        self,
        obj,
    ):

        try:

            presence = (
                obj.presence
            )

        except UserPresence.DoesNotExist:

            return False


        return (
            presence.is_online
        )


    @admin.display(
        description="Última actividad",
    )
    def last_seen_display(
        self,
        obj,
    ):

        try:

            presence = (
                obj.presence
            )

        except UserPresence.DoesNotExist:

            return "—"


        return (
            presence.last_seen
        )


# ============================================================
# USER PRESENCE ADMIN
# ============================================================

@admin.register(
    UserPresence
)
class UserPresenceAdmin(
    admin.ModelAdmin
):

    list_display = (
        "user",
        "online_display",
        "last_seen",
        "updated_at",
    )


    list_filter = (
        "online",
    )


    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
    )


    readonly_fields = (
        "user",
        "online",
        "last_seen",
        "updated_at",
    )


    ordering = (
        "-last_seen",
    )


    @admin.display(
        boolean=True,
        description="Online",
    )
    def online_display(
        self,
        obj,
    ):

        return obj.is_online


# ============================================================
# REEMPLAZAR USER ADMIN ORIGINAL
# ============================================================

try:

    admin.site.unregister(
        User
    )

except admin.sites.NotRegistered:

    pass


admin.site.register(
    User,
    SystemUserAdmin,
)