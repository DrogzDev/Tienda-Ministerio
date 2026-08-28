from django.db.models import Q

from rest_framework import (
    status,
    viewsets,
)
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import (
    JSONParser,
    MultiPartParser,
    FormParser,
)
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend

from accounts.permissions import (
    ROLE_ADMINISTRADOR,
    IsInventoryUser,
    IsAdministrador,
    IsAdministradorOrDirector,
    user_has_role,
)

from .models import (
    InventorySection,
    Category,
    UnitOfMeasure,
    Warehouse,
    Product,
    Stock,
    StockMovement,
    InventoryImportBatch,
)
from .serializers import (
    InventorySectionSerializer,
    CategorySerializer,
    UnitOfMeasureSerializer,
    WarehouseSerializer,
    ProductSerializer,
    StockSerializer,
    StockMovementSerializer,
    InventoryImportBatchSerializer,
    InventoryImportReverseSerializer,
    InventoryOperationSerializer,
    ManualProductCreateSerializer,
)
from .services import (
    register_entry,
    register_exit,
    register_adjustment_in,
    register_adjustment_out,
    create_manual_product,
    reverse_import_batch,
    InventoryError,
    InsufficientStockError,
    ImportReversalError,
)
from .filters import ProductFilter


# ============================================================
# HELPERS
# ============================================================

def _query_bool(value):
    """Convierte valores comunes de query/body a bool."""

    if isinstance(value, bool):
        return value

    if value is None:
        return None

    normalized = str(value).strip().lower()

    if normalized in {"true", "1", "yes", "on"}:
        return True

    if normalized in {"false", "0", "no", "off"}:
        return False

    return None


# ============================================================
# SECCIONES
# ============================================================

class InventorySectionViewSet(viewsets.ModelViewSet):

    serializer_class = InventorySectionSerializer

    queryset = (
        InventorySection.objects
        .all()
        .order_by("order", "name")
    )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsInventoryUser()]

        return [IsAdministrador()]

    def get_queryset(self):
        queryset = super().get_queryset()

        active = _query_bool(
            self.request.query_params.get("active")
        )

        if active is not None:
            queryset = queryset.filter(active=active)

        return queryset


# ============================================================
# CATEGORÍAS
# ============================================================

class CategoryViewSet(viewsets.ModelViewSet):

    serializer_class = CategorySerializer

    queryset = (
        Category.objects
        .select_related("section")
        .all()
    )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsInventoryUser()]

        if self.action == "create":
            return [IsInventoryUser()]

        if self.action in ["update", "partial_update"]:
            return [IsAdministradorOrDirector()]

        return [IsAdministrador()]

    def get_queryset(self):
        queryset = super().get_queryset()

        section = self.request.query_params.get("section")

        active = _query_bool(
            self.request.query_params.get("active")
        )

        search = self.request.query_params.get("search")

        if section:
            queryset = queryset.filter(
                section_id=section
            )

        if active is not None:
            queryset = queryset.filter(
                active=active
            )

        if search:
            queryset = queryset.filter(
                name__icontains=search
            )

        return queryset.order_by(
            "section__order",
            "order",
            "name",
        )


# ============================================================
# UNIDADES
# ============================================================

class UnitOfMeasureViewSet(viewsets.ModelViewSet):

    serializer_class = UnitOfMeasureSerializer

    queryset = (
        UnitOfMeasure.objects
        .prefetch_related("aliases")
        .all()
    )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsInventoryUser()]

        if self.action == "create":
            return [IsInventoryUser()]

        if self.action in ["update", "partial_update"]:
            return [IsAdministradorOrDirector()]

        return [IsAdministrador()]

    def get_queryset(self):
        queryset = super().get_queryset()

        active = _query_bool(
            self.request.query_params.get("active")
        )

        if active is not None:
            queryset = queryset.filter(
                active=active
            )

        return queryset.order_by(
            "name"
        )


# ============================================================
# ALMACENES
# ============================================================

class WarehouseViewSet(viewsets.ModelViewSet):

    serializer_class = WarehouseSerializer

    queryset = (
        Warehouse.objects
        .all()
    )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsInventoryUser()]

        return [IsAdministrador()]

    def get_queryset(self):
        queryset = super().get_queryset()

        active = _query_bool(
            self.request.query_params.get("active")
        )

        if active is not None:
            queryset = queryset.filter(
                active=active
            )

        return queryset.order_by(
            "name"
        )


