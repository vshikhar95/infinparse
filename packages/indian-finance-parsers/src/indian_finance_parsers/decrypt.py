"""Readable copies of password-protected statements (PDF via pikepdf, xls/xlsx via msoffcrypto-tool).
Needs the `decrypt` extra.

Errors name only the file. The libraries put the full path in their messages, so they are re-raised
`from None`: a traceback then shows only our ValueError, not the library error with the path."""
import io
from pathlib import Path


def _decrypt_pdf(path, password, out):
    import pikepdf
    try:
        try:
            pikepdf.open(path).close()
            return path  # opens without a password: nothing to decrypt
        except pikepdf.PasswordError:
            pass
        buf = io.BytesIO()
        with pikepdf.open(path, password=password) as pdf:
            pdf.save(buf)  # in memory first: a failed save leaves no partial plaintext on disk
    except pikepdf.PasswordError:
        raise ValueError(f"{path.name}: wrong or missing password") from None
    except pikepdf.PdfError:
        raise ValueError(f"{path.name}: not a readable PDF") from None
    return _write(out, buf)


def _decrypt_office(path, password, out):
    import msoffcrypto
    from msoffcrypto.exceptions import DecryptionError, FileFormatError, InvalidKeyError, ParseError
    buf = io.BytesIO()
    try:
        with open(path, "rb") as f:
            office = msoffcrypto.OfficeFile(f)
            if not office.is_encrypted():
                return path
            office.load_key(password=password)
            office.decrypt(buf)
    except (InvalidKeyError, DecryptionError):
        raise ValueError(f"{path.name}: wrong or missing password") from None
    except (FileFormatError, ParseError):
        raise ValueError(f"{path.name}: not a readable Excel file") from None
    return _write(out, buf)


def _write(out, buf):
    """Write the decrypted copy, refusing to replace an existing file (two statements with one name, or a
    file the caller didn't expect us to touch)."""
    try:
        with open(out, "xb") as f:
            f.write(buf.getvalue())
    except FileExistsError:
        raise ValueError(f"{out.name}: already exists in tmpdir; use an empty folder per file") from None
    return out


DECRYPTORS = {".pdf": _decrypt_pdf, ".xlsx": _decrypt_office, ".xls": _decrypt_office}


def decrypted(path: Path, password: str | None, tmpdir: Path) -> Path:
    """Decrypted copy of path in tmpdir. Returns path itself when password is None or the file isn't encrypted."""
    path = Path(path)
    if password is None:
        return path
    decrypt = DECRYPTORS.get(path.suffix.lower())
    if decrypt is None:
        raise ValueError(f"{path.name}: can't decrypt {path.suffix} files")
    out = Path(tmpdir) / path.name
    if out.resolve() == path.resolve():
        raise ValueError(f"{path.name}: tmpdir is the file's own folder; the copy would overwrite the original")
    return decrypt(path, password, out)
