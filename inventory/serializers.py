from decimal import Decimal

from rest_framework import serializers

from .models import (
    InventorySection,
    Category,
    UnitOfMeasure,
    UnitAlias,
    Warehouse,
    Product,
    Stock,
    StockMovement,
    InventoryImportBatch,
)


# ============================================================
# SECCIONES
# ============================================================

class InventorySectionSerializer(serializers.ModelSerializer):

    class Meta:
        model = InventorySection
        fields = [
            "id",
            "name",
            "code",
            "description",
            "order",
            "active",
        ]

        read_only_fields = [
            "code",
        ]


# ============================================================
# CATEGORÍAS
# ============================================================

class CategorySerializer(serializers.ModelSerializer):

    section_name = serializers.CharField(
        source="section.name",
        read_only=True,
    )

    class Meta:
        model = Category
        fields = [
            "id",
            "section",
            "section_name",
            "name",
            "order",
            "active",
        ]


# ============================================================
# UNIDADES
# ============================================================

class UnitAliasSerializer(serializers.ModelSerializer):

    class Meta:
        model = UnitAlias
        fields = [
            "id",
            "alias",
        ]


class UnitOfMeasureSerializer(serializers.ModelSerializer):

    aliases = UnitAliasSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = UnitOfMeasure
        fields = [
            "id",
            "name",
            "abbreviation",
            "active",
            "aliases",
        ]


# ============================================================
# ALMACENES
# ============================================================

class WarehouseSerializer(serializers.ModelSerializer):

    class Meta:
        model = Warehouse
        fields = [
            "id",
            "name",
            "location",
            "description",
            "active",
        ]


# ============================================================
# STOCK
# ============================================================

class StockSerializer(serializers.ModelSerializer):

    warehouse_name = serializers.CharField(
        source="warehouse.name",
        read_only=True,
    )

    product_code = serializers.CharField(
        source="product.code",
        read_only=True,
    )

    product_description = serializers.CharField(
        source="product.description",
        read_only=True,
    )

    unit = serializers.CharField(
        source="product.unit.abbreviation",
        read_only=True,
    )

    low_stock = serializers.SerializerMethodField()

    def get_low_stock(self, obj):
        return obj.is_low_stock

    class Meta:
        model = Stock
        fields = [
            "id",

            "product",
            "product_code",
            "product_description",

            "warehouse",
            "warehouse_name",

            "quantity",
            "unit",

            "low_stock",

            "updated_at",
        ]

        read_only_fields = fields


# ============================================================
# PRODUCTOS
# ============================================================

class ProductSerializer(serializers.ModelSerializer):

    section_name = serializers.CharField(
        source="section.name",
        read_only=True,
    )

    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
        allow_null=True,
    )

    unit_name = serializers.CharField(
        source="unit.name",
        read_only=True,
    )

    unit_abbreviation = serializers.CharField(
        source="unit.abbreviation",
        read_only=True,
    )

    image_url = serializers.SerializerMethodField()

    quantity_entry = serializers.DecimalField(
        source="total_entries",
        max_digits=14,
        decimal_places=3,
        read_only=True,
    )

    quantity_delivered = serializers.DecimalField(
        source="total_delivered",
        max_digits=14,
        decimal_places=3,
        read_only=True,
    )

    available = serializers.DecimalField(
        source="total_stock",
        max_digits=14,
        decimal_places=3,
        read_only=True,
    )

    stock_status = serializers.SerializerMethodField()

    stocks = StockSerializer(
        many=True,
        read_only=True,
    )

    def get_image_url(self, obj):
        if not obj.image:
            return None

        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(
                obj.image.url
            )

        return obj.image.url

    def get_stock_status(self, obj):
        available = obj.total_stock

        if available <= 0:
            return "OUT"

        if available <= obj.minimum_stock:
            return "LOW"

        return "OK"

    def validate(self, attrs):

        section = attrs.get(
            "section",
            getattr(self.instance, "section", None)
        )

        category = attrs.get(
            "category",
            getattr(self.instance, "category", None)
        )

        if (
            section
            and category
            and category.section_id != section.id
        ):
            raise serializers.ValidationError({
                "category": (
                    "La categoría seleccionada no pertenece "
                    "a la sección indicada."
                )
            })

        return attrs

    class Meta:
        model = Product

        fields = [
            "id",
            "code",

            "description",

            "section",
            "section_name",

            "category",
            "category_name",

            "unit",
            "unit_name",
            "unit_abbreviation",

            "minimum_stock",

            "image",
            "image_url",

            "notes",
            "active",

            "quantity_entry",
            "quantity_delivered",
            "available",

            "stock_status",

            "stocks",

            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "code",

            "quantity_entry",
            "quantity_delivered",
            "available",

            "stock_status",

            "created_at",
            "updated_at",
        ]


# ============================================================
# MOVIMIENTOS / HISTORIAL
# ============================================================

