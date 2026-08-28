import json
import re

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.db import models, transaction
from django.db.models import Q

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import (
    IsAdministradorOrDirector,
)

from .models import (
    Category,
    InventoryImportBatch,
    InventorySection,
    Product,
    Stock,
    UnitAlias,
    UnitOfMeasure,
    Warehouse,
)

from .utils import normalize_text

from .importers.analyzer import (
    analyze_inventory_excel,
)

from .importers.importer import (
    import_inventory_analysis,
)


ALLOWED_EXTENSIONS = (
    ".xlsx",
    ".xlsm",
)


# ============================================================
# PERMISOS
# ============================================================

class ImportBaseAPIView(APIView):

    permission_classes = [
        IsAdministradorOrDirector,
    ]


# ============================================================
# HELPERS GENERALES
# ============================================================

def _validate_excel_file(
    uploaded_file,
):

    if not uploaded_file:

        return (
            "Debes seleccionar un archivo Excel."
        )

    file_name = (
        uploaded_file.name.lower()
    )

    if not file_name.endswith(
        ALLOWED_EXTENSIONS
    ):

        return (
            "Formato no permitido. "
            "El archivo debe ser .xlsx o .xlsm."
        )

    return None


def _json_safe(
    value,
):

    if value is None:
        return None

    if isinstance(
        value,
        Decimal,
    ):
        return str(value)

    if isinstance(
        value,
        (datetime, date),
    ):
        return value.isoformat()

    if isinstance(
        value,
        models.Model,
    ):

        data = {
            "id": value.pk,
            "label": str(value),
        }

        if hasattr(
            value,
            "code",
        ):
            data["code"] = (
                value.code
            )

        if hasattr(
            value,
            "name",
        ):
            data["name"] = (
                value.name
            )

        if hasattr(
            value,
            "description",
        ):
            data["description"] = (
                value.description
            )

        if hasattr(
            value,
            "abbreviation",
        ):
            data["abbreviation"] = (
                value.abbreviation
            )

        return data

    if isinstance(
        value,
        dict,
    ):

        return {
            str(key): _json_safe(item)
            for key, item
            in value.items()
        }

    if isinstance(
        value,
        (list, tuple, set),
    ):

        return [
            _json_safe(item)
            for item in value
        ]

    return value


def _row_value(
    row,
    *names,
    default=None,
):

    for name in names:

        if name not in row:
            continue

        value = row.get(name)

        if value is not None:
            return value

    return default


def _normalize_messages(
    value,
):

    if not value:
        return []

    if isinstance(
        value,
        str,
    ):
        return [value]

    if isinstance(
        value,
        (list, tuple, set),
    ):

        return [
            str(item)
            for item in value
        ]

    return [
        str(value)
    ]


def _clean_text(
    value,
):

    if value is None:
        return ""

    return " ".join(
        str(value)
        .strip()
        .upper()
        .split()
    )


def _display_value(
    value,
):

    if value is None:
        return ""

    if isinstance(
        value,
        UnitOfMeasure,
    ):
        return value.abbreviation

    if isinstance(
        value,
        models.Model,
    ):

        if hasattr(
            value,
            "name",
        ):
            return value.name

        return str(value)

    return str(value).strip()


def _decimal_value(
    value,
    *,
    field_name,
    allow_zero=False,
):

    if value in (
        None,
        "",
    ):

        if allow_zero:
            return Decimal("0")

        raise ValueError(
            f"{field_name} es obligatorio."
        )

    try:

        decimal_value = Decimal(
            str(value)
            .strip()
            .replace(",", ".")
        )

    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ) as exc:

        raise ValueError(
            f"{field_name} no es válido."
        ) from exc

    if allow_zero:

        if decimal_value < 0:

            raise ValueError(
                (
                    f"{field_name} no puede "
                    "ser negativo."
                )
            )

    else:

        if decimal_value <= 0:

            raise ValueError(
                (
                    f"{field_name} debe ser "
                    "mayor que cero."
                )
            )

    if (
        decimal_value
        .as_tuple()
        .exponent
        < -3
    ):

        raise ValueError(
            (
                f"{field_name} admite "
                "máximo 3 decimales."
            )
        )

    return decimal_value


# ============================================================
# NORMALIZAR ANÁLISIS PARA ANGULAR
# ============================================================

