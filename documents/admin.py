from django.contrib import admin

from .models import (
    DeliveryNote,
    DeliveryNoteItem,
)


class DeliveryNoteItemInline(
    admin.TabularInline
):
    model = DeliveryNoteItem

    extra = 0

    can_delete = False

    readonly_fields = [
        "product",
        "quantity",
        "movement",
        "product_code_snapshot",
        "product_description_snapshot",
        "unit_snapshot",
    ]

    fields = readonly_fields

    def has_add_permission(
        self,
        request,
        obj=None,
    ):
        return False


@admin.register(
    DeliveryNote
)
class DeliveryNoteAdmin(
    admin.ModelAdmin
):
    list_display = [
        "number",
        "delivery_date",
        "delivered_by_name",
        "recipient_name",
        "warehouse",
        "created_by",
        "created_at",
    ]

    list_filter = [
        "delivery_date",
        "warehouse",
        "created_at",
    ]

    search_fields = [
        "number",
        "delivered_by_name",
        "delivered_by_document",
        "recipient_name",
        "recipient_document",
    ]

    readonly_fields = [
        "number",
        "warehouse",
        "delivered_by_name",
        "delivered_by_document",
        "recipient_name",
        "recipient_document",
        "observations",
        "delivery_date",
        "created_by",
        "created_at",
    ]

    inlines = [
        DeliveryNoteItemInline,
    ]

    def has_add_permission(
        self,
        request,
    ):
        # Las notas deben crearse desde el flujo oficial,
        # porque ese flujo descuenta inventario.
        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False


@admin.register(
    DeliveryNoteItem
)
class DeliveryNoteItemAdmin(
    admin.ModelAdmin
):
    list_display = [
        "delivery_note",
        "product_description_snapshot",
        "quantity",
        "movement",
    ]

    search_fields = [
        "delivery_note__number",
        "product_code_snapshot",
        "product_description_snapshot",
    ]

    readonly_fields = [
        "delivery_note",
        "product",
        "quantity",
        "movement",
        "product_code_snapshot",
        "product_description_snapshot",
        "unit_snapshot",
    ]

    def has_add_permission(
        self,
        request,
    ):
        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False
