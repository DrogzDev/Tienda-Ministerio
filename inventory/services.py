from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from .models import (
    InventoryImportBatch,
    Product,
    Stock,
    StockMovement,
    Warehouse,
)
from .utils import parse_decimal


class InventoryError(Exception):
    pass


class InsufficientStockError(InventoryError):
    pass


class InactiveProductError(InventoryError):
    pass


class InactiveWarehouseError(InventoryError):
    pass


class ImportReversalError(InventoryError):
    pass


def _validate_product(product):
    if not isinstance(product, Product):
        raise ValidationError(
            "Debe suministrar un producto válido."
        )

    if not product.active:
        raise InactiveProductError(
            f"El producto '{product.description}' está inactivo."
        )


def _validate_warehouse(warehouse):
    if not isinstance(warehouse, Warehouse):
        raise ValidationError(
            "Debe suministrar un almacén físico válido."
        )

    if not warehouse.active:
        raise InactiveWarehouseError(
            f"El almacén '{warehouse.name}' está inactivo."
        )


def _get_locked_stock(*, product, warehouse):
    """
    Obtiene/bloquea el stock para evitar carreras en PostgreSQL.
    """

    try:
        return (
            Stock.objects
            .select_for_update()
            .get(
                product=product,
                warehouse=warehouse,
            )
        )

    except Stock.DoesNotExist:
        try:
            Stock.objects.create(
                product=product,
                warehouse=warehouse,
                quantity=Decimal("0"),
            )

        except IntegrityError:
            # Otro proceso pudo crear la fila al mismo tiempo.
            pass

        return (
            Stock.objects
            .select_for_update()
            .get(
                product=product,
                warehouse=warehouse,
            )
        )


def _create_movement(
    *,
    product,
    warehouse,
    movement_type,
    quantity,
    previous_stock,
    resulting_stock,
    user,
    source,
    reference,
    notes,
    is_historical,
    import_batch,
    reversal_of=None,
):
    return StockMovement.objects.create(
        product=product,
        warehouse=warehouse,
        movement_type=movement_type,
        quantity=quantity,
        previous_stock=previous_stock,
        resulting_stock=resulting_stock,
        product_code_snapshot=product.code or "",
        product_description_snapshot=product.description,
        unit_snapshot=product.unit.abbreviation,
        source=source,
        reference=(reference or "").strip(),
        notes=(notes or "").strip(),
        created_by=user,
        import_batch=import_batch,
        reversal_of=reversal_of,
        is_historical=is_historical,
    )


@transaction.atomic
def register_entry(
    *,
    product,
    warehouse,
    quantity,
    user=None,
    source=StockMovement.SourceType.MANUAL,
    reference="",
    notes="",
    is_historical=False,
    import_batch=None,
):
    _validate_product(product)
    _validate_warehouse(warehouse)

    quantity = parse_decimal(
        quantity,
        field_name="Cantidad",
        allow_zero=False,
    )

    stock = _get_locked_stock(
        product=product,
        warehouse=warehouse,
    )

    previous_stock = stock.quantity
    resulting_stock = previous_stock + quantity

    stock.quantity = resulting_stock
    stock.save(
        update_fields=[
            "quantity",
            "updated_at",
        ]
    )

    return _create_movement(
        product=product,
        warehouse=warehouse,
        movement_type=StockMovement.MovementType.ENTRY,
        quantity=quantity,
        previous_stock=previous_stock,
        resulting_stock=resulting_stock,
        user=user,
        source=source,
        reference=reference,
        notes=notes,
        is_historical=is_historical,
        import_batch=import_batch,
    )