def _normalize_analysis(
    analysis,
):

    raw_summary = (
        analysis.get(
            "summary",
            {},
        )
    )

    rows = []

    for raw_row in analysis.get(
        "rows",
        [],
    ):

        status_value = str(
            _row_value(
                raw_row,
                "status",
                default="ERROR",
            )
        ).upper()


        # ====================================================
        # PRODUCTO EXISTENTE
        # ====================================================

        matched_product = (
            _row_value(
                raw_row,
                "matched_product",
                "product",
            )
        )

        matched_product_id = (
            _row_value(
                raw_row,
                "matched_product_id",
                "product_id",
            )
        )

        matched_product_code = (
            _row_value(
                raw_row,
                "matched_product_code",
            )
        )

        if isinstance(
            matched_product,
            Product,
        ):

            matched_product_id = (
                matched_product.id
            )

            matched_product_code = (
                matched_product.code
            )


        # ====================================================
        # CATEGORÍA
        # ====================================================

        category_value = (
            _row_value(
                raw_row,
                "category_raw",
                "category",
                "categoria",
                default="",
            )
        )

        resolved_category = (
            _row_value(
                raw_row,
                "resolved_category",
                "category_obj",
            )
        )

        category_id = (
            _row_value(
                raw_row,
                "category_id",
            )
        )


        if isinstance(
            category_value,
            Category,
        ):

            category_id = (
                category_value.id
            )

            category_display = (
                category_value.name
            )

        elif isinstance(
            resolved_category,
            Category,
        ):

            category_id = (
                resolved_category.id
            )

            category_display = (
                resolved_category.name
            )

        else:

            category_display = (
                _display_value(
                    category_value
                )
            )


        # ====================================================
        # UNIDAD
        # ====================================================

        unit_value = (
            _row_value(
                raw_row,
                "unit_raw",
                "unit",
                "unidad",
                default="",
            )
        )

        resolved_unit = (
            _row_value(
                raw_row,
                "resolved_unit",
                "unit_obj",
            )
        )

        unit_id = (
            _row_value(
                raw_row,
                "unit_id",
            )
        )


        if isinstance(
            unit_value,
            UnitOfMeasure,
        ):

            unit_id = (
                unit_value.id
            )

            unit_display = (
                unit_value.abbreviation
            )

        elif isinstance(
            resolved_unit,
            UnitOfMeasure,
        ):

            unit_id = (
                resolved_unit.id
            )

            unit_display = (
                resolved_unit.abbreviation
            )

        else:

            unit_display = (
                _display_value(
                    unit_value
                )
            )


        rows.append({

            "row_number": (
                _row_value(
                    raw_row,
                    "row_number",
                    "row",
                )
            ),

            "status": (
                status_value
            ),

            "code": (
                _row_value(
                    raw_row,
                    "code",
                    "product_code",
                    "codigo_producto",
                    default="",
                )
            ),

            "description": (
                _row_value(
                    raw_row,
                    "description",
                    "descripcion",
                    default="",
                )
            ),

            "category": (
                category_display
            ),

            "category_id": (
                category_id
            ),

            "unit": (
                unit_display
            ),

            "unit_id": (
                unit_id
            ),

            "quantity": (
                _json_safe(
                    _row_value(
                        raw_row,
                        "quantity",
                        "cantidad",
                    )
                )
            ),

            "minimum_stock": (
                _json_safe(
                    _row_value(
                        raw_row,
                        "minimum_stock",
                        "stock_minimo",
                    )
                )
            ),

            "matched_product_id": (
                matched_product_id
            ),

            "matched_product_code": (
                matched_product_code
            ),

            "match_method": (
                _row_value(
                    raw_row,
                    "match_method",
                    default="",
                )
            ),

            "warnings": (
                _normalize_messages(
                    _row_value(
                        raw_row,
                        "warnings",
                        default=[],
                    )
                )
            ),

            "errors": (
                _normalize_messages(
                    _row_value(
                        raw_row,
                        "errors",
                        default=[],
                    )
                )
            ),

        })


    def summary_number(
        *names,
        default=0,
    ):

        for name in names:

            if name not in raw_summary:
                continue

            try:

                return int(
                    raw_summary[name]
                    or 0
                )

            except (
                TypeError,
                ValueError,
            ):

                return default

        return default


    total_rows = (
        summary_number(
            "total_rows",
            "total",
            default=len(rows),
        )
    )

    ready_existing = (
        summary_number(
            "ready_existing",
            "existing",
            "matched_products",
        )
    )

    ready_new = (
        summary_number(
            "ready_new",
            "new",
            "new_products",
        )
    )

    review = (
        summary_number(
            "review",
            "reviews",
        )
    )

    errors = (
        summary_number(
            "errors",
            "error",
        )
    )


    # ========================================================
    # CATÁLOGOS FALTANTES
    # ========================================================

    missing_categories = sorted({

        _clean_text(
            row["category"]
        )

        for row in rows

        if (
            row.get("category")
            and
            not row.get(
                "category_id"
            )
        )

    })


    missing_units = sorted({

        _clean_text(
            row["unit"]
        )

        for row in rows

        if (
            row.get("unit")
            and
            not row.get(
                "unit_id"
            )
        )

    })


    can_import = (
        analysis.get(
            "can_import_without_review"
        )
    )

    if can_import is None:

        can_import = (
            review == 0
            and
            errors == 0
        )


    return {

        "summary": {

            "total_rows": (
                total_rows
            ),

            "ready_existing": (
                ready_existing
            ),

            "ready_new": (
                ready_new
            ),

            "review": (
                review
            ),

            "errors": (
                errors
            ),

        },

        "can_import_without_review": (
            bool(can_import)
        ),

        "missing_catalogs": {

            "categories": (
                missing_categories
            ),

            "units": (
                missing_units
            ),

        },

        "rows": rows,
    }


