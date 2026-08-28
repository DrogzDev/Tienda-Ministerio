from django.urls import path

from rest_framework.routers import (
    DefaultRouter,
)

from .views import (
    InventorySectionViewSet,
    CategoryViewSet,
    UnitOfMeasureViewSet,
    WarehouseViewSet,
    ProductViewSet,
    StockViewSet,
    StockMovementViewSet,
    InventoryImportBatchViewSet,
)

from .views_import import (
    ImportCatalogsAPIView,
    InventoryImportAnalyzeAPIView,
    InventoryImportCompleteCatalogsAPIView,
    InventoryImportConfirmAPIView,
    InventoryImportProductLookupAPIView,
)


router = DefaultRouter()


# ============================================================
# CRUD GENERAL
# ============================================================

router.register(
    "sections",
    InventorySectionViewSet,
    basename="inventory-section",
)

router.register(
    "categories",
    CategoryViewSet,
    basename="category",
)

router.register(
    "units",
    UnitOfMeasureViewSet,
    basename="unit",
)

router.register(
    "warehouses",
    WarehouseViewSet,
    basename="warehouse",
)

router.register(
    "products",
    ProductViewSet,
    basename="product",
)

router.register(
    "stock",
    StockViewSet,
    basename="stock",
)

router.register(
    "movements",
    StockMovementViewSet,
    basename="movement",
)


# ============================================================
# HISTORIAL DE IMPORTACIONES EXCEL
# ============================================================

router.register(
    "import-batches",
    InventoryImportBatchViewSet,
    basename="import-batch",
)

# El @action "reverse" del InventoryImportBatchViewSet genera
# automáticamente:
#
# POST /api/inventory/import-batches/{id}/reverse/
#
# No hace falta declarar un path manual adicional.


# ============================================================
# IMPORTACIONES
# ============================================================

urlpatterns = [

    path(
        "imports/catalogs/",
        ImportCatalogsAPIView.as_view(),
        name="inventory-import-catalogs",
    ),

    path(
        "imports/analyze/",
        InventoryImportAnalyzeAPIView.as_view(),
        name="inventory-import-analyze",
    ),

    path(
        "imports/product-lookup/",
        InventoryImportProductLookupAPIView.as_view(),
        name="inventory-import-product-lookup",
    ),

    path(
        "imports/complete-catalogs/",
        InventoryImportCompleteCatalogsAPIView.as_view(),
        name="inventory-import-complete-catalogs",
    ),

    path(
        "imports/confirm/",
        InventoryImportConfirmAPIView.as_view(),
        name="inventory-import-confirm",
    ),

]


urlpatterns += router.urls