from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.utils.text import slugify

from .utils import normalize_text


# ============================================================
# SECCIONES
# ============================================================

class InventorySection(models.Model):
    """
    Secciones principales equivalentes a las pestañas del Excel.

    Ejemplos:
    - ALMACÉN
    - TRANSPORTE
    - FERRETERÍA
    - BOLSAS
    """

    name = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Nombre",
    )

    code = models.SlugField(
        max_length=160,
        unique=True,
        blank=True,
        verbose_name="Código interno",
    )

    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Descripción",
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Orden",
    )

    active = models.BooleanField(
        default=True,
        verbose_name="Activa",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última modificación",
    )

    class Meta:
        verbose_name = "Sección de inventario"
        verbose_name_plural = "Secciones de inventario"
        ordering = [
            "order",
            "name",
        ]

    def save(self, *args, **kwargs):
        if self.name:
            self.name = " ".join(
                self.name.strip().upper().split()
            )

        if not self.code:
            self.code = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ============================================================
# CATEGORÍAS
# ============================================================

class Category(models.Model):

    section = models.ForeignKey(
        InventorySection,
        on_delete=models.PROTECT,
        related_name="categories",
        verbose_name="Sección",
    )

    name = models.CharField(
        max_length=150,
        verbose_name="Nombre",
    )

    normalized_name = models.CharField(
        max_length=150,
        editable=False,
        db_index=True,
        verbose_name="Nombre normalizado",
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Orden",
    )

    active = models.BooleanField(
        default=True,
        verbose_name="Activa",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última modificación",
    )

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

        ordering = [
            "section__order",
            "section__name",
            "order",
            "name",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "section",
                    "normalized_name",
                ],
                name="unique_normalized_category_per_section",
            )
        ]

        indexes = [
            models.Index(
                fields=[
                    "section",
                    "normalized_name",
                ]
            ),
            models.Index(
                fields=["active"]
            ),
        ]

    def save(self, *args, **kwargs):
        if self.name:
            self.name = " ".join(
                self.name.strip().upper().split()
            )

            self.normalized_name = normalize_text(
                self.name
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.section.name} / "
            f"{self.name}"
        )


# ============================================================
# UNIDADES DE MEDIDA
# ============================================================

