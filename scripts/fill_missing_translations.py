"""Rellena traducciones faltantes en los archivos .po y compila los .mo.

Uso:
    python scripts/fill_missing_translations.py

Requiere:
    deep-translator, Babel
"""

import os
from pathlib import Path
from time import sleep

from babel.messages import pofile, mofile
from deep_translator import GoogleTranslator

SUPPORTED_LOCALES = ["en", "pt", "fr"]
TRANSLATIONS_DIR = Path("translations")
BATCH_SIZE = 10


def chunked(iterable, size):
    iterator = iter(iterable)
    while True:
        batch = []
        for _ in range(size):
            try:
                batch.append(next(iterator))
            except StopIteration:
                break
        if not batch:
            return
        yield batch


def needs_translation(entry):
    if not entry.id:
        return False
    if isinstance(entry.id, tuple):
        return False
    source_text = str(entry.id).strip()
    if not source_text:
        return False
    if not entry.string or not str(entry.string).strip():
        return True
    return source_text == str(entry.string).strip()


def translate_po(lang):
    po_path = TRANSLATIONS_DIR / lang / "LC_MESSAGES" / "messages.po"
    mo_path = TRANSLATIONS_DIR / lang / "LC_MESSAGES" / "messages.mo"

    if not po_path.exists():
        print(f"No existe {po_path}")
        return

    print(f"Procesando {po_path}...")
    with open(po_path, "rb") as pf:
        catalog = pofile.read_po(pf)

    entries_to_translate = [entry for entry in catalog if needs_translation(entry)]
    print(f"  Entradas a traducir: {len(entries_to_translate)}")
    if not entries_to_translate:
        print("  No hay entradas pendientes de traducción.")
        return

    translator = GoogleTranslator(source="es", target=lang)
    total = len(entries_to_translate)
    translated_count = 0
    for batch in chunked(entries_to_translate, BATCH_SIZE):
        texts = [str(entry.id).strip() for entry in batch]
        translated = translator.translate_batch(texts)
        for entry, translation in zip(batch, translated):
            entry.string = translation
        translated_count += len(batch)
        print(f"  Traducido {translated_count}/{total} entradas...")
        sleep(0.5)

    with open(po_path, "wb") as pf:
        pofile.write_po(pf, catalog)
    print(f"  Actualizado {po_path}")

    with open(mo_path, "wb") as mf:
        mofile.write_mo(mf, catalog)
    print(f"  Compilado {mo_path}")


if __name__ == "__main__":
    for locale in SUPPORTED_LOCALES:
        translate_po(locale)
    print("Traducciones faltantes completadas y compiladas.")
