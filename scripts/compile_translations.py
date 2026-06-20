"""Compila los archivos .po en .mo dentro de translations/*/LC_MESSAGES.

Uso: python scripts/compile_translations.py
Requiere: Flask-Babel / Babel instalados (ya añadidos a requirements.txt).
"""

import os
from babel.messages import pofile, mofile


def compile_all(translations_dir="translations"):
    if not os.path.isdir(translations_dir):
        print("No se encontró el directorio translations/")
        return
    for lang in os.listdir(translations_dir):
        lc = os.path.join(translations_dir, lang, "LC_MESSAGES")
        po_path = os.path.join(lc, "messages.po")
        mo_path = os.path.join(lc, "messages.mo")
        if os.path.exists(po_path):
            os.makedirs(lc, exist_ok=True)
            with open(po_path, "rb") as pf:
                catalog = pofile.read_po(pf)
            with open(mo_path, "wb") as mf:
                mofile.write_mo(mf, catalog)
            print(f"Compilado: {mo_path}")


if __name__ == "__main__":
    compile_all()