# ============================================================
# PRODUCTOS
# ============================================================

class ProductViewSet(viewsets.ModelViewSet):

    serializer_class = ProductSerializer

    parser_classes = [
        JSONParser,
        MultiPartParser,
        FormParser,
    ]

    filter_backends = [
        DjangoFilterBackend
    ]

    filterset_class = ProductFilter

    queryset = (
        Product.objects
        .select_related(
            "section",
            "category",
            "unit",
        )
        .prefetch_related(
            "stocks"
        )
    )

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .order_by(
                "section__order",
                "description",
            )
        )

    # ========================================================
    # PERMISOS
    # ========================================================

    def get_permissions(self):

        if self.action in [
            "list",
            "retrieve",
        ]:
            return [
                IsInventoryUser()
            ]

        if self.action == "manual_create":
            return [
                IsInventoryUser()
            ]

        if self.action == "photo":
            return [
                IsInventoryUser()
            ]

        if self.action in [
            "update",
            "partial_update",
        ]:
            return [
                IsAdministradorOrDirector()
            ]

        return [
            IsAdministrador()
        ]

    # ========================================================
    # ACTIVE SOLO ADMIN
    # ========================================================

    def _validate_active_change(
        self,
        request,
        instance,
    ):

        if "active" not in request.data:
            return

        if user_has_role(
            request.user,
            ROLE_ADMINISTRADOR,
        ):
            return

        requested_active = _query_bool(
            request.data.get("active")
        )

        if requested_active is None:
            return

        if requested_active != instance.active:

            raise PermissionDenied(
                "Solo un administrador puede activar o desactivar productos."
            )

    def update(
        self,
        request,
        *args,
        **kwargs,
    ):

        instance = self.get_object()

        self._validate_active_change(
            request,
            instance,
        )

        return super().update(
            request,
            *args,
            **kwargs,
        )

    def partial_update(
        self,
        request,
        *args,
        **kwargs,
    ):

        instance = self.get_object()

        self._validate_active_change(
            request,
            instance,
        )

        return super().partial_update(
            request,
            *args,
            **kwargs,
        )

    # ========================================================
    # FOTO
    # ========================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="photo",
        parser_classes=[
            MultiPartParser,
            FormParser,
        ],
    )
    def photo(
        self,
        request,
        pk=None,
    ):

        product = self.get_object()

        uploaded_image = (
            request.FILES.get("image")
            or request.FILES.get("photo")
        )

        if not uploaded_image:

            return Response(
                {
                    "detail": (
                        "Debes enviar una imagen "
                        "en el campo 'image'."
                    )
                },
                status=
                    status.HTTP_400_BAD_REQUEST,
            )

        serializer = ProductSerializer(
            product,
            data={
                "image":
                    uploaded_image,
            },
            partial=True,
            context={
                "request":
                    request,
            },
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save()

        return Response(
            serializer.data,
            status=
                status.HTTP_200_OK,
        )

    # ========================================================
    # ENTRADA
    # ========================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="entry",
    )
    def entry(
        self,
        request,
        pk=None,
    ):

        product = self.get_object()

        serializer = InventoryOperationSerializer(
            data={
                **request.data,
                "product":
                    product.pk,
            }
        )

        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data

        try:

            movement = register_entry(
                product=
                    product,

                warehouse=
                    data["warehouse"],

                quantity=
                    data["quantity"],

                user=
                    request.user,

                reference=
                    data.get(
                        "reference",
                        ""
                    ),

                notes=
                    data.get(
                        "notes",
                        ""
                    ),
            )

        except InventoryError as exc:

            return Response(
                {
                    "detail":
                        str(exc)
                },
                status=
                    status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            StockMovementSerializer(
                movement
            ).data,
            status=
                status.HTTP_201_CREATED,
        )

    # ========================================================
    # SALIDA
    # ========================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="exit",
    )
    def exit(
        self,
        request,
        pk=None,
    ):

        product = self.get_object()

        serializer = InventoryOperationSerializer(
            data={
                **request.data,
                "product":
                    product.pk,
            }
        )

        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data

        try:

            movement = register_exit(
                product=
                    product,

                warehouse=
                    data["warehouse"],

                quantity=
                    data["quantity"],

                user=
                    request.user,

                reference=
                    data.get(
                        "reference",
                        ""
                    ),

                notes=
                    data.get(
                        "notes",
                        ""
                    ),
            )

        except InsufficientStockError as exc:

            return Response(
                {
                    "detail":
                        str(exc)
                },
                status=
                    status.HTTP_409_CONFLICT,
            )

        except InventoryError as exc:

            return Response(
                {
                    "detail":
                        str(exc)
                },
                status=
                    status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            StockMovementSerializer(
                movement
            ).data,
            status=
                status.HTTP_201_CREATED,
        )

    # ========================================================
    # AJUSTE +
    # ========================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="adjustment-in",
    )
    def adjustment_in(
        self,
        request,
        pk=None,
    ):

        product = self.get_object()

        serializer = InventoryOperationSerializer(
            data={
                **request.data,
                "product":
                    product.pk,
            }
        )

        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data

        try:

            movement = register_adjustment_in(
                product=
                    product,

                warehouse=
                    data["warehouse"],

                quantity=
                    data["quantity"],

                user=
                    request.user,

                reference=
                    data.get(
                        "reference",
                        ""
                    ),

                notes=
                    data.get(
                        "notes",
                        ""
                    ),
            )

        except InventoryError as exc:

            return Response(
                {
                    "detail":
                        str(exc)
                },
                status=
                    status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            StockMovementSerializer(
                movement
            ).data,
            status=
                status.HTTP_201_CREATED,
        )

    # ========================================================
    # AJUSTE -
    # ========================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="adjustment-out",
    )
    def adjustment_out(
        self,
        request,
        pk=None,
    ):

        product = self.get_object()

        serializer = InventoryOperationSerializer(
            data={
                **request.data,
                "product":
                    product.pk,
            }
        )

        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data

        try:

            movement = register_adjustment_out(
                product=
                    product,

                warehouse=
                    data["warehouse"],

                quantity=
                    data["quantity"],

                user=
                    request.user,

                reference=
                    data.get(
                        "reference",
                        ""
                    ),

                notes=
                    data.get(
                        "notes",
                        ""
                    ),
            )

        except InsufficientStockError as exc:

            return Response(
                {
                    "detail":
                        str(exc)
                },
                status=
                    status.HTTP_409_CONFLICT,
            )

        except InventoryError as exc:

            return Response(
                {
                    "detail":
                        str(exc)
                },
                status=
                    status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            StockMovementSerializer(
                movement
            ).data,
            status=
                status.HTTP_201_CREATED,
        )

    # ========================================================
    # CREACIÓN MANUAL / ENTRADA PRODUCTO EXISTENTE
    # ========================================================

    @action(
        detail=False,
        methods=["post"],
        url_path="manual-create",
    )
    def manual_create(
        self,
        request,
    ):

        serializer = ManualProductCreateSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        data = serializer.validated_data

        existing_product = (
            data.get(
                "product"
            )
        )

        try:

            product, movement, created = (
                create_manual_product(

                    product=
                        existing_product,

                    description=
                        data["description"],

                    section=
                        data["section"],

                    category=
                        data["category"],

                    unit=
                        data["unit"],

                    warehouse=
                        data["warehouse"],

                    quantity_entry=
                        data["quantity_entry"],

                    code=
                        data.get(
                            "code",
                            ""
                        ),

                    user=
                        request.user,
                )
            )

        except InventoryError as exc:

            return Response(
                {
                    "detail":
                        str(exc)
                },
                status=
                    status.HTTP_400_BAD_REQUEST,
            )

        except Exception:

            return Response(
                {
                    "detail": (
                        "No se pudo registrar "
                        "la entrada del producto."
                    )
                },
                status=
                    status.HTTP_400_BAD_REQUEST,
            )

        if created:

            detail = (
                "Producto creado correctamente."
            )

            operation = (
                "CREATED"
            )

        else:

            detail = (
                "Entrada agregada correctamente "
                "al producto existente."
            )

            operation = (
                "ENTRY"
            )

        return Response(
            {
                "detail":
                    detail,

                "operation":
                    operation,

                "created":
                    created,

                "product":
                    ProductSerializer(
                        product,
                        context={
                            "request":
                                request,
                        },
                    ).data,

                "movement": (
                    StockMovementSerializer(
                        movement
                    ).data
                    if movement
                    else None
                ),
            },
            status=
                status.HTTP_201_CREATED,
        )


