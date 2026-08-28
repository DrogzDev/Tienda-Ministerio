from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import (
    TA_CENTER,
    TA_LEFT,
)
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# ============================================================
# ASSETS
# ============================================================

ASSETS_DIR = (
    Path(__file__)
    .resolve()
    .parent
    /
    "assets"
)

LOGO_CANDIDATES = [
    ASSETS_DIR
    /
    "minhvi_logo.png",

    ASSETS_DIR
    /
    "minhvi_logo.jpg",

    ASSETS_DIR
    /
    "logo.png",

    ASSETS_DIR
    /
    "logo.jpg",
]

FOOTER_CANDIDATES = [
    ASSETS_DIR
    /
    "venezuela_footer.png",

    ASSETS_DIR
    /
    "footer_venezuela.png",
]


# ============================================================
# COLORES
# ============================================================

NAVY = colors.HexColor(
    "#0B2F7D"
)

NAVY_DARK = colors.HexColor(
    "#08245E"
)

TEXT = colors.HexColor(
    "#18284D"
)

MUTED = colors.HexColor(
    "#687897"
)

BORDER = colors.HexColor(
    "#D9E0EB"
)

SOFT = colors.HexColor(
    "#F6F8FC"
)

YELLOW = colors.HexColor(
    "#FBCB05"
)

BLUE = colors.HexColor(
    "#003DA5"
)

RED = colors.HexColor(
    "#CF142B"
)


# ============================================================
# FECHA EN ESPAÑOL
# ============================================================

DAY_WORDS = {
    1: "uno",
    2: "dos",
    3: "tres",
    4: "cuatro",
    5: "cinco",
    6: "seis",
    7: "siete",
    8: "ocho",
    9: "nueve",
    10: "diez",
    11: "once",
    12: "doce",
    13: "trece",
    14: "catorce",
    15: "quince",
    16: "dieciséis",
    17: "diecisiete",
    18: "dieciocho",
    19: "diecinueve",
    20: "veinte",
    21: "veintiuno",
    22: "veintidós",
    23: "veintitrés",
    24: "veinticuatro",
    25: "veinticinco",
    26: "veintiséis",
    27: "veintisiete",
    28: "veintiocho",
    29: "veintinueve",
    30: "treinta",
    31: "treinta y uno",
}

MONTH_WORDS = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}


# ============================================================
# HELPERS
# ============================================================

def _existing_asset(
    candidates,
):
    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def _safe(
    value,
):
    return escape(
        str(
            value
            or
            ""
        )
    )


def _display_quantity(
    value,
):
    text = format(
        value,
        "f",
    )

    if "." in text:
        text = (
            text
            .rstrip("0")
            .rstrip(".")
        )

    return (
        text
        or
        "0"
    )


def _document_number(
    value,
):
    """
    Deja la cédula legible tal como fue almacenada.
    """

    return (
        str(
            value
            or
            ""
        )
        .strip()
    )


def _date_sentence(
    date,
):
    day_word = DAY_WORDS.get(
        date.day,
        str(
            date.day
        ),
    )

    month_word = MONTH_WORDS.get(
        date.month,
        str(
            date.month
        ),
    )

    return (
        f"En Caracas, a los "
        f"{day_word} ({date.day}) días "
        f"del mes de {month_word} de {date.year}, "
        f"en la sede de la Oficina Principal del MINHVI, "
    )



# ============================================================
# DECORACIÓN DE PÁGINA
# ============================================================