# ============================================================
# RECALCULAR SUMMARY DESPUÉS DE OVERRIDES
# ============================================================

def _refresh_analysis_summary(
    analysis,
):

    rows = analysis.get(
        "rows",
        [],
    )

    ready_new = 0
    ready_existing = 0
    review = 0
    errors = 0

    for row in rows:

        row_status = str(
            row.get(
                "status",
                "ERROR",
            )
        ).upper()

        if row_status == "READY_NEW":
            ready_new += 1

        elif (
            row_status
            ==
            "READY_EXISTING"
        ):
            ready_existing += 1

        elif row_status == "REVIEW":
            review += 1

        else:
            errors += 1


    summary = analysis.setdefault(
        "summary",
        {},
    )

    summary.update({

        "total_rows": len(rows),

        "ready_new": ready_new,

        "ready_existing": (
            ready_existing
        ),

        "review": review,

        "errors": errors,

    })


    analysis[
        "can_import_without_review"
    ] = (
        review == 0
        and
        errors == 0
    )


# ============================================================
# OVERRIDES
# ============================================================

def _parse_overrides(
    request,
):

    raw_overrides = (
        request.data.get(
            "overrides",
            "[]",
        )
    )

    if isinstance(
        raw_overrides,
        list,
    ):

        overrides = (
            raw_overrides
        )

    else:

        if not raw_overrides:
            return []

        try:

            overrides = (
                json.loads(
                    raw_overrides
                )
            )

        except json.JSONDecodeError as exc:

            raise ValueError(
                (
                    "El campo overrides "
                    "no contiene JSON válido."
                )
            ) from exc


    if not isinstance(
        overrides,
        list,
    ):

        raise ValueError(
            (
                "overrides debe ser "
                "una lista."
            )
        )

    return overrides