# ============================================================
# STOCK
# ============================================================

class StockViewSet(
    viewsets.ReadOnlyModelViewSet
):

    serializer_class = (
        StockSerializer
    )

    permission_classes = [
        IsInventoryUser
    ]

    queryset = (
        Stock.objects
        .select_related(
            "product",
            "product__unit",
            "product__category",
            "product__section",
            "warehouse",
        )
        .all()
    )

    def get_queryset(self):

        queryset = (
            super().get_queryset()
        )

        warehouse = (
            self.request
            .query_params
            .get("warehouse")
        )

        section = (
            self.request
            .query_params
            .get("section")
        )

        category = (
            self.request
            .query_params
            .get("category")
        )

        search = (
            self.request
            .query_params
            .get("search")
        )

        if warehouse:
            queryset = queryset.filter(
                warehouse_id=
                    warehouse
            )

        if section:
            queryset = queryset.filter(
                product__section_id=
                    section
            )

        if category:
            queryset = queryset.filter(
                product__category_id=
                    category
            )

        if search:
            queryset = queryset.filter(
                Q(
                    product__description__icontains=
                        search
                )
                |
                Q(
                    product__code__icontains=
                        search
                )
            )

        return queryset.order_by(
            "product__description"
        )


# ============================================================
# MOVIMIENTOS / HISTORIAL
# ============================================================