def _draw_page(
    canvas,
    doc,
):
    width, height = letter

    canvas.saveState()

    # Línea tricolor superior muy discreta.
    stripe_y = (
        height
        -
        9
        *
        mm
    )

    stripe_width = (
        width
        /
        3
    )

    canvas.setFillColor(
        YELLOW
    )

    canvas.rect(
        0,
        stripe_y,
        stripe_width,
        1.8 * mm,
        fill=1,
        stroke=0,
    )

    canvas.setFillColor(
        BLUE
    )

    canvas.rect(
        stripe_width,
        stripe_y,
        stripe_width,
        1.8 * mm,
        fill=1,
        stroke=0,
    )

    canvas.setFillColor(
        RED
    )

    canvas.rect(
        stripe_width * 2,
        stripe_y,
        stripe_width,
        1.8 * mm,
        fill=1,
        stroke=0,
    )

    # Footer institucional.
    footer_asset = _existing_asset(
        FOOTER_CANDIDATES
    )

    if footer_asset:
        try:
            canvas.drawImage(
                str(
                    footer_asset
                ),
                0,
                0,
                width=
                    width,
                height=
                    20 * mm,
                preserveAspectRatio=
                    False,
                mask=
                    "auto",
            )
        except Exception:
            footer_asset = None

    if not footer_asset:
        # Fallback sin imagen.
        canvas.setFillColor(
            YELLOW
        )
        canvas.rect(
            0,
            0,
            width,
            4 * mm,
            fill=1,
            stroke=0,
        )

        canvas.setFillColor(
            BLUE
        )
        canvas.rect(
            0,
            0,
            width,
            2.6 * mm,
            fill=1,
            stroke=0,
        )

        canvas.setFillColor(
            RED
        )
        canvas.rect(
            0,
            0,
            width,
            1.2 * mm,
            fill=1,
            stroke=0,
        )

    canvas.setStrokeColor(
        BORDER
    )

    canvas.setLineWidth(
        0.5
    )

    canvas.line(
        18 * mm,
        18 * mm,
        width - 18 * mm,
        18 * mm,
    )

    canvas.setFillColor(
        MUTED
    )

    canvas.setFont(
        "Helvetica",
        6.7,
    )

    canvas.drawString(
        18 * mm,
        13.2 * mm,
        (
            "Avenida Francisco de Miranda, "
            "Torre del Ministerio del Poder Popular "
            "para Hábitat y Vivienda, Chacao, Miranda."
        ),
    )

    canvas.drawString(
        18 * mm,
        9.8 * mm,
        (
            "Sistema Institucional de Gestión de Inventario"
        ),
    )

    canvas.drawRightString(
        width - 18 * mm,
        9.8 * mm,
        f"Página {doc.page}",
    )

    canvas.restoreState()


# ============================================================
# PDF NOTA DE ENTREGA
# ============================================================

