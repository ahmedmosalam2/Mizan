"""
Image Generator — Pollinations.ai (مجاني بدون API key)
========================================================
بيولد صور إعلانية عبر HTTP request بسيط.
https://pollinations.ai/
"""

import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime


def generate_ad_image(
    prompt: str,
    output_dir: str = "benchmark_results/images",
    width: int = 1080,
    height: int = 1080,
    model: str = "flux",
) -> str:
    """
    يولد صورة إعلان عبر Pollinations.ai (مجاني، بدون API key).

    Args:
        prompt: وصف الصورة بالإنجليزي
        output_dir: مجلد الحفظ
        width: عرض الصورة
        height: ارتفاع الصورة
        model: موديل الصورة (flux / turbo)

    Returns:
        مسار الصورة المحفوظة
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    encoded = urllib.parse.quote(prompt)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={width}&height={height}&model={model}&nologo=true"
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(output_dir) / f"ad_{timestamp}.png"

    try:
        # Pollinations.ai requires a User-Agent header or returns 403 Forbidden
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; MizanAdBot/1.0)",
                "Referer":    "https://pollinations.ai/",
                "Accept":     "image/png,image/*,*/*",
            }
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            output_path.write_bytes(response.read())
        return str(output_path)
    except Exception as e:
        raise RuntimeError(f"Image generation failed: {e}\nURL: {url}")


def build_ad_image_prompt(product: dict, market: str = "KSA") -> str:
    """
    يبني prompt إنجليزي مناسب للصورة بناءً على بيانات المنتج بشكل ديناميكي.
    """
    name_en = product.get("name_en", "Product").lower()
    price = product.get("price_sar", "")
    discount = product.get("discount_pct", "")

    # تحديد بيئة عرض المنتج ديناميكياً بناءً على الكلمات المفتاحية
    setting = "on an elegant wooden stand in a cozy living room decorated with soft Ramadan lights"
    if any(k in name_en for k in ["fryer", "cook", "oven", "kitchen", "kettle", "coffee", "pot"]):
        setting = "on a modern marble kitchen countertop decorated with small Ramadan lanterns"
    elif any(k in name_en for k in ["phone", "laptop", "tablet", "watch", "gadget", "device"]):
        setting = "placed on a premium wooden desk with cozy ambient lighting and subtle Islamic patterns"
    elif any(k in name_en for k in ["perfume", "oud", "cologne", "scent", "beauty"]):
        setting = "resting on a luxury marble pedestal surrounded by delicate white flowers and warm golden rays"

    discount_str = f"with a {discount}% discount badge" if discount else ""
    price_str = f"showing a price of {price} SAR" if price else ""

    return (
        f"A premium commercial marketing photo of a modern sleek {product.get('name_en')}, "
        f"{setting}. In the background, soft warm Ramadan lights, stars, and a subtle crescent moon are visible. "
        f"The photo includes a professional layout {price_str} {discount_str}. "
        f"Cinematic lighting, ultra-realistic product photography, 8k resolution, premium advertising style."
    )

