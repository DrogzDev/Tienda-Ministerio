import json
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.storage import default_storage
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.text import get_valid_filename

from .importers.analyzer import analyze_inventory_excel
from .importers.importer import import_inventory_analysis
from .models import (
    Category,
    InventoryImportBatch,
    InventorySection,
    Product,
    Stock,
    StockMovement,
    UnitAlias,
    UnitOfMeasure,
    Warehouse,
)


# ============================================================
# FORMULARIO DE CARGA EXCEL PARA ADMIN
# ============================================================

class InventoryExcelUploadForm(forms.Form):
    section = forms.ModelChoiceField(
        queryset=InventorySection.objects.none(),
        label="Sección destino",
        help_text="Ej.: ALMACÉN, TRANSPORTE, FERRETERÍA o BOLSAS.",
    )
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.none(),
        label="Almacén físico",
    )
    excel_file = forms.FileField(
        label="Archivo Excel",
        help_text="Use un archivo .xlsx con la plantilla oficial de inventario.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["section"].queryset = InventorySection.objects.filter(
            active=True
        ).order_by("order", "name")
        self.fields["warehouse"].queryset = Warehouse.objects.filter(
            active=True
        ).order_by("name")

    def clean_excel_file(self):
        uploaded = self.cleaned_data["excel_file"]
        suffix = Path(uploaded.name).suffix.lower()
        if suffix != ".xlsx":
            raise forms.ValidationError(
                "El archivo debe ser Excel .xlsx."
            )
        return uploaded


# ============================================================
# HELPERS DEL PREVIEW
# ============================================================

def _safe_temp_name(uploaded_name):
    original = get_valid_filename(Path(uploaded_name).name)
    return f"inventory_import_previews/{uuid4().hex}_{original}"


def _enrich_analysis(analysis):
    """
    Agrega al preview el stock actual y el stock esperado
    sin modificar la base de datos.
    """
    product_ids = {
        row.get("matched_product_id")
        for row in analysis.get("rows", [])
        if row.get("matched_product_id")
    }
    products = Product.objects.filter(pk__in=product_ids).in_bulk()

    for row in analysis.get("rows", []):
        quantity = Decimal(row.get("quantity") or "0")
        product = products.get(row.get("matched_product_id"))

        if product:
            current = product.total_stock
            row["current_stock"] = format(current, "f")
            row["resulting_stock"] = format(current + quantity, "f")
            row["system_unit"] = product.unit.abbreviation
            row["system_description"] = product.description
        else:
            row["current_stock"] = "0"
            row["resulting_stock"] = format(quantity, "f")
            row["system_unit"] = row.get("unit_raw") or ""
            row["system_description"] = row.get("description") or ""

    return analysis


# ============================================================
# SECCIONES
# ============================================================

@admin.register(InventorySection)
class InventorySectionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "code",
        "order",
        "active",
    )
    list_editable = (
        "order",
        "active",
    )
    search_fields = (
        "name",
        "code",
    )
    ordering = (
        "order",
        "name",
    )
    readonly_fields = (
        "code",
        "created_at",
        "updated_at",
    )


# ============================================================
# CATEGORÍAS
# ============================================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "section",
        "order",
        "active",
    )
    list_filter = (
        "section",
        "active",
    )
    list_editable = (
        "order",
        "active",
    )
    search_fields = (
        "name",
        "section__name",
    )
    autocomplete_fields = (
        "section",
    )
    readonly_fields = (
        "normalized_name",
        "created_at",
        "updated_at",
    )


# ============================================================
# UNIDADES
# ============================================================

class UnitAliasInline(admin.TabularInline):
    model = UnitAlias
    extra = 1


@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "abbreviation",
        "active",
    )
    list_filter = (
        "active",
    )
    search_fields = (
        "name",
        "abbreviation",
        "aliases__alias",
    )
    readonly_fields = (
        "normalized_name",
        "normalized_abbreviation",
        "created_at",
        "updated_at",
    )
    inlines = [UnitAliasInline]


@admin.register(UnitAlias)
class UnitAliasAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "alias",
        "unit",
    )
    search_fields = (
        "alias",
        "unit__name",
        "unit__abbreviation",
    )
    autocomplete_fields = (
        "unit",
    )


# ============================================================
# ALMACENES FÍSICOS
# ============================================================

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "location",
        "active",
    )
    list_filter = (
        "active",
    )
    search_fields = (
        "name",
        "location",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )


