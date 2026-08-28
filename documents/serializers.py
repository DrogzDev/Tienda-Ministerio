from rest_framework import serializers

from inventory.models import (
    Product,
    Warehouse,
)

from .models import (
    DeliveryNote,
    DeliveryNoteItem,
)

from .services import (
    DeliveryNoteError,
    create_delivery_note,
)


class DeliveryNoteItemSerializer(
    serializers.ModelSerializer
):
    product_code = serializers.CharField(
        source="product_code_snapshot",
        read_only=True,
    )

    product_description = serializers.CharField(
        source="product_description_snapshot",
        read_only=True,
    )

    unit = serializers.CharField(
        source="unit_snapshot",
        read_only=True,
    )

    movement_id = serializers.IntegerField(
        source="movement.id",
        read_only=True,
    )

    class Meta:
        model = DeliveryNoteItem

        fields = [
            "id",
            "product",
            "product_code",
            "product_description",
            "quantity",
            "unit",
            "movement_id",
        ]

        read_only_fields = fields


class DeliveryNoteSerializer(
    serializers.ModelSerializer
):
    warehouse_name = serializers.CharField(
        source="warehouse.name",
        read_only=True,
    )

    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )

    items = DeliveryNoteItemSerializer(
        many=True,
        read_only=True,
    )

    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryNote

        fields = [
            "id",
            "number",
            "warehouse",
            "warehouse_name",
            "delivered_by_name",
            "delivered_by_document",
            "recipient_name",
            "recipient_document",
            "observations",
            "delivery_date",
            "created_by",
            "created_by_username",
            "created_at",
            "items",
            "pdf_url",
        ]

        read_only_fields = fields

    def get_pdf_url(
        self,
        obj,
    ):
        request = self.context.get(
            "request"
        )

        path = (
            f"/api/documents/"
            f"delivery-notes/"
            f"{obj.pk}/pdf/"
        )

        if request:
            return request.build_absolute_uri(
                path
            )

        return path


class DeliveryNoteCreateItemSerializer(
    serializers.Serializer
):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(
            active=True
        )
    )

    quantity = serializers.DecimalField(
        max_digits=14,
        decimal_places=3,
        min_value=0.001,
    )


class DeliveryNoteCreateSerializer(
    serializers.Serializer
):
    warehouse = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.filter(
            active=True
        )
    )

    delivered_by_name = serializers.CharField(
        max_length=200
    )

    delivered_by_document = serializers.CharField(
        max_length=40
    )

    recipient_name = serializers.CharField(
        max_length=200
    )

    recipient_document = serializers.CharField(
        max_length=40
    )

    observations = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    delivery_date = serializers.DateField(
        required=False
    )

    items = DeliveryNoteCreateItemSerializer(
        many=True,
        allow_empty=False,
    )

    def validate_items(
        self,
        items,
    ):
        product_ids = [
            item["product"].pk
            for item in items
        ]

        if (
            len(product_ids)
            !=
            len(set(product_ids))
        ):
            raise serializers.ValidationError(
                "No puedes repetir un producto "
                "dentro de la misma nota."
            )

        return items

    def create(
        self,
        validated_data,
    ):
        request = self.context[
            "request"
        ]

        try:
            note, _ = create_delivery_note(
                warehouse=
                    validated_data[
                        "warehouse"
                    ],

                delivered_by_name=
                    validated_data[
                        "delivered_by_name"
                    ],

                delivered_by_document=
                    validated_data[
                        "delivered_by_document"
                    ],

                recipient_name=
                    validated_data[
                        "recipient_name"
                    ],

                recipient_document=
                    validated_data[
                        "recipient_document"
                    ],

                observations=
                    validated_data.get(
                        "observations",
                        "",
                    ),

                delivery_date=
                    validated_data.get(
                        "delivery_date"
                    ),

                items=
                    validated_data[
                        "items"
                    ],

                user=
                    request.user,
            )

        except DeliveryNoteError as exc:
            raise serializers.ValidationError({
                "detail":
                    str(exc),
            }) from exc

        return note

    def to_representation(
        self,
        instance,
    ):
        return DeliveryNoteSerializer(
            instance,
            context=self.context,
        ).data
