import re
import unicodedata
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError


def normalize_text(value):
    """Normaliza texto para comparaciones sin perder el valor visible original."""
    if value is None:
        return ""

    text = str(value).strip()
    text = " ".join(text.split())
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.upper()


def normalize_header(value):
    text = normalize_text(value)
    text = re.sub(r"[^A-Z0-9]+", "_", text)
    return text.strip("_")


def parse_decimal(value, *, field_name="cantidad", allow_zero=True):
    """Convierte valores de Excel a Decimal con máximo 3 decimales."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"{field_name} está vacío.")

    if isinstance(value, Decimal):
        number = value
    elif isinstance(value, (int, float)):
        number = Decimal(str(value))
    else:
        text = str(value).strip().replace(" ", "")

        # Soporta valores como "22," o "12,5".
        if text.endswith(","):
            text = text[:-1]
        elif "," in text and "." not in text:
            text = text.replace(",", ".")
        elif "," in text and "." in text:
            # Formato común español: 1.234,50
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")

        try:
            number = Decimal(text)
        except (InvalidOperation, ValueError):
            raise ValidationError(f"{field_name} no es un número válido.")

    if number < 0 or (not allow_zero and number == 0):
        comparator = "mayor que cero" if not allow_zero else "igual o mayor que cero"
        raise ValidationError(f"{field_name} debe ser {comparator}.")

    if number.as_tuple().exponent < -3:
        raise ValidationError(f"{field_name} no puede tener más de 3 decimales.")

    return number
