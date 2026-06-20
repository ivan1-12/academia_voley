from flask_babel import gettext as _
import re
import urllib.request
import socket


def validar_campo_numerico(valor):
    """Permite única y estrictamente números (ej. teléfonos, documentos/cédula, edades)."""
    if not valor:
        return False
    return str(valor).isdigit()


def validar_nombre_texto(valor):
    """Permite letras, espacios y caracteres comunes en nombres propios."""
    if not valor:
        return False
    # Acepta letras con acentos, Ñ, ñ, Ü, espacios, guiones y apóstrofes
    regex = r"^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s\-\'’]+$"
    return bool(re.match(regex, valor))


def validar_password_estricta(password):
    """
    Exige obligatoriamente un mínimo de 8 caracteres, un máximo de 16 caracteres,
    y la inclusión de al menos un carácter especial (ej. @, #, $, %, etc.).
    """
    if not password:
        return False, _("La contraseña no puede estar vacía.")
    if not (8 <= len(password) <= 16):
        return (
            False,
            _("La contraseña debe tener obligatoriamente entre 8 y 16 caracteres."),
        )

    # Caracteres especiales
    caracteres_especiales = set("@#$%^&*()-_=+[{]};:'\",<.>/?`|~!")
    tiene_especial = any(c in caracteres_especiales for c in password)

    if not tiene_especial:
        return (
            False,
            _("La contraseña debe incluir al menos un carácter especial (ej. @, #, $, %, etc.)."),
        )

    return True, ""


def validar_descripcion_entrenador(descripcion):
    """Valida que la descripción o biografía profesional tenga un límite máximo de 150 caracteres."""
    if not descripcion:
        return True
    return len(descripcion) <= 150


def verificar_conexion_internet(timeout=2):
    """Verifica de forma rápida si el servidor tiene acceso a internet."""
    try:
        urllib.request.urlopen("https://www.google.com", timeout=timeout)
        return True
    except Exception:
        return False


def validar_formato_email(email):
    """Valida la sintaxis del email localmente con regex."""
    regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(regex, email))


def verificar_dominio_email_dns(email):
    """Intenta resolver el dominio del email en el DNS para verificar su existencia."""
    try:
        parts = email.split("@")
        if len(parts) < 2:
            return False
        domain = parts[1]
        socket.getaddrinfo(domain, None)
        return True
    except Exception:
        return False


def verificar_email_registro(email, db_connection):
    """
    Verificación inteligente de correo según el estado de la conexión a internet.
    - Si hay internet: realiza verificación de formato, DNS del dominio y duplicados en DB.
    - Si no hay internet: omite verificación de dominio en línea, valida formato y duplicado en DB local.
    """
    if not email:
        return False, _("El correo electrónico es obligatorio.")

    if not validar_formato_email(email):
        return False, _("El formato del correo electrónico no es válido.")

    # Verificar duplicados en la base de datos
    cur = db_connection.cursor()
    try:
        cur.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
        if cur.fetchone():
            return False, _("El correo electrónico ya está registrado.")
    finally:
        cur.close()

    # Verificar conectividad a internet
    online = verificar_conexion_internet()
    if online:
        if not verificar_dominio_email_dns(email):
            return (
                False,
                _("El dominio del correo electrónico no parece existir o no tiene registros DNS activos."),
            )
        return True, _("Email válido y disponible (Verificación online completada).")
    else:
        return (
            True,
            _(
                "Email con formato válido. Nota: Sin conexión a internet, se omitió la verificación de dominio en línea."
            ),
        )