@transaction.atomic
def register_exit(
    *,
    product,
    warehouse,
    quantity,
    user=None,
    source=StockMovement.SourceType.MANUAL,
    reference="",
    notes="",
    is_historical=False,
    import_batch=None,
):
    _validate_product(product)
    _validate_warehouse(warehouse)

    quantity = parse_decimal(
        quantity,
        field_name="Cantidad",
        allow_zero=False,
    )

    stock = _get_locked_stock(
        product=product,
        warehouse=warehouse,
    )

    previous_stock = stock.quantity

    if quantity > previous_stock:
        raise InsufficientStockError(
            f"Stock insuficiente para '{product.description}'. "
            f"Disponible: {previous_stock} {product.unit.abbreviation}. "
            f"Solicitado: {quantity} {product.unit.abbreviation}."
        )

    resulting_stock = previous_stock - quantity

    stock.quantity = resulting_stock
    stock.save(
        update_fields=[
            "quantity",
            "updated_at",
        ]
    )

    return _create_movement(
        product=product,
        warehouse=warehouse,
        movement_type=StockMovement.MovementType.EXIT,
        quantity=quantity,
        previous_stock=previous_stock,
        resulting_stock=resulting_stock,
        user=user,
        source=source,
        reference=reference,
        notes=notes,
        is_historical=is_historical,
        import_batch=import_batch,
    )


@transaction.atomic
def register_adjustment_in(
    *,
    product,
    warehouse,
    quantity,
    user=None,
    reference="",
    notes="",
):
    _validate_product(product)
    _validate_warehouse(warehouse)

    quantity = parse_decimal(
        quantity,
        field_name="Cantidad",
        allow_zero=False,
    )

    stock = _get_locked_stock(
        product=product,
        warehouse=warehouse,
    )

    previous_stock = stock.quantity
    resulting_stock = previous_stock + quantity

    stock.quantity = resulting_stock
    stock.save(
        update_fields=[
            "quantity",
            "updated_at",
        ]
    )

    return _create_movement(
        product=product,
        warehouse=warehouse,
        movement_type=StockMovement.MovementType.ADJUSTMENT_IN,
        quantity=quantity,
        previous_stock=previous_stock,
        resulting_stock=resulting_stock,
        user=user,
        source=StockMovement.SourceType.MANUAL,
        reference=reference,
        notes=notes,
        is_historical=False,
        import_batch=None,
    )


@transaction.atomic
def register_adjustment_out(
    *,
    product,
    warehouse,
    quantity,
    user=None,
    reference="",
    notes="",
):
    _validate_product(product)
    _validate_warehouse(warehouse)

    quantity = parse_decimal(
        quantity,
        field_name="Cantidad",
        allow_zero=False,
    )

    stock = _get_locked_stock(
        product=product,
        warehouse=warehouse,
    )

    previous_stock = stock.quantity

    if quantity > previous_stock:
        raise InsufficientStockError(
            "No se puede realizar el ajuste. "
            f"Disponible: {previous_stock} "
            f"{product.unit.abbreviation}."
        )

    resulting_stock = previous_stock - quantity

    stock.quantity = resulting_stock
    stock.save(
        update_fields=[
            "quantity",
            "updated_at",
        ]
    )

    return _create_movement(
        product=product,
        warehouse=warehouse,
        movement_type=StockMovement.MovementType.ADJUSTMENT_OUT,
        quantity=quantity,
        previous_stock=previous_stock,
        resulting_stock=resulting_stock,
        user=user,
        source=StockMovement.SourceType.MANUAL,
        reference=reference,
        notes=notes,
        is_historical=False,
        import_batch=None,
    )


def get_stock(*, product, warehouse):
    quantity = (
        Stock.objects
        .filter(
            product=product,
            warehouse=warehouse,
        )
        .values_list(
            "quantity",
            flat=True,
        )
        .first()
    )

    return (
        quantity
        if quantity is not None
        else Decimal("0")
    )