def _apply_import_overrides(
    *,
    analysis,
    overrides,
    section,
):

    if not overrides:

        return


    rows_by_number = {}

    for row in analysis.get(
        "rows",
        [],
    ):

        row_number = (
            _row_value(
                row,
                "row_number",
                "row",
            )
        )

        if row_number is not None:

            rows_by_number[
                int(row_number)
            ] = row


    used_rows = set()


    for override in overrides:

        if not isinstance(
            override,
            dict,
        ):

            raise ValueError(
                (
                    "Cada modificación debe "
                    "ser un objeto."
                )
            )


        try:

            row_number = int(
                override.get(
                    "row_number"
                )
            )

        except (
            TypeError,
            ValueError,
        ) as exc:

            raise ValueError(
                (
                    "Una modificación contiene "
                    "un número de fila inválido."
                )
            ) from exc


        if row_number in used_rows:

            raise ValueError(
                (
                    f"La fila {row_number} "
                    "está repetida en overrides."
                )
            )


        used_rows.add(
            row_number
        )


        row = rows_by_number.get(
            row_number
        )


        if row is None:

            raise ValueError(
                (
                    f"La fila {row_number} "
                    "no existe en el Excel."
                )
            )


        mode = str(
            override.get(
                "mode",
                "",
            )
        ).strip().upper()


        quantity = _decimal_value(
            override.get(
                "quantity",
                row.get(
                    "quantity"
                ),
            ),
            field_name=(
                f"Cantidad de la fila "
                f"{row_number}"
            ),
            allow_zero=True,
        )


        # ====================================================
        # PRODUCTO EXISTENTE
        # ====================================================

        if mode == "EXISTING":

            product_id = (
                override.get(
                    "product_id"
                )
            )

            try:

                product = (
                    Product.objects
                    .select_related(
                        "section",
                        "category",
                        "unit",
                    )
                    .get(
                        pk=product_id,
                        section=section,
                        active=True,
                    )
                )

            except (
                Product.DoesNotExist,
                TypeError,
                ValueError,
            ) as exc:

                raise ValueError(
                    (
                        f"El producto seleccionado "
                        f"para la fila {row_number} "
                        "no existe o pertenece "
                        "a otra sección."
                    )
                ) from exc


            row.update({

                "status": (
                    "READY_EXISTING"
                ),

                "code": (
                    product.code
                ),

                "product_code": (
                    product.code
                ),

                "description": (
                    product.description
                ),

                "matched_product": (
                    product
                ),

                "product": (
                    product
                ),

                "matched_product_id": (
                    product.id
                ),

                "product_id": (
                    product.id
                ),

                "matched_product_code": (
                    product.code
                ),

                "match_method": (
                    "USER_SELECTED"
                ),

                "category_raw": (
                    product.category.name
                    if product.category
                    else ""
                ),

                "category": (
                    product.category
                ),

                "category_id": (
                    product.category_id
                ),

                "resolved_category": (
                    product.category
                ),

                "unit_raw": (
                    product
                    .unit
                    .abbreviation
                ),

                "unit": (
                    product.unit
                ),

                "unit_id": (
                    product.unit_id
                ),

                "resolved_unit": (
                    product.unit
                ),

                "quantity": (
                    quantity
                ),

                "minimum_stock": (
                    product.minimum_stock
                ),

                "warnings": [],

                "errors": [],

            })

            continue


        # ====================================================
        # PRODUCTO NUEVO
        # ====================================================

        if mode != "NEW":

            raise ValueError(
                (
                    f"La fila {row_number} "
                    "debe indicar mode NEW "
                    "o EXISTING."
                )
            )


        description = _clean_text(
            override.get(
                "description",
                row.get(
                    "description",
                    "",
                ),
            )
        )


        if not description:

            raise ValueError(
                (
                    f"La descripción de la "
                    f"fila {row_number} "
                    "es obligatoria."
                )
            )


        category_id = (
            override.get(
                "category_id"
            )
        )


        try:

            category = (
                Category.objects
                .get(
                    pk=category_id,
                    section=section,
                    active=True,
                )
            )

        except (
            Category.DoesNotExist,
            TypeError,
            ValueError,
        ) as exc:

            raise ValueError(
                (
                    f"La categoría seleccionada "
                    f"en la fila {row_number} "
                    "no es válida."
                )
            ) from exc


        unit_id = (
            override.get(
                "unit_id"
            )
        )


        try:

            unit = (
                UnitOfMeasure.objects
                .get(
                    pk=unit_id,
                    active=True,
                )
            )

        except (
            UnitOfMeasure.DoesNotExist,
            TypeError,
            ValueError,
        ) as exc:

            raise ValueError(
                (
                    f"La unidad seleccionada "
                    f"en la fila {row_number} "
                    "no es válida."
                )
            ) from exc


        minimum_stock = (
            _decimal_value(
                override.get(
                    "minimum_stock",
                    row.get(
                        "minimum_stock",
                        0,
                    ),
                ),
                field_name=(
                    f"Stock mínimo de la "
                    f"fila {row_number}"
                ),
                allow_zero=True,
            )
        )


        optional_code = _clean_text(
            override.get(
                "code",
                row.get(
                    "code",
                    "",
                ),
            )
        )


        row.update({

            "status": (
                "READY_NEW"
            ),

            "code": (
                optional_code
            ),

            "product_code": (
                optional_code
            ),

            "description": (
                description
            ),

            "matched_product": (
                None
            ),

            "product": (
                None
            ),

            "matched_product_id": (
                None
            ),

            "product_id": (
                None
            ),

            "matched_product_code": (
                None
            ),

            "match_method": (
                "USER_NEW"
            ),

            "category_raw": (
                category.name
            ),

            "category": (
                category
            ),

            "category_id": (
                category.id
            ),

            "resolved_category": (
                category
            ),

            "unit_raw": (
                unit.abbreviation
            ),

            "unit": (
                unit
            ),

            "unit_id": (
                unit.id
            ),

            "resolved_unit": (
                unit
            ),

            "quantity": (
                quantity
            ),

            "minimum_stock": (
                minimum_stock
            ),

            "warnings": [],

            "errors": [],

        })


    _refresh_analysis_summary(
        analysis
    )


# ============================================================
# CATÁLOGOS PARA ANGULAR
# ============================================================

