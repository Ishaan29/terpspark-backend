import qrcode
import io
import base64
from PIL import Image


def generate_qr_code(ticket_code: str) -> str:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )

    qr.add_data(ticket_code)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_bytes = buffer.getvalue()
    img_base64 = base64.b64encode(img_bytes).decode('utf-8')

    return f"data:image/png;base64,{img_base64}"


def generate_ticket_code(timestamp: int, event_id: str) -> str:
    event_short = event_id[:8]
    return f"TKT-{timestamp}-{event_short}"
