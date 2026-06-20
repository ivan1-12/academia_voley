"""Actualiza entradas de traducción que tienen msgstr idéntico a msgid.

Este script rellenará automáticamente las entradas del archivo .po para
los idiomas pt y fr donde msgstr todavía sea igual al texto original.
"""

from pathlib import Path
from babel.messages import pofile, mofile
from deep_translator import GoogleTranslator

TRANSLATIONS = ["pt", "fr"]
BASE_DIR = Path("translations")


def load_catalog(lang):
    po_path = BASE_DIR / lang / "LC_MESSAGES" / "messages.po"
    with open(po_path, "rb") as pf:
        catalog = pofile.read_po(pf)
    return catalog, po_path


def save_catalog(catalog, po_path):
    mo_path = po_path.with_suffix(".mo")
    with open(po_path, "wb") as pf:
        pofile.write_po(pf, catalog)
    with open(mo_path, "wb") as mf:
        mofile.write_mo(mf, catalog)
    print(f"Guardado {po_path} y {mo_path}")


def needs_translation(entry):
    if not entry.id or not isinstance(entry.id, str):
        return False
    source = entry.id.strip()
    if not source:
        return False
    target = entry.string.strip() if entry.string else ""
    if target == "" or target == source:
        return True
    return False


def update_translations(lang):
    catalog, po_path = load_catalog(lang)
    entries = [entry for entry in catalog if needs_translation(entry)]
    if not entries:
        print(f"{lang}: no hay entradas para actualizar")
        return
    print(f"{lang}: actualizando {len(entries)} entradas")
    translator = GoogleTranslator(source="es", target=lang)
    messages = [entry.id.strip() for entry in entries]
    translated = translator.translate_batch(messages)
    for entry, text in zip(entries, translated):
        entry.string = text
    save_catalog(catalog, po_path)


if __name__ == "__main__":
    for language in TRANSLATIONS:
        update_translations(language)
    print("Actualización completada.")