class ImportCatalogsAPIView(
    ImportBaseAPIView
):

    def get(
        self,
        request,
    ):

        sections = (
            InventorySection.objects
            .filter(
                active=True
            )
            .order_by(
                "order",
                "name",
            )
        )


        warehouses = (
            Warehouse.objects
            .filter(
                active=True
            )
            .order_by(
                "name"
            )
        )


        categories = (
            Category.objects
            .filter(
                active=True
            )
            .select_related(
                "section"
            )
            .order_by(
                "section__order",
                "section__name",
                "order",
                "name",
            )
        )


        units = (
            UnitOfMeasure.objects
            .filter(
                active=True
            )
            .order_by(
                "name"
            )
        )


        return Response({

            "sections": [

                {
                    "id": (
                        section.id
                    ),

                    "name": (
                        section.name
                    ),

                    "code": (
                        section.code
                    ),
                }

                for section
                in sections
            ],


            "warehouses": [

                {
                    "id": (
                        warehouse.id
                    ),

                    "name": (
                        warehouse.name
                    ),

                    "location": (
                        warehouse.location
                    ),
                }

                for warehouse
                in warehouses
            ],


            "categories": [

                {
                    "id": (
                        category.id
                    ),

                    "name": (
                        category.name
                    ),

                    "section_id": (
                        category.section_id
                    ),

                    "section_name": (
                        category.section.name
                    ),
                }

                for category
                in categories
            ],


            "units": [

                {
                    "id": (
                        unit.id
                    ),

                    "name": (
                        unit.name
                    ),

                    "abbreviation": (
                        unit.abbreviation
                    ),
                }

                for unit
                in units
            ],

        })


# ============================================================
# ANALIZAR EXCEL
# ============================================================

