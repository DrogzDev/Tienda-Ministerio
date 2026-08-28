from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from inventory.models import (
    Product,
    StockMovement,
    Warehouse,
)

from inventory.services import (
    InventoryError,
    register_exit,
)

from .models import (
    DeliveryNote,
    DeliveryNoteItem,
)


class DeliveryNoteError(Exception):
    pass


def _clean_required_text(
    value,
    *,
    field_name,
):
    value = str(
        value
        or
        ""
    ).strip()

    if not value:
        raise DeliveryNoteError(
            f"{field_name} es obligatorio."
        )

    return value


@transaction.atomic
def create_delivery_note(
    *,
    warehouse,
    delivered_by_name,
    delivered_by_document,
    recipient_name,
    recipient_document,
    items,
    user,
    observations="",
    delivery_date=None,
):
    """
    Crea la nota y descuenta inventario.

    Regla principal:
    si falla un solo producto, Django revierte TODA la transacción.
    """

    if not user:
        raise DeliveryNoteError(
            "La nota requiere un usuario responsable."
        )

    if (
        not warehouse
        or
        not isinstance(
            warehouse,
            Warehouse,
        )
    ):
        raise DeliveryNoteError(
            "El almacén de origen no es válido."
        )

    if not warehouse.active:
        raise DeliveryNoteError(
            "El almacén seleccionado está inactivo."
        )

    delivered_by_name = _clean_required_text(
        delivered_by_name,
        field_name="El nombre de quien entrega",
    )

    delivered_by_document = _clean_required_text(
        delivered_by_document,
        field_name="La cédula de quien entrega",
    )

    recipient_name = _clean_required_text(
        recipient_name,
        field_name="El nombre de quien recibe",
    )

    recipient_document = _clean_required_text(
        recipient_document,
        field_name="La cédula de quien recibe",
    )

    if not items:
        raise DeliveryNoteError(
            "La nota debe contener al menos un producto."
        )

    normalized_items = []
    product_ids = set()

    for item in items:
        product = item.get(
            "product"
        )

        quantity = item.get(
            "quantity"
        )

        if (
            not product
            or
            not isinstance(
                product,
                Product,
            )
        ):
            raise DeliveryNoteError(
                "Uno de los productos no es válido."
            )

        if not product.active:
            raise DeliveryNoteError(
                f"El producto '{product.description}' está inactivo."
            )

        if product.pk in product_ids:
            raise DeliveryNoteError(
                f"El producto '{product.description}' "
                "está repetido en la nota."
            )

        product_ids.add(
            product.pk
        )

        try:
            quantity = Decimal(
                str(
                    quantity
                ).replace(
                    ",",
                    ".",
                )
            )
        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ) as exc:
            raise DeliveryNoteError(
                f"La cantidad de '{product.description}' no es válida."
            ) from exc

        if quantity <= Decimal("0"):
            raise DeliveryNoteError(
                f"La cantidad de '{product.description}' "
                "debe ser mayor que cero."
            )

        normalized_items.append({
            "product":
                product,

            "quantity":
                quantity,
        })

    note = DeliveryNote.objects.create(
        warehouse=
            warehouse,

        delivered_by_name=
            delivered_by_name,

        delivered_by_document=
            delivered_by_document,

        recipient_name=
            recipient_name,

        recipient_document=
            recipient_document,

        observations=
            str(
                observations
                or
                ""
            ).strip(),

        delivery_date=(
            delivery_date
            or
            timezone.localdate()
        ),

        created_by=
            user,
    )

    created_items = []

    try:
        for item in normalized_items:
            product = item[
                "product"
            ]

            quantity = item[
                "quantity"
            ]

            movement = register_exit(
                product=
                    product,

                warehouse=
                    warehouse,

                quantity=
                    quantity,

                user=
                    user,

                source=(
                    StockMovement
                    .SourceType
                    .MANUAL
                ),

                reference=
                    note.number,

                notes=(
                    f"Salida correspondiente a la "
                    f"nota de entrega {note.number}. "
                    f"Recibe: {note.recipient_name} "
                    f"({note.recipient_document})."
                ),
            )

            note_item = DeliveryNoteItem.objects.create(
                delivery_note=
                    note,

                product=
                    product,

                quantity=
                    quantity,

                movement=
                    movement,

                product_code_snapshot=(
                    product.code
                    or
                    ""
                ),

                product_description_snapshot=
                    product.description,

                unit_snapshot=
                    product.unit.abbreviation,
            )

            created_items.append(
                note_item
            )

    except InventoryError as exc:
        # Al propagarse dentro de @transaction.atomic,
        # se revierte la nota y todos los EXIT previos.
        raise DeliveryNoteError(
            str(exc)
        ) from exc

    return (
        note,
        created_items,
    )