class StockMovementSerializer(serializers.ModelSerializer):

    movement_type_display = serializers.CharField(
        source="get_movement_type_display",
        read_only=True,
    )

    source_display = serializers.CharField(
        source="get_source_display",
        read_only=True,
    )

    product_code = serializers.CharField(
        source="product.code",
        read_only=True,
    )

    product_description = serializers.CharField(
        source="product.description",
        read_only=True,
    )

    section_name = serializers.CharField(
        source="product.section.name",
        read_only=True,
    )

    category_name = serializers.CharField(
        source="product.category.name",
        read_only=True,
        allow_null=True,
    )

    warehouse_name = serializers.CharField(
        source="warehouse.name",
        read_only=True,
    )

    username = serializers.CharField(
        source="created_by.username",
        read_only=True,
        allow_null=True,
    )

    unit = serializers.CharField(
        source="product.unit.abbreviation",
        read_only=True,
    )

    import_file_name = serializers.CharField(
        source="import_batch.file_name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = StockMovement

        fields = [
            "id",

            "movement_type",
            "movement_type_display",

            "product",
            "product_code",
            "product_description",

            "section_name",
            "category_name",

            "warehouse",
            "warehouse_name",

            "quantity",
            "unit",

            "previous_stock",
            "resulting_stock",

            # Snapshot de auditoría
            "product_code_snapshot",
            "product_description_snapshot",
            "unit_snapshot",

            "source",
            "source_display",

            "reference",
            "notes",

            "created_by",
            "username",

            "import_batch",
            "import_file_name",

            "reversal_of",

            "is_historical",

            "created_at",
        ]

        read_only_fields = fields


# ============================================================
# LOTES DE IMPORTACIÓN / HISTORIAL EXCEL
# ============================================================

class InventoryImportBatchSerializer(serializers.ModelSerializer):

    section_name = serializers.CharField(
        source="section.name",
        read_only=True,
    )

    warehouse_name = serializers.CharField(
        source="warehouse.name",
        read_only=True,
    )

    imported_by_username = serializers.SerializerMethodField()

    reversed_by_username = serializers.SerializerMethodField()

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    source_file_url = serializers.SerializerMethodField()

    def get_imported_by_username(self, obj):
        if not obj.imported_by:
            return None

        return obj.imported_by.username

    def get_reversed_by_username(self, obj):
        if not obj.reversed_by:
            return None

        return obj.reversed_by.username

    def get_source_file_url(self, obj):
        if not obj.source_file:
            return None

        request = self.context.get("request")

        if request:
            return request.build_absolute_uri(
                obj.source_file.url
            )

        return obj.source_file.url

    class Meta:
        model = InventoryImportBatch

        fields = [
            "id",

            "file_name",
            "source_file_url",

            "status",
            "status_display",

            "section",
            "section_name",

            "warehouse",
            "warehouse_name",

            "total_rows",
            "created_products",
            "matched_products",
            "movements_created",
            "skipped_rows",

            "error_message",

            "imported_by",
            "imported_by_username",

            "reversed_at",
            "reversed_by",
            "reversed_by_username",
            "reversal_reason",

            "created_at",
            "completed_at",
        ]

        read_only_fields = fields


# ============================================================
# ANULACIÓN DE IMPORTACIÓN
# ============================================================

class InventoryImportReverseSerializer(
    serializers.Serializer
):

    reason = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=1000,
        trim_whitespace=True,
    )


# ============================================================
# OPERACIONES
# ============================================================

class InventoryOperationSerializer(serializers.Serializer):

    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(
            active=True
        )
    )

    warehouse = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.filter(
            active=True
        )
    )

    quantity = serializers.DecimalField(
        max_digits=14,
        decimal_places=3,
        min_value=Decimal("0.001"),
    )

    reference = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=150,
    )

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
    )


# ============================================================
# CREACIÓN MANUAL / ENTRADA A PRODUCTO EXISTENTE
# ============================================================

class ManualProductCreateSerializer(
    serializers.Serializer
):

    product_id = serializers.PrimaryKeyRelatedField(
        source="product",
        queryset=Product.objects.filter(
            active=True
        ),
        required=False,
        allow_null=True,
    )

    description = serializers.CharField(
        required=True,
        allow_blank=False,
    )

    section = serializers.PrimaryKeyRelatedField(
        queryset=InventorySection.objects.filter(
            active=True
        )
    )

    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(
            active=True
        )
    )

    unit = serializers.PrimaryKeyRelatedField(
        queryset=UnitOfMeasure.objects.filter(
            active=True
        )
    )

    warehouse = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.filter(
            active=True
        )
    )

    quantity_entry = serializers.DecimalField(
        max_digits=14,
        decimal_places=3,
        min_value=Decimal("0"),
    )

    code = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    def validate(
        self,
        attrs,
    ):

        existing_product = attrs.get(
            "product"
        )

        # ====================================================
        # PRODUCTO EXISTENTE
        # ====================================================

        if existing_product:

            if (
                attrs["quantity_entry"]
                <=
                Decimal("0")
            ):

                raise serializers.ValidationError({
                    "quantity_entry": (
                        "Para agregar existencia a un producto "
                        "existente debes indicar una cantidad mayor a cero."
                    )
                })

            attrs["description"] = (
                existing_product.description
            )

            attrs["section"] = (
                existing_product.section
            )

            attrs["category"] = (
                existing_product.category
            )

            attrs["unit"] = (
                existing_product.unit
            )

            attrs["code"] = (
                existing_product.code
                or
                ""
            )

            return attrs

        # ====================================================
        # PRODUCTO NUEVO
        # ====================================================

        section = attrs[
            "section"
        ]

        category = attrs[
            "category"
        ]

        if (
            category.section_id
            !=
            section.id
        ):

            raise serializers.ValidationError({
                "category": (
                    "La categoría no pertenece "
                    "a la sección seleccionada."
                )
            })

        description = (
            " ".join(
                attrs[
                    "description"
                ]
                .strip()
                .upper()
                .split()
            )
        )

        attrs[
            "description"
        ] = description

        code = (
            attrs.get(
                "code",
                ""
            )
            .strip()
            .upper()
        )

        if (
            code
            and
            Product.objects
            .filter(
                code__iexact=code
            )
            .exists()
        ):

            raise serializers.ValidationError({
                "code": (
                    "Este código pertenece a un producto existente. "
                    "Busca el producto y selecciónalo para registrar "
                    "una nueva entrada."
                )
            })

        attrs[
            "code"
        ] = code

        return attrs
