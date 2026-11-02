import json
import qrcode
from io import BytesIO
from django.core.files import File

def generate_household_qr_payload(household):
    """
    Constructs a standardized, non-sensitive QR payload (FR-24).
    Contains ONLY unique household identifier and village code.
    Zero resident names, phone numbers, or PII embedded.
    """
    return json.dumps({
        'uid': household.uid,
        'vcode': household.village.code,
    }, separators=(',', ':'))


def generate_qr_image_file(household):
    """
    Renders QR code image in PNG format and returns a Django File object.
    """
    payload_str = generate_household_qr_payload(household)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(payload_str)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    filename = f"qr_{household.village.code}_{household.uid}.png"
    return File(buffer, name=filename)