class StockMovementViewSet(
    viewsets.ReadOnlyModelViewSet
):

    serializer_class = (
        StockMovementSerializer
    )

    permission_classes = [
        IsAdministradorOrDirector,
    ]

    queryset = (
        StockMovement.objects
        .select_related(
            "product",
            "product__unit",
            "product__category",
            "product__section",
            "warehouse",
            "created_by",
            "import_batch",
        )
        .all()
    )

    def get_queryset(self):

        queryset = (
            super().get_queryset()
        )

        product = (
            self.request
            .query_params
            .get("product")
        )

        warehouse = (
            self.request
            .query_params
            .get("warehouse")
        )

        movement_type = (
            self.request
            .query_params
            .get("type")
        )

        section = (
            self.request
            .query_params
            .get("section")
        )

        category = (
            self.request
            .query_params
            .get("category")
        )

        source = (
            self.request
            .query_params
            .get("source")
        )

        import_batch = (
            self.request
            .query_params
            .get("import_batch")
        )

        search = (
            self.request
            .query_params
            .get("search")
        )

        if product:
            queryset = queryset.filter(
                product_id=
                    product
            )

        if warehouse:
            queryset = queryset.filter(
                warehouse_id=
                    warehouse
            )

        if movement_type:
            queryset = queryset.filter(
                movement_type=
                    movement_type
            )

        if section:
            queryset = queryset.filter(
                product__section_id=
                    section
            )

        if category:
            queryset = queryset.filter(
                product__category_id=
                    category
            )

        if source:
            queryset = queryset.filter(
                source__iexact=
                    source
            )

        if import_batch:
            queryset = queryset.filter(
                import_batch_id=
                    import_batch
            )

        if search:
            queryset = queryset.filter(
                Q(
                    product__description__icontains=
                        search
                )
                |
                Q(
                    product__code__icontains=
                        search
                )
                |
                Q(
                    product_description_snapshot__icontains=
                        search
                )
                |
                Q(
                    product_code_snapshot__icontains=
                        search
                )
                |
                Q(
                    reference__icontains=
                        search
                )
                |
                Q(
                    import_batch__file_name__icontains=
                        search
                )
            )

        return queryset.order_by(
            "-created_at",
            "-id",
        )


# ============================================================
# LOTES DE IMPORTACIÓN EXCEL
# ============================================================

