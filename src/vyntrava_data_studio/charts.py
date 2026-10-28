"""Deterministic PNG bars for grouped sales amounts."""

from decimal import Decimal, InvalidOperation
import io

from PIL import Image, ImageDraw, ImageFont

from .delivery import DeliveryError


def grouped_amounts_png(groups: dict[str, str]) -> bytes:
    """Render the ordered analysis breakdown without runtime metadata."""
    labels = list(groups)
    try:
        amounts = [Decimal(groups[label]) for label in labels]
    except (InvalidOperation, ValueError):
        raise DeliveryError("chart_range") from None
    if any(not amount.is_finite() or amount < 0 for amount in amounts):
        raise DeliveryError("chart_range")

    image = Image.new("RGB", (900, 500), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=18)
    small_font = ImageFont.load_default(size=15)
    top, right, bottom = 60, 860, 405
    maximum = max(amounts, default=Decimal(0))
    scale = maximum * Decimal("1.1") if maximum else Decimal(1)
    ticks = [format(scale * step / 4, ".2f") for step in range(5)]
    title_width = draw.textbbox((0, 0), "Importe", font=font)[2]
    tick_width = max(draw.textbbox((0, 0), tick, font=small_font)[2]
                     for tick in ticks)
    left = max(90, 16 + title_width + 16 + tick_width + 16)
    draw.text((450, 12), "Ventas por fecha", fill="#222222", font=font,
              anchor="mt")
    for step in range(5):
        y = bottom - (bottom - top) * step // 4
        draw.line((left, y, right, y), fill="#dddddd", width=1)
        draw.text((left - 10, y), ticks[step], fill="#333333", font=small_font,
                  anchor="rm")
    draw.line((left, top, left, bottom), fill="#444444", width=2)
    draw.line((left, bottom, right, bottom), fill="#444444", width=2)
    draw.text((16, (top + bottom) // 2), "Importe", fill="#222222",
              font=font, anchor="lm")
    if labels:
        slot = (right - left) / len(labels)
        width = min(80, slot * 0.65)
        for index, (label, amount) in enumerate(zip(labels, amounts)):
            center = left + slot * (index + 0.5)
            height = int((bottom - top) * amount / scale)
            draw.rectangle((round(center - width / 2), bottom - height,
                            round(center + width / 2), bottom), fill="#237a57")
            draw.text((center, bottom + 12), label, fill="#222222", font=small_font,
                      anchor="mt")
            draw.text((center, bottom - height - 8), format(amount, "f"),
                      fill="#222222", font=small_font, anchor="mb")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