@transaction.atomic
def create_manual_product(
    *,
    description,
    section,
    category,
    unit,
    warehouse,
    quantity_entry,
    code="",
    user=None,
    product=None,
):

    # ========================================================
    # PRODUCTO EXISTENTE
    # ========================================================

    if product is not None:

        _validate_product(
            product
        )

        _validate_warehouse(
            warehouse
        )


        if (
            quantity_entry
            <=
            Decimal("0")
        ):

            raise InventoryError(
                "La cantidad de entrada debe ser mayor a cero."
            )


        movement = register_entry(
            product=product,
            warehouse=warehouse,
            quantity=quantity_entry,
            user=user,
            reference=(
                "ENTRADA MANUAL"
            ),
            notes=(
                "Entrada agregada desde "
                "Agregar productos."
            ),
        )


        return (
            product,
            movement,
            False,
        )


    # ========================================================
    # PRODUCTO NUEVO
    # ========================================================

    product = Product(
        description=description,
        section=section,
        category=category,
        unit=unit,
    )


    if code:

        product.code = (
            code
        )


    product.save()


    movement = None


    # ========================================================
    # ENTRADA INICIAL
    # ========================================================

    if (
        quantity_entry
        >
        Decimal("0")
    ):

        movement = register_entry(
            product=product,
            warehouse=warehouse,
            quantity=quantity_entry,
            user=user,
            reference=(
                "CARGA MANUAL INICIAL"
            ),
            notes=(
                "Creación manual del producto."
            ),
        )


    else:

        Stock.objects.get_or_create(
            product=product,
            warehouse=warehouse,
            defaults={
                "quantity":
                    Decimal("0")
            },
        )


    return (
        product,
        movement,
        True,
    )

# ============================================================
# ANULACIÓN DE IMPORTACIÓN EXCEL
# ============================================================

