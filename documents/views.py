from django.db.models import Q
from django.http import HttpResponse

from rest_framework import (
    status,
    viewsets,
)

from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import (
    IsAdministrador,
)

from .documents import (
    build_delivery_note_pdf,
)

from .models import (
    DeliveryNote,
)

from .serializers import (
    DeliveryNoteCreateSerializer,
    DeliveryNoteSerializer,
)


class DeliveryNoteViewSet(
    viewsets.ModelViewSet
):
    """
    Notas de entrega.

    - Listar
    - Consultar
    - Crear
    - Descargar/ver PDF

    No se permite editar ni borrar porque una nota ya emitida
    está ligada a movimientos reales de inventario.
    """

    permission_classes = [
        IsAdministrador,
    ]

    http_method_names = [
        "get",
        "post",
        "head",
        "options",
    ]

    queryset = (
        DeliveryNote.objects
        .select_related(
            "warehouse",
            "created_by",
        )
        .prefetch_related(
            "items",
            "items__product",
            "items__movement",
        )
        .all()
    )

    def get_serializer_class(
        self,
    ):
        if self.action == "create":
            return DeliveryNoteCreateSerializer

        return DeliveryNoteSerializer

    def get_queryset(
        self,
    ):
        queryset = (
            super()
            .get_queryset()
        )

        search = (
            self.request
            .query_params
            .get(
                "search"
            )
        )

        warehouse = (
            self.request
            .query_params
            .get(
                "warehouse"
            )
        )

        date_from = (
            self.request
            .query_params
            .get(
                "date_from"
            )
        )

        date_to = (
            self.request
            .query_params
            .get(
                "date_to"
            )
        )

        if search:
            queryset = queryset.filter(
                Q(
                    number__icontains=
                        search
                )
                |
                Q(
                    delivered_by_name__icontains=
                        search
                )
                |
                Q(
                    delivered_by_document__icontains=
                        search
                )
                |
                Q(
                    recipient_name__icontains=
                        search
                )
                |
                Q(
                    recipient_document__icontains=
                        search
                )
                |
                Q(
                    items__product_description_snapshot__icontains=
                        search
                )
            ).distinct()

        if warehouse:
            queryset = queryset.filter(
                warehouse_id=
                    warehouse
            )

        if date_from:
            queryset = queryset.filter(
                delivery_date__gte=
                    date_from
            )

        if date_to:
            queryset = queryset.filter(
                delivery_date__lte=
                    date_to
            )

        return queryset

    def create(
        self,
        request,
        *args,
        **kwargs,
    ):
        serializer = (
            self.get_serializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        note = serializer.save()

        output = DeliveryNoteSerializer(
            note,
            context={
                "request":
                    request,
            },
        )

        return Response(
            output.data,
            status=
                status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="pdf",
    )
    def pdf(
        self,
        request,
        pk=None,
    ):
        note = self.get_object()

        pdf_bytes = (
            build_delivery_note_pdf(
                note
            )
        )

        response = HttpResponse(
            pdf_bytes,
            content_type=
                "application/pdf",
        )

        download = (
            request
            .query_params
            .get(
                "download"
            )
            ==
            "1"
        )

        disposition = (
            "attachment"
            if download
            else
            "inline"
        )

        response[
            "Content-Disposition"
        ] = (
            f'{disposition}; '
            f'filename="{note.number}.pdf"'
        )

        return response
