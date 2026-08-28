from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from inventory.models import (
    Category,
    InventoryImportBatch,
    Product,
    StockMovement,
    UnitOfMeasure,
)
from inventory.services import register_entry
from inventory.utils import normalize_text, parse_decimal


VALID_ACTIONS = {"use_existing", "create_new", "skip"}


def _decision_for(decisions, row_number):
    if not decisions:
        return {}
    return decisions.get(row_number) or decisions.get(str(row_number)) or {}


def _get_or_create_category(*, section, row, decision):
    category_id = decision.get("category_id") or row.get("category_id")
    if category_id:
        category = Category.objects.get(pk=category_id, active=True)
        if category.section_id != section.id:
            raise ValidationError(
                f"Fila {row['row_number']}: la categoría no pertenece a la sección seleccionada."
            )
        return category

    if not decision.get("create_category"):
        raise ValidationError(
            f"Fila {row['row_number']}: debe resolver la categoría '{row.get('category_raw')}'."
        )

    raw_name = (row.get("category_raw") or "").strip()
    if not raw_name:
        raise ValidationError(f"Fila {row['row_number']}: categoría vacía.")

    normalized = normalize_text(raw_name)
    category = Category.objects.filter(
        section=section,
        normalized_name=normalized,
    ).first()
    if category:
        return category

    return Category.objects.create(section=section, name=raw_name)


def _get_or_create_unit(*, row, decision):
    unit_id = decision.get("unit_id") or row.get("unit_id")
    if unit_id:
        return UnitOfMeasure.objects.get(pk=unit_id, active=True)

    if not decision.get("create_unit"):
        raise ValidationError(
            f"Fila {row['row_number']}: debe resolver la unidad '{row.get('unit_raw')}'."
        )

    raw_unit = normalize_text(row.get("unit_raw"))
    if not raw_unit:
        raise ValidationError(f"Fila {row['row_number']}: unidad vacía.")

    unit = UnitOfMeasure.objects.filter(
        normalized_abbreviation=raw_unit,
        active=True,
    ).first()
    if unit:
        return unit

    # Para una unidad realmente nueva (ej. ROLLO), el texto se usa como nombre y abreviatura.
    return UnitOfMeasure.objects.create(
        name=raw_unit,
        abbreviation=raw_unit,
    )


def import_inventory_analysis(*, analysis, section, warehouse, user=None,
                              decisions=None, source_file=None,
                              original_filename=""):
    """
    Confirma una previsualización generada por analyzer.py.

    decisions por fila, ejemplo:
    {
        8: {"action": "use_existing", "product_id": 21},
        12: {"action": "create_new", "create_category": True},
        15: {"action": "create_new", "create_unit": True},
        20: {"action": "skip"},
    }
    """
    if not section.active:
        raise ValidationError("La sección seleccionada está inactiva.")
    if not warehouse.active:
        raise ValidationError("El almacén físico seleccionado está inactivo.")

    rows = analysis.get("rows") or []

    batch = InventoryImportBatch.objects.create(
        section=section,
        warehouse=warehouse,
        source_file=source_file,
        file_name=original_filename or getattr(source_file, "name", "") or "",
        total_rows=len(rows),
        imported_by=user,
        status=InventoryImportBatch.Status.PROCESSING,
    )

    created_products = 0
    matched_products = 0
    movements_created = 0
    skipped_rows = 0
    results = []

    try:
        with transaction.atomic():
            for row in rows:
                row_number = row["row_number"]
                decision = _decision_for(decisions, row_number)

                action = decision.get("action")
                if not action:
                    if row["status"] == "READY_EXISTING":
                        action = "use_existing"
                    elif row["status"] == "READY_NEW":
                        action = "create_new"
                    elif row["status"] in {"REVIEW", "ERROR"}:
                        raise ValidationError(
                            f"Fila {row_number}: requiere revisión antes de importar."
                        )

                if action not in VALID_ACTIONS:
                    raise ValidationError(f"Fila {row_number}: acción inválida '{action}'.")

                if action == "skip":
                    skipped_rows += 1
                    results.append({"row_number": row_number, "action": "skipped"})
                    continue

                if row.get("errors") and not decision.get("force"):
                    raise ValidationError(
                        f"Fila {row_number}: {' '.join(row['errors'])}"
                    )

                category = _get_or_create_category(
                    section=section,
                    row=row,
                    decision=decision,
                )
                unit = _get_or_create_unit(row=row, decision=decision)

                if action == "use_existing":
                    product_id = decision.get("product_id") or row.get("matched_product_id")
                    if not product_id:
                        raise ValidationError(
                            f"Fila {row_number}: no se indicó qué producto existente utilizar."
                        )

                    product = Product.objects.select_related("unit", "section").get(pk=product_id)
                    if product.section_id != section.id:
                        raise ValidationError(
                            f"Fila {row_number}: el producto seleccionado pertenece a otra sección."
                        )

                    # La importación nunca cambia la ficha maestra silenciosamente.
                    if product.unit_id != unit.id and not decision.get("force"):
                        raise ValidationError(
                            f"Fila {row_number}: la unidad del Excel no coincide con "
                            f"{product.code} ({product.unit.abbreviation})."
                        )

                    matched_products += 1
                else:
                    minimum_stock = (
                        parse_decimal(
                            row["minimum_stock"],
                            field_name="STOCK_MINIMO",
                            allow_zero=True,
                        )
                        if row.get("minimum_stock") not in (None, "")
                        else Decimal("0")
                    )

                    product = Product.objects.create(
                        description=row["description"],
                        section=section,
                        category=category,
                        unit=unit,
                        minimum_stock=minimum_stock,
                        notes=row.get("notes") or "",
                    )
                    created_products += 1

                quantity = parse_decimal(
                    row["quantity"],
                    field_name="CANTIDAD",
                    allow_zero=True,
                )

                movement_id = None
                if quantity > 0:
                    movement = register_entry(
                        product=product,
                        warehouse=warehouse,
                        quantity=quantity,
                        user=user,
                        source=StockMovement.SourceType.EXCEL,
                        reference=f"IMPORT-{batch.pk}",
                        notes=row.get("notes") or "",
                        import_batch=batch,
                    )
                    movement_id = movement.id
                    movements_created += 1

                results.append({
                    "row_number": row_number,
                    "action": action,
                    "product_id": product.id,
                    "product_code": product.code,
                    "movement_id": movement_id,
                    "quantity": format(quantity, "f"),
                })

            batch.created_products = created_products
            batch.matched_products = matched_products
            batch.movements_created = movements_created
            batch.skipped_rows = skipped_rows
            batch.status = InventoryImportBatch.Status.COMPLETED
            batch.completed_at = timezone.now()
            batch.save(update_fields=[
                "created_products",
                "matched_products",
                "movements_created",
                "skipped_rows",
                "status",
                "completed_at",
            ])

    except Exception as exc:
        batch.status = InventoryImportBatch.Status.FAILED
        batch.error_message = str(exc)
        batch.completed_at = timezone.now()
        batch.save(update_fields=["status", "error_message", "completed_at"])
        raise

    return {
        "batch_id": batch.id,
        "status": batch.status,
        "total_rows": batch.total_rows,
        "created_products": created_products,
        "matched_products": matched_products,
        "movements_created": movements_created,
        "skipped_rows": skipped_rows,
        "rows": results,
    }
