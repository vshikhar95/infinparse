"""Readable copies of password-protected statements (PDF via pikepdf, xls/xlsx via msoffcrypto-tool).
Needs the `decrypt` extra."""
import io
from pathlib import Path


def _decrypt_pdf(path, password, out):
    import pikepdf
    try:
        with pikepdf.open(path, password=password) as pdf:
            pdf.save(out)
    except pikepdf.PasswordError:
        return "wrong or missing password"
    except pikepdf.PdfError:  # its message carries the full path
        return "not a readable PDF"
    return None


def _decrypt_office(path, password, out):
    import msoffcrypto
    from msoffcrypto.exceptions import DecryptionError, FileFormatError, InvalidKeyError, ParseError
    buf = io.BytesIO()
    try:
        with open(path, "rb") as f:
            office = msoffcrypto.OfficeFile(f)
            office.load_key(password=password)
            office.decrypt(buf)
    except (InvalidKeyError, DecryptionError):
        return "wrong or missing password"
    except (FileFormatError, ParseError):
        return "not a readable Excel file"
    Path(out).write_bytes(buf.getvalue())
    return None


DECRYPTORS = {".pdf": _decrypt_pdf, ".xlsx": _decrypt_office, ".xls": _decrypt_office}


def decrypted(path: Path, password: str | None, tmpdir: Path) -> Path:
    """Decrypted copy of path in tmpdir, or path itself when password is None.
    A wrong password or unreadable file raises ValueError naming only the file, never a library traceback
    carrying the full path."""
    path = Path(path)
    if password is None:
        return path
    decrypt = DECRYPTORS.get(path.suffix.lower())
    if decrypt is None:
        raise ValueError(f"{path.name}: can't decrypt {path.suffix} files")
    out = Path(tmpdir) / path.name
    problem = decrypt(path, password, out)
    if problem:  # raised outside the except block, so no chained library error
        raise ValueError(f"{path.name}: {problem}")
    return out