def build_delivery_note_pdf(
    note,
):
    """
    Convierte una DeliveryNote existente en PDF.

    Este archivo NO descuenta inventario.
    """

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,

        pagesize=
            letter,

        rightMargin=
            18 * mm,

        leftMargin=
            18 * mm,

        topMargin=
            18 * mm,

        bottomMargin=
            25 * mm,

        title=(
            f"Nota de entrega "
            f"{note.number}"
        ),

        author=(
            "Ministerio del Poder Popular "
            "para Hábitat y Vivienda"
        ),
    )

    base_styles = (
        getSampleStyleSheet()
    )

    title_style = ParagraphStyle(
        "Title",

        parent=
            base_styles["Heading1"],

        fontName=
            "Helvetica-Bold",

        fontSize=
            17,

        leading=
            20,

        alignment=
            TA_LEFT,

        textColor=
            NAVY_DARK,

        spaceAfter=
            2,
    )

    eyebrow_style = ParagraphStyle(
        "Eyebrow",

        parent=
            base_styles["Normal"],

        fontName=
            "Helvetica-Bold",

        fontSize=
            6.8,

        leading=
            8,

        alignment=
            TA_LEFT,

        textColor=
            MUTED,

        spaceAfter=
            2,
    )

    body_style = ParagraphStyle(
        "Body",

        parent=
            base_styles["Normal"],

        fontName=
            "Helvetica",

        fontSize=
            9.2,

        leading=
            15,

        alignment=
            TA_LEFT,

        textColor=
            TEXT,
    )

    body_bold_style = ParagraphStyle(
        "BodyBold",

        parent=
            body_style,

        fontName=
            "Helvetica-Bold",
    )

    label_style = ParagraphStyle(
        "Label",

        parent=
            base_styles["Normal"],

        fontName=
            "Helvetica-Bold",

        fontSize=
            6.7,

        leading=
            8,

        textColor=
            MUTED,
    )

    value_style = ParagraphStyle(
        "Value",

        parent=
            base_styles["Normal"],

        fontName=
            "Helvetica-Bold",

        fontSize=
            8.6,

        leading=
            10,

        textColor=
            TEXT,
    )

    table_header_style = ParagraphStyle(
        "TableHeader",

        parent=
            base_styles["Normal"],

        fontName=
            "Helvetica-Bold",

        fontSize=
            7.7,

        leading=
            9,

        textColor=
            colors.white,

        alignment=
            TA_LEFT,
    )

    table_quantity_style = ParagraphStyle(
        "Quantity",

        parent=
            base_styles["Normal"],

        fontName=
            "Helvetica-Bold",

        fontSize=
            9,

        leading=
            11,

        textColor=
            NAVY_DARK,

        alignment=
            TA_CENTER,
    )

    table_description_style = ParagraphStyle(
        "Description",

        parent=
            base_styles["Normal"],

        fontName=
            "Helvetica",

        fontSize=
            8.6,

        leading=
            11,

        textColor=
            TEXT,
    )

    story = []

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    logo_asset = _existing_asset(
        LOGO_CANDIDATES
    )

    if logo_asset:
        logo = Image(
            str(
                logo_asset
            ),
            width=
                61 * mm,
            height=
                19 * mm,
        )
    else:
        logo = Paragraph(
            (
                "<b>MINISTERIO DEL PODER POPULAR "
                "PARA HÁBITAT Y VIVIENDA</b>"
            ),
            body_bold_style,
        )

    document_header = Table(
        [
            [
                logo,

                Table(
                    [
                        [
                            Paragraph(
                                "DOCUMENTO INSTITUCIONAL",
                                eyebrow_style,
                            )
                        ],

                        [
                            Paragraph(
                                "NOTA DE ENTREGA",
                                title_style,
                            )
                        ],

                        [
                            Paragraph(
                                _safe(
                                    note.number
                                ),
                                value_style,
                            )
                        ],

                        [
                            Paragraph(
                                note.delivery_date.strftime(
                                    "%d/%m/%Y"
                                ),
                                eyebrow_style,
                            )
                        ],
                    ],

                    colWidths=[
                        64 * mm,
                    ],
                ),
            ]
        ],

        colWidths=[
            96 * mm,
            72 * mm,
        ],

        hAlign=
            "LEFT",
    )

    document_header.setStyle(
        TableStyle([
            (
                "VALIGN",
                (
                    0,
                    0,
                ),
                (
                    -1,
                    -1,
                ),
                "MIDDLE",
            ),

            (
                "ALIGN",
                (
                    1,
                    0,
                ),
                (
                    1,
                    0,
                ),
                "RIGHT",
            ),

            (
                "LEFTPADDING",
                (
                    0,
                    0,
                ),
                (
                    -1,
                    -1,
                ),
                0,
            ),

            (
                "RIGHTPADDING",
                (
                    0,
                    0,
                ),
                (
                    -1,
                    -1,
                ),
                0,
            ),

            (
                "TOPPADDING",
                (
                    0,
                    0,
                ),
                (
                    -1,
                    -1,
                ),
                0,
            ),

            (
                "BOTTOMPADDING",
                (
                    0,
                    0,
                ),
                (
                    -1,
                    -1,
                ),
                0,
            ),
        ])
    )

    story.append(
        document_header
    )

    story.append(
        Spacer(
            1,
            5 * mm,
        )
    )

    # Línea institucional.
    brand_line = Table(
        [["", "", ""]],

        colWidths=[
            84 * mm,
            42 * mm,
            42 * mm,
        ],

        rowHeights=[
            2.3 * mm,
        ],
    )

    brand_line.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (
                    0,
                    0,
                ),
                (
                    0,
                    0,
                ),
                YELLOW,
            ),

            (
                "BACKGROUND",
                (
                    1,
                    0,
                ),
                (
                    1,
                    0,
                ),
                BLUE,
            ),

            (
                "BACKGROUND",
                (
                    2,
                    0,
                ),
                (
                    2,
                    0,
                ),
                RED,
            ),

            (
                "LEFTPADDING",
                (
                    0,
                    0,
                ),
                (
                    -1,
                    -1,
                ),
                0,
            ),

            (
                "RIGHTPADDING",
                (
                    0,
                    0,
                ),
                (
                    -1,
                    -1,
                ),
                0,
            ),

            (
                "TOPPADDING",
                (
                    0,
                    0,
                ),
                (
                    -1,
                    -1,
                ),
                0,
            ),

            (
                "BOTTOMPADDING",
                (
                    0,
                    0,
                ),
                (
                    -1,
                    -1,
                ),
                0,
            ),
        ])
    )

    story.append(
        brand_line
    )

    story.append(
        Spacer(
            1,
            7 * mm,
        )
    )

    # --------------------------------------------------------
    # FECHA + PARTICIPANTES
    # --------------------------------------------------------

    meta_table = Table(
        [
            [
                Paragraph(
                    "ENTREGA",
                    label_style,
                ),

                Paragraph(
                    "RECIBE",
                    label_style,
                ),
            ],

            [
                Paragraph(
                    _safe(
                        note.delivered_by_name
                    ),
                    value_style,
                ),

                Paragraph(
                    _safe(
                        note.recipient_name
                    ),
                    value_style,
                ),
            ],

            [
                Paragraph(
                    (
                        "C.I. "
                        +
                        _safe(
                            _document_number(
                                note.delivered_by_document
                            )
                        )
                    ),
                    body_style,
                ),

                Paragraph(
                    (
                        "C.I. "
                        +
                        _safe(
                            _document_number(
                                note.recipient_document
                            )
                        )
                    ),
                    body_style,
                ),
            ],
        ],

        colWidths=[
            84 * mm,
            84 * mm,
        ],

        hAlign=
            "LEFT",
    )

    meta_table.setStyle(
        TableStyle([
            (
                "BOX",
                (0, 0),
                (-1, -1),
                0.6,
                BORDER,
            ),
            (
                "INNERGRID",
                (0, 0),
                (-1, -1),
                0.35,
                BORDER,
            ),
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                SOFT,
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE",
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                9,
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                9,
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                7,
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                7,
            ),
        ])
    )

    story.append(
        meta_table
    )


    story.append(
        Spacer(
            1,
            7 * mm,
        )
    )

    # --------------------------------------------------------
    # TEXTO FORMAL SIMILAR AL MODELO
    # --------------------------------------------------------

    intro = (
        _date_sentence(
            note.delivery_date
        )
        +
        f"Yo <b>{_safe(note.delivered_by_name)}</b>, "
        f"titular de la cédula de identidad Nro. "
        f"<b>{_safe(_document_number(note.delivered_by_document))}</b>, "
        f"dejo constancia de que hago entrega al ciudadano(a) "
        f"<b>{_safe(note.recipient_name)}</b>, "
        f"titular de la C.I. Nro. "
        f"<b>{_safe(_document_number(note.recipient_document))}</b>, "
        f"quien recibe conforme los bienes que se detallan a continuación:"
    )

    story.append(
        Paragraph(
            intro,
            body_style,
        )
    )

    story.append(
        Spacer(
            1,
            7 * mm,
        )
    )

    # --------------------------------------------------------
    # PRODUCTOS: SOLO CANTIDAD + DESCRIPCIÓN
    # --------------------------------------------------------

    table_data = [
        [
            Paragraph(
                "CANTIDAD",
                table_header_style,
            ),

            Paragraph(
                "DESCRIPCIÓN",
                table_header_style,
            ),
        ]
    ]

    items = (
        note.items
        .select_related(
            "product",
        )
        .all()
    )

    for item in items:
        description = (
            item.product_description_snapshot
            or
            item.product.description
        )

        table_data.append([
            Paragraph(
                _display_quantity(
                    item.quantity
                ),
                table_quantity_style,
            ),

            Paragraph(
                _safe(
                    description
                ),
                table_description_style,
            ),
        ])

    products_table = Table(
        table_data,

        colWidths=[
            34 * mm,
            134 * mm,
        ],

        repeatRows=
            1,

        hAlign=
            "LEFT",
    )

    products_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (
                    0,
                    0,
                ),
                (
                    -1,
                    0,
                ),
                NAVY,
            ),

            (
                "BOX",
                (
                    0,
                    0,
                ),
                (
                    -1,
                    -1,
                ),
                0.65,
                BORDER,
            ),

            (
                "INNERGRID",
                (
                    0,
                    0,
                ),
                (
                    -1,
                    -1,
                ),
                0.35,
                BORDER,
            ),

            (
                "ROWBACKGROUNDS",
                (
                    0,
                    1,
                ),
                (
                    -1,
                    -1,
                ),
                [
                    colors.white,
                    SOFT,
                ],
            ),

            (
                "VALIGN",
                (
                    0,
                    0,
                ),
                (
                    -1,
                    -1,
                ),
                "MIDDLE",
            ),

            (
                "ALIGN",
                (
                    0,
                    1,
                ),
                (
                    0,
                    -1,
                ),
                "CENTER",
            ),

            (
                "LEFTPADDING",
                (
                    0,
                    0,
                ),
                (
                    -1,
                    -1,
                ),
                9,
            ),

            (
                "RIGHTPADDING",
                (
                    0,
                    0,
                ),
                (
                    -1,
                    -1,
                ),
                9,
            ),

            (
                "TOPPADDING",
                (
                    0,
                    0,
                ),
                (
                    -1,
                    -1,
                ),
                8,
            ),

            (
                "BOTTOMPADDING",
                (
                    0,
                    0,
                ),
                (
                    -1,
                    -1,
                ),
                8,
            ),
        ])
    )

    story.append(
        products_table
    )

    story.append(
        Spacer(
            1,
            7 * mm,
        )
    )

    story.append(
        Paragraph(
            "Sin más a que hacer referencia,",
            body_style,
        )
    )

    if (
        note.observations
        and
        note.observations.strip()
    ):
        story.append(
            Spacer(
                1,
                5 * mm,
            )
        )

        observations_table = Table(
            [
                [
                    Paragraph(
                        "OBSERVACIONES",
                        label_style,
                    )
                ],

                [
                    Paragraph(
                        _safe(
                            note.observations
                        ),
                        body_style,
                    )
                ],
            ],

            colWidths=[
                168 * mm,
            ],
        )

        observations_table.setStyle(
            TableStyle([
                (
                    "BOX",
                    (
                        0,
                        0,
                    ),
                    (
                        -1,
                        -1,
                    ),
                    0.5,
                    BORDER,
                ),

                (
                    "BACKGROUND",
                    (
                        0,
                        0,
                    ),
                    (
                        -1,
                        0,
                    ),
                    SOFT,
                ),

                (
                    "LEFTPADDING",
                    (
                        0,
                        0,
                    ),
                    (
                        -1,
                        -1,
                    ),
                    9,
                ),

                (
                    "RIGHTPADDING",
                    (
                        0,
                        0,
                    ),
                    (
                        -1,
                        -1,
                    ),
                    9,
                ),

                (
                    "TOPPADDING",
                    (
                        0,
                        0,
                    ),
                    (
                        -1,
                        -1,
                    ),
                    7,
                ),

                (
                    "BOTTOMPADDING",
                    (
                        0,
                        0,
                    ),
                    (
                        -1,
                        -1,
                    ),
                    7,
                ),
            ])
        )

        story.append(
            observations_table
        )

    # --------------------------------------------------------
    # FIRMAS
    # --------------------------------------------------------

    story.append(
        Spacer(
            1,
            18 * mm,
        )
    )

    signature_style = ParagraphStyle(
        "Signature",

        parent=
            base_styles["Normal"],

        fontName=
            "Helvetica-Bold",

        fontSize=
            8,

        leading=
            10,

        textColor=
            TEXT,

        alignment=
            TA_CENTER,
    )

    signature_meta_style = ParagraphStyle(
        "SignatureMeta",

        parent=
            base_styles["Normal"],

        fontName=
            "Helvetica",

        fontSize=
            7,

        leading=
            9,

        textColor=
            MUTED,

        alignment=
            TA_CENTER,
    )

    signatures = Table(
        [
            [
                Paragraph(
                    "ENTREGA",
                    label_style,
                ),

                Paragraph(
                    "RECIBE",
                    label_style,
                ),
            ],

            [
                "",
                "",
            ],

            [
                Paragraph(
                    _safe(
                        note.delivered_by_name
                    ),
                    signature_style,
                ),

                Paragraph(
                    _safe(
                        note.recipient_name
                    ),
                    signature_style,
                ),
            ],

            [
                Paragraph(
                    (
                        "C.I. "
                        +
                        _safe(
                            _document_number(
                                note.delivered_by_document
                            )
                        )
                    ),
                    signature_meta_style,
                ),

                Paragraph(
                    (
                        "C.I. "
                        +
                        _safe(
                            _document_number(
                                note.recipient_document
                            )
                        )
                    ),
                    signature_meta_style,
                ),
            ],
        ],

        colWidths=[
            78 * mm,
            78 * mm,
        ],

        rowHeights=[
            6 * mm,
            13 * mm,
            None,
            None,
        ],

        hAlign=
            "CENTER",
    )

    signatures.setStyle(
        TableStyle([
            (
                "ALIGN",
                (
                    0,
                    0,
                ),
                (
                    -1,
                    -1,
                ),
                "CENTER",
            ),

            (
                "VALIGN",
                (
                    0,
                    0,
                ),
                (
                    -1,
                    -1,
                ),
                "BOTTOM",
            ),

            (
                "LINEABOVE",
                (
                    0,
                    2,
                ),
                (
                    0,
                    2,
                ),
                0.65,
                TEXT,
            ),

            (
                "LINEABOVE",
                (
                    1,
                    2,
                ),
                (
                    1,
                    2,
                ),
                0.65,
                TEXT,
            ),

            (
                "LEFTPADDING",
                (
                    0,
                    0,
                ),
                (
                    -1,
                    -1,
                ),
                8,
            ),

            (
                "RIGHTPADDING",
                (
                    0,
                    0,
                ),
                (
                    -1,
                    -1,
                ),
                8,
            ),
        ])
    )

    story.append(
        KeepTogether([
            signatures
        ])
    )

    doc.build(
        story,

        onFirstPage=
            _draw_page,

        onLaterPages=
            _draw_page,
    )

    pdf_bytes = (
        buffer.getvalue()
    )

    buffer.close()

    return pdf_bytes