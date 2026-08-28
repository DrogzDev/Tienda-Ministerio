from decimal import Decimal

from django.db.models import DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce

from .models import Category, Product, Stock, UnitAlias, UnitOfMeasure
from .utils import normalize_text


DECIMAL_OUTPUT = DecimalField(max_digits=14, decimal_places=3)


def get_product_by_code(code):
    if not code:
        return None
    return (
        Product.objects.select_related("section", "category", "unit")
        .filter(code=str(code).strip().upper())
        .first()
    )


def resolve_category(*, section, raw_name):
    normalized = normalize_text(raw_name)
    if not normalized:
        return None
    return (
        Category.objects.filter(
            section=section,
            normalized_name=normalized,
            active=True,
        )
        .first()
    )


def resolve_unit(raw_value):
    normalized = normalize_text(raw_value)
    if not normalized:
        return None

    unit = (
        UnitOfMeasure.objects.filter(active=True)
        .filter(
            Q(normalized_abbreviation=normalized)
            | Q(normalized_name=normalized)
        )
        .first()
    )
    if unit:
        return unit

    alias = (
        UnitAlias.objects.select_related("unit")
        .filter(alias=normalized, unit__active=True)
        .first()
    )
    return alias.unit if alias else None


def find_matching_products(*, section, description, unit):
    """La categoría NO forma parte de la identidad del producto."""
    normalized_description = normalize_text(description)
    if not normalized_description or unit is None:
        return Product.objects.none()

    return (
        Product.objects.select_related("section", "category", "unit")
        .filter(
            section=section,
            normalized_description=normalized_description,
            unit=unit,
            active=True,
        )
        .order_by("id")
    )


def get_inventory_queryset(*, section=None, category=None, warehouse=None,
                            search=None, active_only=True):
    qs = Product.objects.select_related("section", "category", "unit")

    if active_only:
        qs = qs.filter(active=True)
    if section is not None:
        qs = qs.filter(section=section)
    if category is not None:
        qs = qs.filter(category=category)
    if search:
        term = str(search).strip()
        qs = qs.filter(
            Q(code__icontains=term)
            | Q(description__icontains=term)
            | Q(category__name__icontains=term)
        )

    stock_filter = Q(stocks__warehouse=warehouse) if warehouse is not None else Q()

    return qs.annotate(
        total_stock=Coalesce(
            Sum("stocks__quantity", filter=stock_filter),
            Value(Decimal("0")),
            output_field=DECIMAL_OUTPUT,
        )
    ).order_by("section__order", "description")


def get_low_stock_queryset(*, warehouse=None, section=None):
    qs = Stock.objects.select_related(
        "product",
        "product__section",
        "product__category",
        "product__unit",
        "warehouse",
    ).filter(
        product__active=True,
        quantity__lte=F("product__minimum_stock"),
    )

    if warehouse is not None:
        qs = qs.filter(warehouse=warehouse)
    if section is not None:
        qs = qs.filter(product__section=section)

    return qs.order_by("quantity", "product__description")