class UnitOfMeasure(models.Model):
    """
    Unidad utilizada por el producto.

    Ejemplos:
    UND
    KG
    LITROS
    CAJA
    PAQ
    PAQ X3
    PAR
    GALON
    etc.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nombre",
    )

    abbreviation = models.CharField(
        max_length=40,
        unique=True,
        verbose_name="Abreviatura",
    )

    normalized_name = models.CharField(
        max_length=100,
        editable=False,
        db_index=True,
    )

    normalized_abbreviation = models.CharField(
        max_length=40,
        editable=False,
        db_index=True,
    )

    active = models.BooleanField(
        default=True,
        verbose_name="Activa",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última modificación",
    )

    class Meta:
        verbose_name = "Unidad de medida"
        verbose_name_plural = "Unidades de medida"

        ordering = [
            "name",
        ]

    def save(self, *args, **kwargs):

        if self.name:
            self.name = " ".join(
                self.name.strip().upper().split()
            )

            self.normalized_name = normalize_text(
                self.name
            )

        if self.abbreviation:
            self.abbreviation = " ".join(
                self.abbreviation
                .strip()
                .upper()
                .split()
            )

            self.normalized_abbreviation = normalize_text(
                self.abbreviation
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.abbreviation


# ============================================================
# ALIAS DE UNIDADES
# ============================================================

class UnitAlias(models.Model):
    """
    Variantes encontradas en Excel.

    Ejemplo:

    UND
    UNID
    UNIDAD
    UNIDADES

    pueden apuntar todas a la unidad canónica UND.
    """

    unit = models.ForeignKey(
        UnitOfMeasure,
        on_delete=models.CASCADE,
        related_name="aliases",
        verbose_name="Unidad",
    )

    alias = models.CharField(
        max_length=60,
        unique=True,
        verbose_name="Alias",
    )

    class Meta:
        verbose_name = "Alias de unidad"
        verbose_name_plural = "Alias de unidades"

        ordering = [
            "alias",
        ]

    def save(self, *args, **kwargs):

        if self.alias:
            self.alias = normalize_text(
                self.alias
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.alias} → "
            f"{self.unit.abbreviation}"
        )


# ============================================================
# ALMACENES FÍSICOS
# ============================================================

class Warehouse(models.Model):
    """
    Ubicación física.

    Es diferente de la sección de inventario
    llamada ALMACÉN.
    """

    name = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Nombre",
    )

    location = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Ubicación",
    )

    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Descripción",
    )

    active = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última modificación",
    )

    class Meta:
        verbose_name = "Almacén físico"
        verbose_name_plural = "Almacenes físicos"

        ordering = [
            "name",
        ]

    def save(self, *args, **kwargs):

        if self.name:
            self.name = " ".join(
                self.name.strip().upper().split()
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ============================================================
# RUTAS DE ARCHIVOS
# ============================================================

def product_image_upload_to(instance, filename):
    now = timezone.now()

    return (
        f"products/"
        f"{now.year}/"
        f"{now.month:02d}/"
        f"{filename}"
    )


def inventory_import_upload_to(instance, filename):
    now = timezone.now()

    return (
        f"inventory_imports/"
        f"{now.year}/"
        f"{now.month:02d}/"
        f"{filename}"
    )


# ============================================================
# PRODUCTOS
# ============================================================

class Product(models.Model):

    code = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Código",
    )

    description = models.CharField(
        max_length=255,
        verbose_name="Descripción",
    )

    normalized_description = models.CharField(
        max_length=255,
        editable=False,
        db_index=True,
        verbose_name="Descripción normalizada",
    )

    section = models.ForeignKey(
        InventorySection,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="Sección",
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        null=True,
        blank=True,
        verbose_name="Categoría",
    )

    unit = models.ForeignKey(
        UnitOfMeasure,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="Unidad de medida",
    )

    minimum_stock = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=0,
        validators=[
            MinValueValidator(
                Decimal("0")
            )
        ],
        verbose_name="Stock mínimo",
    )

    image = models.ImageField(
        upload_to=product_image_upload_to,
        null=True,
        blank=True,
        verbose_name="Imagen",
    )

    notes = models.TextField(
        blank=True,
        default="",
        verbose_name="Observaciones",
    )

    active = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última modificación",
    )

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

        ordering = [
            "section__order",
            "section__name",
            "description",
        ]

        indexes = [
            models.Index(
                fields=["normalized_description"]
            ),

            models.Index(
                fields=[
                    "section",
                    "normalized_description",
                ]
            ),

            models.Index(
                fields=[
                    "section",
                    "unit",
                    "normalized_description",
                ]
            ),

            models.Index(
                fields=["category"]
            ),

            models.Index(
                fields=["active"]
            ),
        ]

    def clean(self):
        super().clean()

        if (
            self.category_id
            and self.section_id
        ):
            if (
                self.category.section_id
                != self.section_id
            ):
                raise ValidationError({
                    "category": (
                        "La categoría seleccionada "
                        "no pertenece a la sección "
                        "del producto."
                    )
                })

    def save(self, *args, **kwargs):

        if self.description:
            self.description = " ".join(
                self.description
                .strip()
                .upper()
                .split()
            )

            self.normalized_description = (
                normalize_text(
                    self.description
                )
            )

        if self.code:
            self.code = (
                self.code
                .strip()
                .upper()
            )

        self.full_clean()

        # Primer guardado para obtener PK.
        if not self.pk and not self.code:

            super().save(
                *args,
                **kwargs,
            )

            self.code = (
                f"INV-{self.pk:06d}"
            )

            super().save(
                update_fields=[
                    "code"
                ]
            )

            return

        super().save(
            *args,
            **kwargs,
        )

    # ========================================================
    # TOTALES DE INVENTARIO
    # ========================================================

    @property
    def total_entries(self):
        """
        Cantidad acumulada de entradas.

        Ejemplo:
        Entrada inicial: 63
        Entrada nueva:   20

        total_entries = 83
        """

        total = (
            self.movements
            .filter(
                movement_type="ENTRY",
                reversal__isnull=True,
            )
            .aggregate(
                total=Sum("quantity")
            )
            .get("total")
        )

        return (
            total
            if total is not None
            else Decimal("0")
        )

    @property
    def total_delivered(self):
        """
        Cantidad acumulada entregada/salida.

        Ejemplo:
        Primera entrega: 11
        Segunda entrega: 5

        total_delivered = 16
        """

        total = (
            self.movements
            .filter(
                movement_type="EXIT"
            )
            .aggregate(
                total=Sum("quantity")
            )
            .get("total")
        )

        return (
            total
            if total is not None
            else Decimal("0")
        )

    @property
    def total_stock(self):
        """
        Stock disponible actual sumando todos
        los almacenes físicos.

        Este es el valor de DISPONIBLE.
        """

        total = (
            self.stocks
            .aggregate(
                total=Sum("quantity")
            )
            .get("total")
        )

        return (
            total
            if total is not None
            else Decimal("0")
        )

    @property
    def stock_status(self):
        """
        Estado general del producto.
        """

        if self.total_stock <= self.minimum_stock:
            return "LOW"

        return "OK"

    def __str__(self):
        return (
            f"{self.code} - "
            f"{self.description}"
        )


# ============================================================
# STOCK
# ============================================================

class Stock(models.Model):

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="stocks",
        verbose_name="Producto",
    )

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="stocks",
        verbose_name="Almacén físico",
    )

    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=0,
        validators=[
            MinValueValidator(
                Decimal("0")
            )
        ],
        verbose_name="Cantidad disponible",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última actualización",
    )

    class Meta:
        verbose_name = "Existencia"
        verbose_name_plural = "Existencias"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "product",
                    "warehouse",
                ],
                name=(
                    "unique_product_"
                    "warehouse_stock"
                ),
            ),

            models.CheckConstraint(
                condition=models.Q(
                    quantity__gte=0
                ),
                name=(
                    "stock_quantity_gte_zero"
                ),
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "product",
                    "warehouse",
                ]
            )
        ]

    @property
    def is_low_stock(self):
        return (
            self.quantity
            <=
            self.product.minimum_stock
        )

    def __str__(self):
        return (
            f"{self.product.description} | "
            f"{self.warehouse.name} | "
            f"{self.quantity} "
            f"{self.product.unit.abbreviation}"
        )


# ============================================================
# LOTES DE IMPORTACIÓN
# ============================================================

class InventoryImportBatch(models.Model):

    class Status(models.TextChoices):
        PROCESSING = (
            "PROCESSING",
            "Procesando",
        )

        COMPLETED = (
            "COMPLETED",
            "Completada",
        )

        FAILED = (
            "FAILED",
            "Fallida",
        )

        REVERSED = (
            "REVERSED",
            "Anulada",
        )

    section = models.ForeignKey(
        InventorySection,
        on_delete=models.PROTECT,
        related_name="import_batches",
        verbose_name="Sección",
    )

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="import_batches",
        verbose_name="Almacén físico",
    )

    source_file = models.FileField(
        upload_to=inventory_import_upload_to,
        null=True,
        blank=True,
        verbose_name="Archivo original",
    )

    file_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Nombre del archivo",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROCESSING,
        verbose_name="Estado",
    )

    total_rows = models.PositiveIntegerField(
        default=0,
        verbose_name="Total de filas",
    )

    created_products = models.PositiveIntegerField(
        default=0,
        verbose_name="Productos creados",
    )

    matched_products = models.PositiveIntegerField(
        default=0,
        verbose_name="Productos relacionados",
    )

    movements_created = models.PositiveIntegerField(
        default=0,
        verbose_name="Movimientos creados",
    )

    skipped_rows = models.PositiveIntegerField(
        default=0,
        verbose_name="Filas omitidas",
    )

    error_message = models.TextField(
        blank=True,
        default="",
        verbose_name="Mensaje de error",
    )

    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inventory_import_batches",
        verbose_name="Importado por",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de finalización",
    )

    reversed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de anulación",
    )

    reversed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reversed_inventory_import_batches",
        verbose_name="Anulada por",
    )

    reversal_reason = models.TextField(
        blank=True,
        default="",
        verbose_name="Motivo de anulación",
    )

    class Meta:
        verbose_name = "Importación de inventario"
        verbose_name_plural = "Importaciones de inventario"

        ordering = [
            "-created_at",
        ]

    def __str__(self):

        return (
            f"Importación #{self.pk} - "
            f"{self.section.name} - "
            f"{self.status}"
        )


# ============================================================
# MOVIMIENTOS DE INVENTARIO
# ============================================================

class StockMovement(models.Model):

    class MovementType(models.TextChoices):

        ENTRY = (
            "ENTRY",
            "Entrada",
        )

        EXIT = (
            "EXIT",
            "Salida",
        )

        ADJUSTMENT_IN = (
            "ADJUSTMENT_IN",
            "Ajuste positivo",
        )

        ADJUSTMENT_OUT = (
            "ADJUSTMENT_OUT",
            "Ajuste negativo",
        )

    class SourceType(models.TextChoices):

        MANUAL = (
            "MANUAL",
            "Manual",
        )

        EXCEL = (
            "EXCEL",
            "Importación Excel",
        )

        SYSTEM = (
            "SYSTEM",
            "Sistema",
        )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="movements",
        verbose_name="Producto",
    )

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.PROTECT,
        related_name="movements",
        verbose_name="Almacén físico",
    )

    movement_type = models.CharField(
        max_length=30,
        choices=MovementType.choices,
        verbose_name="Tipo de movimiento",
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

    previous_stock = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=0,
        verbose_name="Existencia anterior",
    )

    resulting_stock = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=0,
        verbose_name="Existencia resultante",
    )

    # --------------------------------------------------------
    # Snapshot para auditoría
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Procedencia
    # --------------------------------------------------------

    source = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.MANUAL,
        verbose_name="Origen",
    )

    reference = models.CharField(
        max_length=150,
        blank=True,
        default="",
        verbose_name="Referencia",
    )

    notes = models.TextField(
        blank=True,
        default="",
        verbose_name="Observaciones",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inventory_movements",
        verbose_name="Realizado por",
    )

    import_batch = models.ForeignKey(
        InventoryImportBatch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movements",
        verbose_name="Lote de importación",
    )

    reversal_of = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reversal",
        verbose_name="Movimiento revertido",
    )

    is_historical = models.BooleanField(
        default=False,
        verbose_name="Movimiento histórico",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha",
    )

    class Meta:
        verbose_name = "Movimiento de inventario"
        verbose_name_plural = "Movimientos de inventario"

        ordering = [
            "-created_at",
        ]

        indexes = [
            models.Index(
                fields=["product"]
            ),

            models.Index(
                fields=["warehouse"]
            ),

            models.Index(
                fields=["movement_type"]
            ),

            models.Index(
                fields=["created_at"]
            ),

            models.Index(
                fields=["import_batch"]
            ),

            models.Index(
                fields=["reversal_of"]
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    quantity__gt=0
                ),
                name=(
                    "movement_quantity_gt_zero"
                ),
            )
        ]

    def __str__(self):

        description = (
            self.product_description_snapshot
            or self.product.description
        )

        unit = (
            self.unit_snapshot
            or self.product.unit.abbreviation
        )

        return (
            f"{self.get_movement_type_display()} | "
            f"{description} | "
            f"{self.quantity} "
            f"{unit}"
        )