@transaction.atomic
def reverse_import_batch(
    *,
    batch,
    user,
    reason,
):
    """
    Revierte por completo una importación Excel ya completada.

    Reglas:
    - solo se revierte un lote COMPLETED;
    - nunca se borra el lote ni sus movimientos originales;
    - valida TODO el stock antes de modificar una sola existencia;
    - crea un ADJUSTMENT_OUT por cada ENTRY original;
    - cada movimiento de reversión queda relacionado mediante reversal_of;
    - si una sola fila no puede revertirse, toda la operación hace rollback.
    """

    if not isinstance(
        batch,
        InventoryImportBatch,
    ):
        raise ImportReversalError(
            "Debe suministrar una importación válida."
        )

    reason = (
        reason
        or
        ""
    ).strip()

    if not reason:
        raise ImportReversalError(
            "Debes indicar el motivo de la anulación."
        )

    # Volvemos a obtener el lote bloqueado para evitar que dos
    # solicitudes intenten anularlo al mismo tiempo.
    batch = (
        InventoryImportBatch.objects
        .select_for_update()
        .select_related(
            "section",
            "warehouse",
            "imported_by",
            "reversed_by",
        )
        .get(
            pk=batch.pk
        )
    )

    if (
        batch.status
        ==
        InventoryImportBatch.Status.REVERSED
    ):
        raise ImportReversalError(
            "Esta importación ya fue anulada."
        )

    if (
        batch.status
        !=
        InventoryImportBatch.Status.COMPLETED
    ):
        raise ImportReversalError(
            "Solo se pueden anular importaciones completadas."
        )

    # Movimientos que realmente agregaron existencia mediante Excel.
    original_movements = list(
        StockMovement.objects
        .select_for_update()
        .select_related(
            "product",
            "product__unit",
            "warehouse",
        )
        .filter(
            import_batch=batch,
            source=StockMovement.SourceType.EXCEL,
            movement_type=StockMovement.MovementType.ENTRY,
            reversal_of__isnull=True,
        )
        .order_by(
            "product_id",
            "warehouse_id",
            "id",
        )
    )

    if not original_movements:
        raise ImportReversalError(
            "Esta importación no tiene movimientos de entrada para revertir."
        )

    # Evita una anulación parcial o una segunda anulación si por algún
    # motivo el estado del lote no refleja todavía movimientos revertidos.
    original_ids = [
        movement.id
        for movement in original_movements
    ]

    if (
        StockMovement.objects
        .filter(
            reversal_of_id__in=original_ids
        )
        .exists()
    ):
        raise ImportReversalError(
            "La importación ya contiene movimientos de anulación."
        )

    # ========================================================
    # VALIDACIÓN GLOBAL DE STOCK
    # ========================================================
    #
    # Primero sumamos cuánto debe quitarse por producto/almacén.
    # No se modifica nada hasta verificar todos los grupos.
    # ========================================================

    totals = list(
        StockMovement.objects
        .filter(
            id__in=original_ids
        )
        .values(
            "product_id",
            "warehouse_id",
        )
        .annotate(
            quantity_to_reverse=Sum(
                "quantity"
            )
        )
        .order_by(
            "product_id",
            "warehouse_id",
        )
    )

    locked_stocks = {}

    for total in totals:

        product_id = total[
            "product_id"
        ]

        warehouse_id = total[
            "warehouse_id"
        ]

        quantity_to_reverse = (
            total[
                "quantity_to_reverse"
            ]
            or
            Decimal("0")
        )

        try:
            stock = (
                Stock.objects
                .select_for_update()
                .select_related(
                    "product",
                    "product__unit",
                    "warehouse",
                )
                .get(
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                )
            )

        except Stock.DoesNotExist:
            raise ImportReversalError(
                "No existe la fila de stock necesaria para "
                "revertir uno de los productos de la importación."
            )

        if (
            quantity_to_reverse
            >
            stock.quantity
        ):
            raise InsufficientStockError(
                "No se puede anular la importación porque el producto "
                f"'{stock.product.description}' ya no tiene suficiente "
                "existencia en "
                f"'{stock.warehouse.name}'. "
                f"Disponible actual: {stock.quantity} "
                f"{stock.product.unit.abbreviation}. "
                f"Necesario para revertir: {quantity_to_reverse} "
                f"{stock.product.unit.abbreviation}."
            )

        locked_stocks[
            (
                product_id,
                warehouse_id,
            )
        ] = stock

    # ========================================================
    # REVERSIÓN
    # ========================================================

    reversal_movements = []

    for original in original_movements:

        stock = locked_stocks[
            (
                original.product_id,
                original.warehouse_id,
            )
        ]

        previous_stock = (
            stock.quantity
        )

        resulting_stock = (
            previous_stock
            -
            original.quantity
        )

        # Esta comprobación no debería fallar porque validamos
        # previamente los totales, pero se mantiene por seguridad.
        if (
            resulting_stock
            <
            Decimal("0")
        ):
            raise InsufficientStockError(
                "La anulación produciría una existencia negativa."
            )

        stock.quantity = (
            resulting_stock
        )

        stock.save(
            update_fields=[
                "quantity",
                "updated_at",
            ]
        )

        reversal = _create_movement(
            product=original.product,
            warehouse=original.warehouse,
            movement_type=(
                StockMovement
                .MovementType
                .ADJUSTMENT_OUT
            ),
            quantity=original.quantity,
            previous_stock=previous_stock,
            resulting_stock=resulting_stock,
            user=user,
            source=(
                StockMovement
                .SourceType
                .SYSTEM
            ),
            reference=(
                f"REVERSAL-IMPORT-{batch.pk}"
            ),
            notes=(
                f"Anulación de importación #{batch.pk}. "
                f"Motivo: {reason}"
            ),
            is_historical=False,
            import_batch=batch,
            reversal_of=original,
        )

        reversal_movements.append(
            reversal
        )

    batch.status = (
        InventoryImportBatch
        .Status
        .REVERSED
    )

    batch.reversed_at = (
        timezone.now()
    )

    batch.reversed_by = (
        user
    )

    batch.reversal_reason = (
        reason
    )

    batch.save(
        update_fields=[
            "status",
            "reversed_at",
            "reversed_by",
            "reversal_reason",
        ]
    )

    return (
        batch,
        reversal_movements,
    )
