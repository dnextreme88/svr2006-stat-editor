"""String / filename helpers.  Python 3 port: inputs are bytes."""

_SYMBOLS = b"!@#$%^&*()-_=+|\\/[]{}:;\"'<>,./?~`"


def _as_bytes(value):
    if isinstance(value, str):
        return value.encode("latin-1", "replace")
    return value


def string_fix(value):
    """Escape non-printable bytes as {XX} so they are safe in a filename."""
    value = _as_bytes(value)
    out = bytearray()
    last = len(value) - 1
    for i, c in enumerate(value):
        if c < 33 or c > 127:
            if c != 0x5C and i != last:
                out += ("{%.2X}" % c).encode("ascii")
        else:
            out.append(c)
    return out.decode("latin-1")


def is_string_invalid(value):
    """True if the blob contains bytes that cannot be part of an extension."""
    value = _as_bytes(value)
    for c in value:
        if c < 0x20 or c > 0x7F:
            return True
    return False


def string_get_file_extension(_data):
    """Guess a file extension from the first four bytes of an entry."""
    _data = _as_bytes(_data)
    if _data in (b"PAC ", b"PACH", b"DPAC", b"EPAC", b"HSPC", b"SHDC"):
        return ".pac"
    if _data == b"<?xm":
        return ".xml"
    if _data == b"BPE ":
        return ".bpe"
    if _data == b"\x1bLua":
        return ".lua"
    if not is_string_invalid(_data):
        _data = _data.lower().replace(b" ", b"")
        if len(_data) < 3:
            return ".dat"
        for char in _SYMBOLS:
            if char in _data:
                return ".dat"
        return "." + _data.decode("latin-1")
    return ".dat"
