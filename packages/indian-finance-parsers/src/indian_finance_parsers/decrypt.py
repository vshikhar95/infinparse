"""Password-protected statements (PDF via pikepdf, xls/xlsx via msoffcrypto-tool) decrypted in memory, so the
plaintext never touches disk. Needs the `decrypt` extra.

Errors name only the file. The libraries put the full path in their messages, so they are re-raised
`from None`: a traceback then shows only our ValueError, not the library error with the path."""
import io
from pathlib import Path


def _decrypt_pdf(path, password):
    import pikepdf
    try:
        try:
            pikepdf.open(path).close()
            return None  # opens without a password: nothing to decrypt
        except pikepdf.PasswordError:
            pass
        buf = io.BytesIO()
        with pikepdf.open(path, password=password) as pdf:
            pdf.save(buf)
    except pikepdf.PasswordError:
        raise ValueError(f"{path.name}: wrong or missing password") from None
    except pikepdf.PdfError:
        raise ValueError(f"{path.name}: not a readable PDF") from None
    return buf


def _decrypt_office(path, password):
    import msoffcrypto
    from msoffcrypto.exceptions import DecryptionError, FileFormatError, InvalidKeyError, ParseError
    buf = io.BytesIO()
    try:
        with open(path, "rb") as f:
            office = msoffcrypto.OfficeFile(f)
            if not office.is_encrypted():
                return None
            office.load_key(password=password)
            office.decrypt(buf)
    except (InvalidKeyError, DecryptionError):
        raise ValueError(f"{path.name}: wrong or missing password") from None
    except (FileFormatError, ParseError):
        raise ValueError(f"{path.name}: not a readable Excel file") from None
    return buf


DECRYPTORS = {".pdf": _decrypt_pdf, ".xlsx": _decrypt_office, ".xls": _decrypt_office}


def decrypted(path, password: str | None):
    """What to hand a parser: the path itself when password is None or the file isn't encrypted, otherwise the
    decrypted file as an in-memory io.BytesIO whose .name is the original file name (meta() reads names)."""
    path = Path(path)
    if password is None:
        return path
    decrypt = DECRYPTORS.get(path.suffix.lower())
    if decrypt is None:
        raise ValueError(f"{path.name}: can't decrypt {path.suffix} files")
    buf = decrypt(path, password)
    if buf is None:
        return path
    buf.seek(0)
    buf.name = path.name
    return buf
