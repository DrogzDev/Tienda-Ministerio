from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from inventory.models import (
    Product,
    StockMovement,
    Warehouse,
)


class DeliveryNote(models.Model):
    """
    Nota institucional de entrega.

    El documento vive en la app `documents`, pero las existencias
    siguen siendo responsabilidad de `inventory`.
    """

    number = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        editable=False,
        verbose_name="Número de nota",
    )

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="delivery_notes",
        verbose_name="Almacén de origen",
    )

    delivered_by_name = models.CharField(
        max_length=200,
        verbose_name="Entrega",
    )

    delivered_by_document = models.CharField(
        max_length=40,
        verbose_name="Cédula de quien entrega",
    )

    recipient_name = models.CharField(
        max_length=200,
        verbose_name="Recibe",
    )

    recipient_document = models.CharField(
        max_length=40,
        verbose_name="Cédula de quien recibe",
    )

    observations = models.TextField(
        blank=True,
        default="",
        verbose_name="Observaciones",
    )

    delivery_date = models.DateField(
        default=timezone.localdate,
        verbose_name="Fecha de entrega",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="delivery_notes_created",
        verbose_name="Creada por",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    class Meta:
        verbose_name = "Nota de entrega"
        verbose_name_plural = "Notas de entrega"
        ordering = [
            "-created_at",
            "-id",
        ]
        indexes = [
            models.Index(
                fields=["number"],
                name="documents_note_number_idx",
            ),
            models.Index(
                fields=["delivery_date"],
                name="documents_note_date_idx",
            ),
            models.Index(
                fields=["warehouse"],
                name="documents_note_warehouse_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        self.delivered_by_name = self._normalize_name(
            self.delivered_by_name
        )
        self.delivered_by_document = self._normalize_document(
            self.delivered_by_document
        )
        self.recipient_name = self._normalize_name(
            self.recipient_name
        )
        self.recipient_document = self._normalize_document(
            self.recipient_document
        )

        if self.number:
            return super().save(
                *args,
                **kwargs,
            )

        # Primer guardado para obtener PK.
        super().save(
            *args,
            **kwargs,
        )

        year = (
            self.delivery_date.year
            if self.delivery_date
            else timezone.localdate().year
        )

        self.number = (
            f"NE-{year}-{self.pk:06d}"
        )

        super().save(
            update_fields=[
                "number",
            ]
        )

    @staticmethod
    def _normalize_name(value):
        return " ".join(
            str(value or "")
            .strip()
            .upper()
            .split()
        )

    @staticmethod
    def _normalize_document(value):
        return (
            str(value or "")
            .strip()
            .upper()
        )

    def __str__(self):
        return (
            f"{self.number} - "
            f"{self.recipient_name}"
        )


class DeliveryNoteItem(models.Model):
    """
    Línea de una nota de entrega.

    `movement` apunta al StockMovement EXIT que realizó
    el descuento real del inventario.
    """

    delivery_note = models.ForeignKey(
        DeliveryNote,
        on_delete=models.PROTECT,
        related_name="items",
        verbose_name="Nota de entrega",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="delivery_note_items",
        verbose_name="Producto",
    )

    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        validators=[
            MinValueValidator(
                Decimal("0.001")
            )
        ],
        verbose_name="Cantidad",
    )

    movement = models.OneToOneField(
        StockMovement,
        on_delete=models.PROTECT,
        related_name="delivery_note_item",
        verbose_name="Movimiento de salida",
    )

    # Snapshots: el PDF histórico no cambia aunque luego
    # editen el producto.
    product_code_snapshot = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="Código histórico",
    )

    product_description_snapshot = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Descripción histórica",
    )

    unit_snapshot = models.CharField(
        max_length=40,
        blank=True,
        default="",
        verbose_name="Unidad histórica",
    )

    class Meta:
        verbose_name = "Ítem de nota de entrega"
        verbose_name_plural = "Ítems de notas de entrega"
        ordering = [
            "id",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "delivery_note",
                    "product",
                ],
                name="unique_product_per_delivery_note",
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "delivery_note",
                    "product",
                ],
                name="doc_note_item_prod_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.delivery_note.number} | "
            f"{self.product_description_snapshot or self.product.description} | "
            f"{self.quantity}"
        )