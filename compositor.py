"""
Brand-asset compositor.
Overlays real logo + product PNGs onto AI-generated scenes using PIL.

This is how professional designers work — AI generates the scene/environment;
the real branded assets get composited on top for pixel-perfect accuracy.
"""
from pathlib import Path
from PIL import Image, ImageOps

# Position presets (fractions of image dimensions)
LOGO_POS = {
    "top-left":      (0.04, 0.04),
    "top-right":     (0.78, 0.04),
    "top-center":    (0.41, 0.04),
    "bottom-left":   (0.04, 0.87),
    "bottom-right":  (0.78, 0.87),
    "bottom-center": (0.41, 0.89),
}

# Product position = (x_center_frac, y_center_frac)
PRODUCT_POS = {
    "center":         (0.50, 0.55),
    "right-third":    (0.70, 0.55),
    "left-third":     (0.30, 0.55),
    "bottom-center":  (0.50, 0.72),
    "right-foreground": (0.72, 0.65),
}


# ─────────────────────────────── Asset loading ───────────────────────────────
def get_brand_assets(brand: dict, brands_dir: Path) -> dict:
    """
    Load and resolve asset paths from brand JSON.
    Returns {"logos": {primary, white, black}, "products": {name: path, ...}}.
    All paths returned are absolute strings or None.
    """
    assets = brand.get("assets") or {}

    def resolve(p):
        if not p:
            return None
        path = Path(p)
        if not path.is_absolute():
            path = brands_dir / p
        return str(path) if path.exists() else None

    return {
        "logos": {
            "primary": resolve(assets.get("logo_primary")),
            "white":   resolve(assets.get("logo_white")),
            "black":   resolve(assets.get("logo_black")),
        },
        "products": {
            name: resolve(p) for name, p in (assets.get("products") or {}).items()
            if resolve(p)
        },
    }


# ─────────────────────── Smart product detection from text ───────────────────────
def detect_product(post: dict, products: dict[str, str]) -> str | None:
    """Search post fields for a product name match; return asset path or None."""
    if not products:
        return None
    haystack = " ".join([
        str(post.get("main_topic", "")),
        str(post.get("key_topic", "")),
        str(post.get("caption", "")),
        str(post.get("visual_note", "")),
        str(post.get("script_slides", "")),
    ]).lower()

    # Try longest names first to avoid "Raftaar 120" being missed by "Raftaar"
    names_by_length = sorted(products.keys(), key=lambda n: -len(n))
    for name in names_by_length:
        if name.lower() in haystack:
            return products[name]
    return None


# ─────────────────────── Smart logo variant selection ───────────────────────
def pick_logo_variant(logos: dict, scene_path: str, position: str = "top-left") -> str | None:
    """
    Choose white vs colored logo based on the brightness of the scene region
    where the logo will sit.
    """
    primary = logos.get("primary")
    white = logos.get("white")
    black = logos.get("black")

    if not (white or black):
        return primary

    try:
        img = Image.open(scene_path).convert("L")
        W, H = img.size
        xf, yf = LOGO_POS.get(position, LOGO_POS["top-left"])
        x = int(W * xf)
        y = int(H * yf)
        # Sample a 25% × 12% rectangle around the logo position
        x2 = min(W, x + int(W * 0.25))
        y2 = min(H, y + int(H * 0.12))
        crop = img.crop((x, y, x2, y2))
        if crop.size[0] == 0 or crop.size[1] == 0:
            return primary
        avg = sum(crop.getdata()) / (crop.size[0] * crop.size[1])
        if avg < 110 and white:
            return white
        if avg > 175 and black:
            return black
        return primary
    except Exception:
        return primary


