import os

LOGO_CANDIDATES = ("logo.png", "logo.jpg", "logo.jpeg", "logo.webp", "logo.svg")


def resolve_brand_logo(static_folder):
    """Devuelve la ruta relativa static/images/<archivo> del logo activo, o None."""
    images_dir = os.path.join(static_folder, "images")
    for name in LOGO_CANDIDATES:
        if os.path.isfile(os.path.join(images_dir, name)):
            return f"images/{name}"
    return None