# ============================================================
# STOCK INLINE - SOLO LECTURA
# ============================================================

class StockInline(admin.TabularInline):
    model = Stock
    extra = 0
    fields = (
        "warehouse",
        "quantity",
        "updated_at",
    )
    readonly_fields = (
        "warehouse",
        "quantity",
        "updated_at",
    )
    can_delete = False
    show_change_link = False

    def has_add_permission(self, request, obj=None):
        return False


# ============================================================
# PRODUCTOS
# ============================================================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "code",
        "description",
        "section",
        "category",
        "unit",
        "entrada",
        "entregada",
        "disponible",
        "minimum_stock",
        "stock_status",
        "active",
        "image_thumbnail",
    )
    list_filter = (
        "active",
        "section",
        "category",
        "unit",
    )
    search_fields = (
        "code",
        "description",
        "category__name",
        "section__name",
    )
    autocomplete_fields = (
        "section",
        "category",
        "unit",
    )
    readonly_fields = (
        "code",
        "normalized_description",
        "entrada",
        "entregada",
        "disponible",
        "image_preview",
        "api_json_link",
        "json_preview",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (
            "Producto",
            {
                "fields": (
                    "code",
                    "description",
                    "section",
                    "category",
                    "unit",
                    "minimum_stock",
                    "notes",
                    "active",
                )
            },
        ),
        (
            "Imagen",
            {
                "fields": (
                    "image",
                    "image_preview",
                )
            },
        ),
        (
            "Inventario",
            {
                "fields": (
                    "entrada",
                    "entregada",
                    "disponible",
                )
            },
        ),
        (
            "API",
            {
                "fields": (
                    "api_json_link",
                    "json_preview",
                )
            },
        ),
        (
            "Sistema",
            {
                "classes": ("collapse",),
                "fields": (
                    "normalized_description",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )
    inlines = [StockInline]
    ordering = ("description",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "section",
                "category",
                "unit",
            )
            .prefetch_related(
                "stocks",
                "movements",
            )
        )

    @admin.display(description="Entrada")
    def entrada(self, obj):
        if not obj.pk:
            return "0"
        return f"{obj.total_entries} {obj.unit.abbreviation}"

    @admin.display(description="Entregada")
    def entregada(self, obj):
        if not obj.pk:
            return "0"
        return f"{obj.total_delivered} {obj.unit.abbreviation}"

    @admin.display(description="Disponible")
    def disponible(self, obj):
        if not obj.pk:
            return "0"
        return f"{obj.total_stock} {obj.unit.abbreviation}"

    @admin.display(description="Estado")
    def stock_status(self, obj):
        if not obj.pk:
            return "-"
        if obj.total_stock <= obj.minimum_stock:
            return format_html(
                '<strong style="color:#dc3545;">STOCK BAJO</strong>'
            )
        return format_html(
            '<strong style="color:#198754;">DISPONIBLE</strong>'
        )

    @admin.display(description="Imagen")
    def image_thumbnail(self, obj):
        if not obj.image:
            return "-"
        return format_html(
            '<img src="{}" style="width:45px;height:45px;object-fit:cover;border-radius:6px;" />',
            obj.image.url,
        )

    @admin.display(description="Vista previa")
    def image_preview(self, obj):
        if not obj or not obj.image:
            return "Sin imagen"
        return format_html(
            '<img src="{}" style="max-width:300px;max-height:300px;object-fit:contain;border-radius:8px;" />',
            obj.image.url,
        )

    @admin.display(description="JSON API")
    def api_json_link(self, obj):
        if not obj or not obj.pk:
            return "Guarda primero el producto para ver su JSON."
        url = f"/api/inventory/products/{obj.pk}/?format=json"
        return format_html(
            '<a href="{}" target="_blank" style="font-weight:600;text-decoration:none;">Ver JSON real de la API ↗</a>',
            url,
        )

    @admin.display(description="Vista previa del JSON")
    def json_preview(self, obj):
        if not obj or not obj.pk:
            return "Guarda primero el producto para generar la vista previa."

        data = {
            "id": obj.id,
            "code": obj.code,
            "description": obj.description,
            "section": obj.section_id,
            "section_name": obj.section.name,
            "category": obj.category_id if obj.category else None,
            "category_name": obj.category.name if obj.category else None,
            "unit": obj.unit_id,
            "unit_name": obj.unit.name,
            "unit_abbreviation": obj.unit.abbreviation,
            "minimum_stock": str(obj.minimum_stock),
            "image_url": obj.image.url if obj.image else None,
            "notes": obj.notes,
            "active": obj.active,
            "quantity_entry": str(obj.total_entries),
            "quantity_delivered": str(obj.total_delivered),
            "available": str(obj.total_stock),
            "stock_status": "LOW" if obj.total_stock <= obj.minimum_stock else "OK",
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
            "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
        }

        pretty_json = json.dumps(data, ensure_ascii=False, indent=4)
        return format_html(
            '<pre style="background:#111827;color:#e5e7eb;padding:16px;border-radius:8px;max-width:950px;overflow:auto;font-size:12px;line-height:1.5;">{}</pre>',
            pretty_json,
        )


# ============================================================
# STOCK
# ============================================================

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "warehouse",
        "quantity",
        "stock_status",
        "updated_at",
    )
    list_filter = (
        "warehouse",
        "product__section",
        "product__category",
    )
    search_fields = (
        "product__code",
        "product__description",
        "warehouse__name",
    )
    autocomplete_fields = (
        "product",
        "warehouse",
    )
    readonly_fields = (
        "product",
        "warehouse",
        "quantity",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Estado")
    def stock_status(self, obj):
        if obj.quantity <= obj.product.minimum_stock:
            return format_html('<strong style="color:#dc3545;">BAJO</strong>')
        return format_html('<strong style="color:#198754;">OK</strong>')


# ============================================================
# MOVIMIENTOS
# ============================================================

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "movement_type",
        "product_code_snapshot",
        "product_description_snapshot",
        "warehouse",
        "quantity",
        "unit_snapshot",
        "previous_stock",
        "resulting_stock",
        "source",
        "created_by",
    )
    list_filter = (
        "movement_type",
        "source",
        "warehouse",
        "is_historical",
        "created_at",
    )
    search_fields = (
        "product_code_snapshot",
        "product_description_snapshot",
        "reference",
        "notes",
        "created_by__username",
    )
    readonly_fields = [field.name for field in StockMovement._meta.fields]
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ============================================================
# IMPORTACIONES EXCEL
# ============================================================

@admin.register(InventoryImportBatch)
class InventoryImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "section",
        "warehouse",
        "file_name",
        "status",
        "total_rows",
        "created_products",
        "matched_products",
        "movements_created",
        "skipped_rows",
        "imported_by",
    )
    list_filter = (
        "status",
        "section",
        "warehouse",
        "created_at",
    )
    search_fields = (
        "file_name",
        "imported_by__username",
    )
    readonly_fields = [field.name for field in InventoryImportBatch._meta.fields]
    ordering = ("-created_at",)

    # Hace que aparezca "+ Agregar" en el Admin.
    # Al pulsarlo, redirigimos al asistente de importación Excel.
    def has_add_permission(self, request):
        return super().has_add_permission(request)

    def add_view(self, request, form_url="", extra_context=None):
        return redirect(
            reverse(
                "admin:inventory_inventoryimportbatch_import_excel"
            )
        )

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-excel/",
                self.admin_site.admin_view(self.import_excel_view),
                name="inventory_inventoryimportbatch_import_excel",
            ),
            path(
                "import-excel/confirm/",
                self.admin_site.admin_view(self.confirm_import_view),
                name="inventory_inventoryimportbatch_confirm_import",
            ),
        ]
        return custom_urls + urls

    def import_excel_view(self, request):
        """
        Paso 1: seleccionar sección, almacén y Excel.
        Paso 2: analizar y mostrar preview SIN tocar inventario.
        """
        if request.method == "POST":
            form = InventoryExcelUploadForm(request.POST, request.FILES)

            if form.is_valid():
                section = form.cleaned_data["section"]
                warehouse = form.cleaned_data["warehouse"]
                uploaded = form.cleaned_data["excel_file"]
                original_filename = Path(uploaded.name).name
                temp_name = _safe_temp_name(original_filename)

                temp_name = default_storage.save(temp_name, uploaded)

                try:
                    with default_storage.open(temp_name, "rb") as excel_file:
                        analysis = analyze_inventory_excel(
                            file_or_path=excel_file,
                            section=section,
                        )

                    analysis = _enrich_analysis(analysis)

                except Exception as exc:
                    if default_storage.exists(temp_name):
                        default_storage.delete(temp_name)

                    messages.error(
                        request,
                        f"No se pudo analizar el Excel: {exc}",
                    )
                    return redirect(
                        reverse(
                            "admin:inventory_inventoryimportbatch_import_excel"
                        )
                    )

                context = {
                    **self.admin_site.each_context(request),
                    "opts": self.model._meta,
                    "title": "Revisar importación de inventario",
                    "analysis": analysis,
                    "section": section,
                    "warehouse": warehouse,
                    "temp_file_name": temp_name,
                    "original_filename": original_filename,
                    "confirm_url": reverse(
                        "admin:inventory_inventoryimportbatch_confirm_import"
                    ),
                    "upload_url": reverse(
                        "admin:inventory_inventoryimportbatch_import_excel"
                    ),
                }

                return TemplateResponse(
                    request,
                    "admin/inventory/import_excel_review.html",
                    context,
                )
        else:
            form = InventoryExcelUploadForm()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Importar inventario desde Excel",
            "form": form,
        }

        return TemplateResponse(
            request,
            "admin/inventory/import_excel_upload.html",
            context,
        )

    def confirm_import_view(self, request):
        """
        Reanaliza el mismo archivo por seguridad y, si no existen
        filas REVIEW/ERROR, confirma la importación usando importer.py.
        """
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])

        temp_name = (request.POST.get("temp_file_name") or "").strip()
        original_filename = (request.POST.get("original_filename") or "").strip()
        section_id = request.POST.get("section_id")
        warehouse_id = request.POST.get("warehouse_id")

        if not temp_name.startswith("inventory_import_previews/"):
            messages.error(request, "Archivo temporal inválido.")
            return redirect(
                reverse(
                    "admin:inventory_inventoryimportbatch_import_excel"
                )
            )

        if not default_storage.exists(temp_name):
            messages.error(
                request,
                "El archivo temporal ya no existe. Vuelva a cargar el Excel.",
            )
            return redirect(
                reverse(
                    "admin:inventory_inventoryimportbatch_import_excel"
                )
            )

        section = get_object_or_404(
            InventorySection,
            pk=section_id,
            active=True,
        )
        warehouse = get_object_or_404(
            Warehouse,
            pk=warehouse_id,
            active=True,
        )

        try:
            with default_storage.open(temp_name, "rb") as excel_file:
                analysis = analyze_inventory_excel(
                    file_or_path=excel_file,
                    section=section,
                )

            analysis = _enrich_analysis(analysis)

            if not analysis.get("can_import_without_review"):
                messages.error(
                    request,
                    "La importación todavía contiene filas que requieren revisión. "
                    "No se modificó el inventario.",
                )

                context = {
                    **self.admin_site.each_context(request),
                    "opts": self.model._meta,
                    "title": "Revisar importación de inventario",
                    "analysis": analysis,
                    "section": section,
                    "warehouse": warehouse,
                    "temp_file_name": temp_name,
                    "original_filename": original_filename,
                    "confirm_url": reverse(
                        "admin:inventory_inventoryimportbatch_confirm_import"
                    ),
                    "upload_url": reverse(
                        "admin:inventory_inventoryimportbatch_import_excel"
                    ),
                }

                return TemplateResponse(
                    request,
                    "admin/inventory/import_excel_review.html",
                    context,
                )

            # Abrimos otra vez el temporal para que InventoryImportBatch
            # conserve una copia del Excel original en media/inventory_imports/.
            with default_storage.open(temp_name, "rb") as raw_file:
                django_file = File(
                    raw_file,
                    name=original_filename or Path(temp_name).name,
                )

                result = import_inventory_analysis(
                    analysis=analysis,
                    section=section,
                    warehouse=warehouse,
                    user=request.user,
                    source_file=django_file,
                    original_filename=original_filename,
                )

            if default_storage.exists(temp_name):
                default_storage.delete(temp_name)

            messages.success(
                request,
                (
                    "Importación completada. "
                    f"Productos nuevos: {result['created_products']}. "
                    f"Productos existentes: {result['matched_products']}. "
                    f"Movimientos creados: {result['movements_created']}."
                ),
            )

            return redirect(
                reverse(
                    "admin:inventory_inventoryimportbatch_changelist"
                )
            )

        except (ValidationError, Exception) as exc:
            messages.error(
                request,
                f"No se pudo completar la importación: {exc}",
            )

            return redirect(
                reverse(
                    "admin:inventory_inventoryimportbatch_import_excel"
                )
            )