class InventoryImportAnalyzeAPIView(
    ImportBaseAPIView
):

    def post(
        self,
        request,
    ):

        uploaded_file = (
            request.FILES.get(
                "file"
            )
        )

        section_id = (
            request.data.get(
                "section"
            )
        )

        warehouse_id = (
            request.data.get(
                "warehouse"
            )
        )


        file_error = (
            _validate_excel_file(
                uploaded_file
            )
        )


        if file_error:

            return Response(
                {
                    "detail": (
                        file_error
                    )
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )


        try:

            section = (
                InventorySection.objects
                .get(
                    pk=section_id,
                    active=True,
                )
            )

            warehouse = (
                Warehouse.objects
                .get(
                    pk=warehouse_id,
                    active=True,
                )
            )

        except (
            InventorySection.DoesNotExist,
            Warehouse.DoesNotExist,
            TypeError,
            ValueError,
        ):

            return Response(
                {
                    "detail": (
                        "Sección o almacén "
                        "no válido."
                    )
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )


        try:

            uploaded_file.seek(0)

            analysis = (
                analyze_inventory_excel(
                    file_or_path=(
                        uploaded_file
                    ),
                    section=section,
                )
            )

        except Exception as exc:

            return Response(
                {
                    "detail": (
                        "No se pudo analizar "
                        f"el Excel: {exc}"
                    )
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )


        return Response({

            "file": {
                "name": (
                    uploaded_file.name
                ),
                "size": (
                    uploaded_file.size
                ),
            },

            "section": {
                "id": section.id,
                "name": section.name,
            },

            "warehouse": {
                "id": warehouse.id,
                "name": warehouse.name,
            },

            "analysis": (
                _normalize_analysis(
                    analysis
                )
            ),

        })


# ============================================================
# BUSCAR PRODUCTOS EXISTENTES
# ============================================================

class InventoryImportProductLookupAPIView(
    ImportBaseAPIView
):

    def get(
        self,
        request,
    ):

        query = (
            request.query_params
            .get(
                "q",
                "",
            )
            .strip()
        )

        section_id = (
            request.query_params
            .get(
                "section"
            )
        )

        warehouse_id = (
            request.query_params
            .get(
                "warehouse"
            )
        )


        if not section_id:

            return Response(
                {
                    "detail": (
                        "Debes indicar "
                        "la sección."
                    )
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )


        try:

            section = (
                InventorySection.objects
                .get(
                    pk=section_id,
                    active=True,
                )
            )

        except (
            InventorySection.DoesNotExist,
            TypeError,
            ValueError,
        ):

            return Response(
                {
                    "detail": (
                        "La sección no es válida."
                    )
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )


        if not query:

            return Response({
                "results": []
            })


        products = (
            Product.objects
            .filter(
                section=section,
                active=True,
            )
            .filter(
                Q(
                    code__icontains=query
                )
                |
                Q(
                    description__icontains=query
                )
            )
            .select_related(
                "section",
                "category",
                "unit",
            )
            .order_by(
                "description"
            )[:20]
        )


        products = list(
            products
        )


        product_ids = [
            product.id
            for product
            in products
        ]


        stock_queryset = (
            Stock.objects
            .filter(
                product_id__in=(
                    product_ids
                )
            )
        )


        if warehouse_id:

            stock_queryset = (
                stock_queryset
                .filter(
                    warehouse_id=(
                        warehouse_id
                    )
                )
            )


        stock_map = {}


        for stock in stock_queryset:

            current = (
                stock_map.get(
                    stock.product_id,
                    Decimal("0"),
                )
            )

            stock_map[
                stock.product_id
            ] = (
                current
                +
                stock.quantity
            )


        results = []


        for product in products:

            available = (
                stock_map.get(
                    product.id,
                    Decimal("0"),
                )
            )


            results.append({

                "id": (
                    product.id
                ),

                "code": (
                    product.code
                ),

                "description": (
                    product.description
                ),

                "section_id": (
                    product.section_id
                ),

                "section": (
                    product.section.name
                ),

                "category_id": (
                    product.category_id
                ),

                "category": (
                    product.category.name
                    if product.category
                    else None
                ),

                "unit_id": (
                    product.unit_id
                ),

                "unit": (
                    product
                    .unit
                    .abbreviation
                ),

                "unit_name": (
                    product.unit.name
                ),

                "minimum_stock": (
                    str(
                        product.minimum_stock
                    )
                ),

                "available": (
                    str(available)
                ),

            })


        return Response({
            "results": results
        })


# ============================================================
# CREAR CATÁLOGOS FALTANTES
# ============================================================

class InventoryImportCompleteCatalogsAPIView(
    ImportBaseAPIView
):

    def post(
        self,
        request,
    ):

        section_id = (
            request.data.get(
                "section"
            )
        )

        categories = (
            request.data.get(
                "categories",
                [],
            )
        )

        units = (
            request.data.get(
                "units",
                [],
            )
        )


        try:

            section = (
                InventorySection.objects
                .get(
                    pk=section_id,
                    active=True,
                )
            )

        except (
            InventorySection.DoesNotExist,
            TypeError,
            ValueError,
        ):

            return Response(
                {
                    "detail": (
                        "La sección seleccionada "
                        "no existe o está inactiva."
                    )
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )


        if not isinstance(
            categories,
            list,
        ):

            return Response(
                {
                    "detail": (
                        "categories debe "
                        "ser una lista."
                    )
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )


        if not isinstance(
            units,
            list,
        ):

            return Response(
                {
                    "detail": (
                        "units debe "
                        "ser una lista."
                    )
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )


        created_categories = []
        existing_categories = []

        created_units = []
        existing_units = []

        created_aliases = []


        try:

            with transaction.atomic():

                # ============================================
                # CATEGORÍAS
                # ============================================

                for raw_category in categories:

                    name = (
                        _clean_text(
                            raw_category
                        )
                    )

                    if not name:
                        continue


                    normalized_name = (
                        normalize_text(
                            name
                        )
                    )


                    category = (
                        Category.objects
                        .filter(
                            section=section,
                            normalized_name=(
                                normalized_name
                            ),
                        )
                        .first()
                    )


                    if category:

                        existing_categories.append({
                            "id": category.id,
                            "name": category.name,
                        })

                        continue


                    category = (
                        Category.objects
                        .create(
                            section=section,
                            name=name,
                        )
                    )


                    created_categories.append({
                        "id": category.id,
                        "name": category.name,
                    })


                # ============================================
                # UNIDADES
                # ============================================

                processed_units = set()


                for raw_unit in units:

                    raw_unit = (
                        _clean_text(
                            raw_unit
                        )
                    )

                    if not raw_unit:
                        continue


                    (
                        canonical_name,
                        abbreviation,
                        aliases,
                    ) = (
                        self._resolve_unit(
                            raw_unit
                        )
                    )


                    key = (
                        normalize_text(
                            abbreviation
                        )
                    )


                    if key in processed_units:
                        continue


                    processed_units.add(
                        key
                    )


                    unit = (
                        UnitOfMeasure.objects
                        .filter(
                            normalized_abbreviation=(
                                key
                            )
                        )
                        .first()
                    )


                    if not unit:

                        unit = (
                            UnitOfMeasure.objects
                            .create(
                                name=(
                                    canonical_name
                                ),
                                abbreviation=(
                                    abbreviation
                                ),
                            )
                        )


                        created_units.append({
                            "id": unit.id,
                            "name": unit.name,
                            "abbreviation": (
                                unit.abbreviation
                            ),
                        })

                    else:

                        existing_units.append({
                            "id": unit.id,
                            "name": unit.name,
                            "abbreviation": (
                                unit.abbreviation
                            ),
                        })


                    aliases_to_create = (
                        set(aliases)
                        |
                        {raw_unit}
                    )


                    self._create_aliases(
                        unit=unit,
                        aliases=(
                            aliases_to_create
                        ),
                        created_aliases=(
                            created_aliases
                        ),
                    )


        except Exception as exc:

            return Response(
                {
                    "detail": (
                        "No se pudieron crear "
                        "los elementos faltantes. "
                        f"{exc}"
                    )
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )


        return Response(
            {

                "detail": (
                    "Los elementos faltantes "
                    "fueron creados correctamente."
                ),

                "created": {

                    "categories": (
                        created_categories
                    ),

                    "units": (
                        created_units
                    ),

                    "aliases": (
                        created_aliases
                    ),

                },

                "existing": {

                    "categories": (
                        existing_categories
                    ),

                    "units": (
                        existing_units
                    ),

                },

            },
            status=(
                status.HTTP_201_CREATED
            ),
        )


    def _resolve_unit(
        self,
        raw_unit,
    ):

        value = (
            _clean_text(
                raw_unit
            )
            .replace(
                ".",
                " ",
            )
        )

        value = " ".join(
            value.split()
        )


        mappings = {

            "UND": (
                "UNIDAD",
                "UND",
                {
                    "UNID",
                    "UNIDAD",
                    "UNIDADES",
                },
            ),

            "UNID": (
                "UNIDAD",
                "UND",
                {
                    "UNID",
                    "UNIDAD",
                    "UNIDADES",
                },
            ),

            "UNIDAD": (
                "UNIDAD",
                "UND",
                {
                    "UNID",
                    "UNIDAD",
                    "UNIDADES",
                },
            ),

            "UNIDADES": (
                "UNIDAD",
                "UND",
                {
                    "UNID",
                    "UNIDAD",
                    "UNIDADES",
                },
            ),

            "KG": (
                "KILOGRAMO",
                "KG",
                {
                    "KILO",
                    "KILOS",
                    "KILOGRAMO",
                    "KILOGRAMOS",
                },
            ),

            "KILO": (
                "KILOGRAMO",
                "KG",
                {
                    "KILO",
                    "KILOS",
                    "KILOGRAMO",
                    "KILOGRAMOS",
                },
            ),

            "KILOS": (
                "KILOGRAMO",
                "KG",
                {
                    "KILO",
                    "KILOS",
                    "KILOGRAMO",
                    "KILOGRAMOS",
                },
            ),

            "PAQ": (
                "PAQUETE",
                "PAQ",
                {
                    "PAQUETE",
                    "PAQUETES",
                },
            ),

            "PAQUETE": (
                "PAQUETE",
                "PAQ",
                {
                    "PAQUETE",
                    "PAQUETES",
                },
            ),

            "PAQUETES": (
                "PAQUETE",
                "PAQ",
                {
                    "PAQUETE",
                    "PAQUETES",
                },
            ),

            "CAJA": (
                "CAJA",
                "CAJA",
                {
                    "CAJAS",
                },
            ),

            "CAJAS": (
                "CAJA",
                "CAJA",
                {
                    "CAJAS",
                },
            ),

            "PAR": (
                "PAR",
                "PAR",
                {
                    "PARES",
                },
            ),

            "PARES": (
                "PAR",
                "PAR",
                {
                    "PARES",
                },
            ),

            "LITRO": (
                "LITRO",
                "LITROS",
                {
                    "LT",
                    "LTS",
                    "LITRO",
                },
            ),

            "LITROS": (
                "LITRO",
                "LITROS",
                {
                    "LT",
                    "LTS",
                    "LITRO",
                },
            ),

            "GALON": (
                "GALÓN",
                "GALON",
                {
                    "GALÓN",
                    "GALONES",
                },
            ),

            "GALÓN": (
                "GALÓN",
                "GALON",
                {
                    "GALÓN",
                    "GALONES",
                },
            ),

            "POTE": (
                "POTE",
                "POTE",
                {
                    "POTES",
                },
            ),

            "SOBRE": (
                "SOBRE",
                "SOBRE",
                {
                    "SOBRES",
                },
            ),

            "METRO": (
                "METRO",
                "METROS",
                {
                    "METRO",
                    "MTS",
                },
            ),

            "METROS": (
                "METRO",
                "METROS",
                {
                    "METRO",
                    "MTS",
                },
            ),

        }


        if value in mappings:

            return mappings[
                value
            ]


        package_match = re.match(
            (
                r"^(?:PAQ|PAQUETE)"
                r"\s*X?\s*(\d+)$"
            ),
            value,
        )


        if package_match:

            amount = (
                package_match
                .group(1)
            )

            return (
                f"PAQUETE X{amount}",
                f"PAQ X{amount}",
                set(),
            )


        return (
            value,
            value,
            set(),
        )


    def _create_aliases(
        self,
        *,
        unit,
        aliases,
        created_aliases,
    ):

        for raw_alias in aliases:

            alias = (
                normalize_text(
                    _clean_text(
                        raw_alias
                    )
                )
            )


            if not alias:
                continue


            if (
                alias
                ==
                unit.normalized_abbreviation
            ):
                continue


            existing = (
                UnitAlias.objects
                .filter(
                    alias=alias
                )
                .first()
            )


            if existing:

                if (
                    existing.unit_id
                    !=
                    unit.id
                ):

                    raise ValueError(
                        (
                            f"El alias "
                            f"'{raw_alias}' "
                            "ya pertenece "
                            "a otra unidad."
                        )
                    )

                continue


            unit_alias = (
                UnitAlias.objects
                .create(
                    unit=unit,
                    alias=alias,
                )
            )


            created_aliases.append({

                "id": (
                    unit_alias.id
                ),

                "alias": (
                    unit_alias.alias
                ),

                "unit_id": (
                    unit.id
                ),

                "unit": (
                    unit.abbreviation
                ),

            })


# ============================================================
# CONFIRMAR IMPORTACIÓN
# ============================================================

class InventoryImportConfirmAPIView(
    ImportBaseAPIView
):

    def post(
        self,
        request,
    ):

        uploaded_file = (
            request.FILES.get(
                "file"
            )
        )

        section_id = (
            request.data.get(
                "section"
            )
        )

        warehouse_id = (
            request.data.get(
                "warehouse"
            )
        )


        file_error = (
            _validate_excel_file(
                uploaded_file
            )
        )


        if file_error:

            return Response(
                {
                    "detail": file_error
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )


        try:

            section = (
                InventorySection.objects
                .get(
                    pk=section_id,
                    active=True,
                )
            )

            warehouse = (
                Warehouse.objects
                .get(
                    pk=warehouse_id,
                    active=True,
                )
            )

        except (
            InventorySection.DoesNotExist,
            Warehouse.DoesNotExist,
            TypeError,
            ValueError,
        ):

            return Response(
                {
                    "detail": (
                        "Sección o almacén "
                        "no válido."
                    )
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )


        try:

            # =================================================
            # 1. REANALIZAMOS EL EXCEL ORIGINAL
            # =================================================

            uploaded_file.seek(0)


            analysis = (
                analyze_inventory_excel(
                    file_or_path=(
                        uploaded_file
                    ),
                    section=section,
                )
            )


            # =================================================
            # 2. APLICAMOS CAMBIOS DEL ADMINISTRADOR/DIRECTOR
            # =================================================

            overrides = (
                _parse_overrides(
                    request
                )
            )


            _apply_import_overrides(
                analysis=analysis,
                overrides=overrides,
                section=section,
            )


            # =================================================
            # 3. VALIDAMOS EL RESULTADO FINAL
            # =================================================

            normalized = (
                _normalize_analysis(
                    analysis
                )
            )


            if not normalized[
                "can_import_without_review"
            ]:

                return Response(
                    {

                        "detail": (
                            "La carga todavía "
                            "contiene filas con "
                            "errores o pendientes "
                            "de revisión."
                        ),

                        "analysis": (
                            normalized
                        ),

                    },
                    status=(
                        status
                        .HTTP_409_CONFLICT
                    ),
                )


            user = request.user


            # =================================================
            # 4. IMPORTAMOS
            # =================================================

            result = (
                import_inventory_analysis(
                    analysis=analysis,
                    section=section,
                    warehouse=warehouse,
                    user=user,
                    original_filename=(
                        uploaded_file.name
                    ),
                )
            )


        except Exception as exc:

            return Response(
                {
                    "detail": (
                        "No se pudo completar "
                        "la importación: "
                        f"{exc}"
                    )
                },
                status=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
            )


        if isinstance(
            result,
            InventoryImportBatch,
        ):

            payload = {

                "batch_id": (
                    result.id
                ),

                "status": (
                    result.status
                ),

                "total_rows": (
                    result.total_rows
                ),

                "created_products": (
                    result.created_products
                ),

                "matched_products": (
                    result.matched_products
                ),

                "movements_created": (
                    result.movements_created
                ),

                "skipped_rows": (
                    result.skipped_rows
                ),

            }

        else:

            payload = (
                _json_safe(
                    result
                )
            )


        return Response(
            {

                "detail": (
                    "Inventario importado "
                    "correctamente."
                ),

                "result": (
                    payload
                ),

            },
            status=(
                status.HTTP_201_CREATED
            ),
        )