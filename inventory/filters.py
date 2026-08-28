import django_filters

from django.db.models import Q

from .models import Product

from .utils import (
    normalize_text,
)


# ============================================================
# PRODUCTOS
# ============================================================

class ProductFilter(
    django_filters.FilterSet
):

    # --------------------------------------------------------
    # BUSCADOR GENERAL
    # --------------------------------------------------------
    #
    # /products/?q=papel
    #
    # Busca:
    # - descripción
    # - código
    #
    # --------------------------------------------------------

    q = django_filters.CharFilter(
        method="filter_search"
    )


    # --------------------------------------------------------
    # COMPATIBILIDAD
    # --------------------------------------------------------
    #
    # Dejamos también:
    #
    # /products/?search=papel
    #
    # porque tu ViewSet anterior ya utilizaba ese nombre.
    #
    # --------------------------------------------------------

    search = django_filters.CharFilter(
        method="filter_search"
    )


    # --------------------------------------------------------
    # DESCRIPCIÓN
    # --------------------------------------------------------
    #
    # /products/?description=papel
    #
    # --------------------------------------------------------

    description = django_filters.CharFilter(
        method="filter_description"
    )


    # --------------------------------------------------------
    # CÓDIGO
    # --------------------------------------------------------

    code = django_filters.CharFilter(
        field_name="code",
        lookup_expr="icontains",
    )


    # --------------------------------------------------------
    # RELACIONES
    # --------------------------------------------------------

    section = django_filters.NumberFilter(
        field_name="section_id"
    )


    category = django_filters.NumberFilter(
        field_name="category_id"
    )


    unit = django_filters.NumberFilter(
        field_name="unit_id"
    )


    # --------------------------------------------------------
    # ACTIVO
    # --------------------------------------------------------

    active = django_filters.BooleanFilter(
        field_name="active"
    )


    # ========================================================
    # BÚSQUEDA POR DESCRIPCIÓN
    # ========================================================

    def filter_description(
        self,
        queryset,
        name,
        value,
    ):

        value = (
            value
            or ""
        ).strip()


        if not value:

            return queryset


        normalized = (
            normalize_text(
                value
            )
        )


        return queryset.filter(
            normalized_description__icontains=(
                normalized
            )
        )


    # ========================================================
    # BÚSQUEDA GENERAL
    # ========================================================

    def filter_search(
        self,
        queryset,
        name,
        value,
    ):

        value = (
            value
            or ""
        ).strip()


        if not value:

            return queryset


        normalized = (
            normalize_text(
                value
            )
        )


        return queryset.filter(

            Q(
                normalized_description__icontains=(
                    normalized
                )
            )

            |

            Q(
                code__icontains=value
            )

        )


    # ========================================================
    # META
    # ========================================================

    class Meta:

        model = Product

        fields = [
            "section",
            "category",
            "unit",
            "active",
        ]