# ───────────────────────────── Composition ─────────────────────────────
def composite_assets(
    scene_path: str,
    output_path: str,
    logo_path: str = None,
    product_path: str = None,
    logo_position: str = "top-left",
    logo_width_frac: float = 0.18,
    product_position: str = "bottom-center",
    product_height_frac: float = 0.55,
    log=None,
) -> str:
    """
    Open the AI-generated scene and composite product (bottom) + logo (top).
    Saves the final image to output_path. Returns output_path.
    """
    scene = Image.open(scene_path).convert("RGBA")
    W, H = scene.size

    # ─── Product overlay (under logo) ───
    if product_path and Path(product_path).exists():
        try:
            prod = Image.open(product_path).convert("RGBA")
            target_h = int(H * product_height_frac)
            ratio = target_h / prod.height
            new_w = int(prod.width * ratio)
            prod = prod.resize((new_w, target_h), Image.LANCZOS)

            xc, yc = PRODUCT_POS.get(product_position, PRODUCT_POS["bottom-center"])
            x = int(W * xc - prod.width / 2)
            y = int(H * yc - prod.height / 2)
            x = max(20, min(W - prod.width - 20, x))
            y = max(20, min(H - prod.height - 20, y))

            # Soft shadow under product for grounding
            shadow = Image.new("RGBA", prod.size, (0, 0, 0, 0))
            shadow_alpha = prod.split()[-1].point(lambda a: int(a * 0.35))
            shadow = Image.new("RGBA", prod.size, (0, 0, 0, 255))
            shadow.putalpha(shadow_alpha)
            from PIL import ImageFilter
            shadow_blurred = shadow.filter(ImageFilter.GaussianBlur(radius=18))
            scene.paste(shadow_blurred, (x + 8, y + 18), shadow_blurred)

            scene.paste(prod, (x, y), prod)
            if log:
                log(f"     · product overlaid at ({x},{y})")
        except Exception as e:
            if log:
                log(f"     ⚠ product overlay failed: {e}")

    # ─── Logo overlay ───
    if logo_path and Path(logo_path).exists():
        try:
            logo = Image.open(logo_path).convert("RGBA")
            target_w = int(W * logo_width_frac)
            ratio = target_w / logo.width
            new_h = int(logo.height * ratio)
            logo = logo.resize((target_w, new_h), Image.LANCZOS)

            xf, yf = LOGO_POS.get(logo_position, LOGO_POS["top-left"])
            x = int(W * xf)
            y = int(H * yf)
            scene.paste(logo, (x, y), logo)
            if log:
                log(f"     · logo overlaid at ({x},{y})")
        except Exception as e:
            if log:
                log(f"     ⚠ logo overlay failed: {e}")

    scene.convert("RGB").save(output_path, "PNG", optimize=True)
    return output_path


# ─────────────────── Update brand JSON with new asset paths ───────────────────
def save_assets_to_brand(brand: dict, brands_dir: Path, brand_key: str,
                          logo_files: dict, product_files: dict) -> dict:
    """
    Copy files into brands/<key>_assets/ and update brand['assets'] in JSON.

    Args:
      logo_files:   {"primary": "C:/path/to/logo.png", "white": "...", "black": "..."}
      product_files: {"Raftaar 120": "C:/path/to/raftaar_120.png", ...}
    """
    import shutil, json
    assets_dir = brands_dir / f"{brand_key}_assets"
    assets_dir.mkdir(exist_ok=True)
    products_dir = assets_dir / "products"
    products_dir.mkdir(exist_ok=True)

    new_assets = brand.get("assets", {}) or {}

    # Logos
    for variant, src in (logo_files or {}).items():
        if not src or not Path(src).exists():
            continue
        dst = assets_dir / f"logo_{variant}.png"
        try:
            shutil.copy(src, dst)
            new_assets[f"logo_{variant}"] = f"{brand_key}_assets/logo_{variant}.png"
        except Exception as e:
            print(f"copy fail {src} -> {dst}: {e}")

    # Products
    existing_products = new_assets.get("products", {}) or {}
    for prod_name, src in (product_files or {}).items():
        if not src or not Path(src).exists():
            continue
        # Slugify product name
        safe = "".join(c for c in prod_name if c.isalnum() or c in "_-").strip("_") or "product"
        dst = products_dir / f"{safe.lower()}.png"
        try:
            shutil.copy(src, dst)
            existing_products[prod_name] = f"{brand_key}_assets/products/{safe.lower()}.png"
        except Exception as e:
            print(f"copy fail {src} -> {dst}: {e}")
    if existing_products:
        new_assets["products"] = existing_products

    brand["assets"] = new_assets
    # Persist brand JSON
    brand_file = brands_dir / f"{brand_key}.json"
    brand_file.write_text(json.dumps(brand, indent=2, ensure_ascii=False), encoding="utf-8")
    return brand