class InventoryImportBatchViewSet(
    viewsets.ReadOnlyModelViewSet
):

    serializer_class = (
        InventoryImportBatchSerializer
    )

    permission_classes = [
        IsAdministradorOrDirector,
    ]

    queryset = (
        InventoryImportBatch.objects
        .select_related(
            "section",
            "warehouse",
            "imported_by",
            "reversed_by",
        )
        .all()
    )

    def get_permissions(self):
        # Consultar historial de importaciones:
        # ADMIN + DIRECTOR.
        #
        # Anular una importación:
        # SOLO ADMIN.
        if self.action == "reverse":
            return [
                IsAdministrador()
            ]

        return [
            IsAdministradorOrDirector()
        ]

    def get_queryset(self):

        queryset = (
            super().get_queryset()
        )

        status_value = (
            self.request
            .query_params
            .get("status")
        )

        section = (
            self.request
            .query_params
            .get("section")
        )

        warehouse = (
            self.request
            .query_params
            .get("warehouse")
        )

        imported_by = (
            self.request
            .query_params
            .get("imported_by")
        )

        search = (
            self.request
            .query_params
            .get("search")
        )

        if status_value:
            queryset = queryset.filter(
                status=
                    status_value
            )

        if section:
            queryset = queryset.filter(
                section_id=
                    section
            )

        if warehouse:
            queryset = queryset.filter(
                warehouse_id=
                    warehouse
            )

        if imported_by:
            queryset = queryset.filter(
                imported_by_id=
                    imported_by
            )

        if search:
            queryset = queryset.filter(
                Q(
                    file_name__icontains=
                        search
                )
                |
                Q(
                    section__name__icontains=
                        search
                )
                |
                Q(
                    warehouse__name__icontains=
                        search
                )
                |
                Q(
                    imported_by__username__icontains=
                        search
                )
            )

        return queryset.order_by(
            "-created_at",
            "-id",
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="movements",
    )
    def movements(
        self,
        request,
        pk=None,
    ):

        batch = self.get_object()

        base_movements = (
            StockMovement.objects
            .filter(
                import_batch=batch
            )
            .select_related(
                "product",
                "product__unit",
                "product__category",
                "product__section",
                "warehouse",
                "created_by",
                "import_batch",
                "reversal_of",
            )
        )

        # Los movimientos originales son los que formaron parte
        # de la carga Excel. Los de reversión se entregan aparte
        # para no romper la vista actual del Import Review.
        movements = (
            base_movements
            .filter(
                reversal_of__isnull=True
            )
            .order_by(
                "created_at",
                "id",
            )
        )

        reversal_movements = (
            base_movements
            .filter(
                reversal_of__isnull=False
            )
            .order_by(
                "created_at",
                "id",
            )
        )

        search = (
            request.query_params
            .get("search")
        )

        if search:

            search_filter = (
                Q(
                    product__description__icontains=
                        search
                )
                |
                Q(
                    product__code__icontains=
                        search
                )
                |
                Q(
                    product_description_snapshot__icontains=
                        search
                )
                |
                Q(
                    product_code_snapshot__icontains=
                        search
                )
            )

            movements = (
                movements
                .filter(
                    search_filter
                )
            )

            reversal_movements = (
                reversal_movements
                .filter(
                    search_filter
                )
            )

        return Response(
            {
                "batch":
                    InventoryImportBatchSerializer(
                        batch,
                        context={
                            "request":
                                request,
                        },
                    ).data,

                "movements":
                    StockMovementSerializer(
                        movements,
                        many=True,
                        context={
                            "request":
                                request,
                        },
                    ).data,

                "reversal_movements":
                    StockMovementSerializer(
                        reversal_movements,
                        many=True,
                        context={
                            "request":
                                request,
                        },
                    ).data,
            },
            status=
                status.HTTP_200_OK,
        )

    # ========================================================
    # ANULAR IMPORTACIÓN
    # SOLO ADMINISTRADOR
    # ========================================================

    @action(
        detail=True,
        methods=["post"],
        url_path="reverse",
    )
    def reverse(
        self,
        request,
        pk=None,
    ):

        batch = self.get_object()

        serializer = (
            InventoryImportReverseSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        reason = (
            serializer
            .validated_data[
                "reason"
            ]
        )

        try:

            (
                reversed_batch,
                reversal_movements,
            ) = reverse_import_batch(
                batch=batch,
                user=request.user,
                reason=reason,
            )

        except InsufficientStockError as exc:

            return Response(
                {
                    "detail":
                        str(exc)
                },
                status=
                    status.HTTP_409_CONFLICT,
            )

        except ImportReversalError as exc:

            return Response(
                {
                    "detail":
                        str(exc)
                },
                status=
                    status.HTTP_400_BAD_REQUEST,
            )

        except InventoryError as exc:

            return Response(
                {
                    "detail":
                        str(exc)
                },
                status=
                    status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "detail": (
                    "Importación anulada correctamente."
                ),

                "batch":
                    InventoryImportBatchSerializer(
                        reversed_batch,
                        context={
                            "request":
                                request,
                        },
                    ).data,

                "reversal_count":
                    len(
                        reversal_movements
                    ),

                "reversal_movements":
                    StockMovementSerializer(
                        reversal_movements,
                        many=True,
                        context={
                            "request":
                                request,
                        },
                    ).data,
            },
            status=
                status.HTTP_200_OK,
        )

