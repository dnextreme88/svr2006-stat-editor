"""Byte-level helpers.  Python 3 port: every value here is `bytes`."""
import binascii


def read_int(content, offset, size):
    """Little-endian unsigned integer of `size` bytes at `offset`."""
    return int.from_bytes(content[offset:offset + size], "little")


def read_string(content, offset, size):
    """Raw slice, returned as bytes (may contain NULs / padding)."""
    return content[offset:offset + size]


def fill_string(value, size):
    """NUL-pad a name out to its fixed field width."""
    if isinstance(value, str):
        value = value.encode("latin-1", "replace")
    if len(value) > size:
        raise ValueError("value %r is longer than its %d-byte field" % (value, size))
    return value + b"\x00" * (size - len(value))


def string_shortener(value):
    """Cut a fixed-width field at the first NUL and decode it for display."""
    if isinstance(value, str):
        value = value.encode("latin-1", "replace")
    end = value.find(b"\x00")
    if end != -1:
        value = value[:end]
    return value.decode("latin-1")


def int_to_string(number, size):
    """Little-endian encoding of `number` into exactly `size` bytes."""
    return int(number).to_bytes(size, "little")


# kept for API compatibility with the original module
def hexlify(data):
    return binascii.hexlify(data)
