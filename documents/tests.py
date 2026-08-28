from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from inventory.models import (
    InventorySection,
    Product,
    Stock,
    StockMovement,
    UnitOfMeasure,
    Warehouse,
)

from .documents import (
    build_delivery_note_pdf,
)

from .models import (
    DeliveryNote,
)

from .services import (
    DeliveryNoteError,
    create_delivery_note,
)


User = get_user_model()


class DeliveryNoteServiceTests(
    TestCase
):
    def setUp(self):
        self.user = User.objects.create_user(
            username="test_admin",
            password="test123",
        )

        self.section = InventorySection.objects.create(
            name="ALMACEN",
        )

        self.unit = UnitOfMeasure.objects.create(
            name="UNIDAD",
            abbreviation="UND",
        )

        self.warehouse = Warehouse.objects.create(
            name="ALMACEN GENERAL",
            active=True,
        )

        self.product = Product.objects.create(
            description="ALMOHADILLA PARA SELLO",
            section=self.section,
            unit=self.unit,
            minimum_stock=0,
            active=True,
        )

        Stock.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            quantity=Decimal("10"),
        )

    def test_create_note_decrements_stock(self):
        note, items = create_delivery_note(
            warehouse=self.warehouse,
            delivered_by_name="MIGUEL MONGES",
            delivered_by_document="V-8.756.216",
            recipient_name="DAVID CARMONA",
            recipient_document="V-27.439.762",
            items=[
                {
                    "product":
                        self.product,

                    "quantity":
                        Decimal("4"),
                }
            ],
            user=self.user,
        )

        stock = Stock.objects.get(
            product=self.product,
            warehouse=self.warehouse,
        )

        self.assertEqual(
            stock.quantity,
            Decimal("6"),
        )

        self.assertTrue(
            note.number.startswith(
                "NE-"
            )
        )

        self.assertEqual(
            len(items),
            1,
        )

        self.assertEqual(
            items[0].movement.movement_type,
            StockMovement.MovementType.EXIT,
        )

    def test_insufficient_stock_rolls_back_note(self):
        with self.assertRaises(
            DeliveryNoteError
        ):
            create_delivery_note(
                warehouse=self.warehouse,
                delivered_by_name="MIGUEL MONGES",
                delivered_by_document="V-8.756.216",
                recipient_name="DAVID CARMONA",
                recipient_document="V-27.439.762",
                items=[
                    {
                        "product":
                            self.product,

                        "quantity":
                            Decimal("100"),
                    }
                ],
                user=self.user,
            )

        self.assertEqual(
            DeliveryNote.objects.count(),
            0,
        )

        stock = Stock.objects.get(
            product=self.product,
            warehouse=self.warehouse,
        )

        self.assertEqual(
            stock.quantity,
            Decimal("10"),
        )

    def test_pdf_is_generated(self):
        note, _ = create_delivery_note(
            warehouse=self.warehouse,
            delivered_by_name="MIGUEL MONGES",
            delivered_by_document="V-8.756.216",
            recipient_name="DAVID CARMONA",
            recipient_document="V-27.439.762",
            items=[
                {
                    "product":
                        self.product,

                    "quantity":
                        Decimal("2"),
                }
            ],
            user=self.user,
        )

        pdf = build_delivery_note_pdf(
            note
        )

        self.assertTrue(
            pdf.startswith(
                b"%PDF"
            )
        )
