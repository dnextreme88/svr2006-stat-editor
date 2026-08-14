"""Buffered binary file wrapper.  Python 3 port of the original control.py."""
import os


class pac_file(object):

    def __init__(self, filename, buffer=2048):
        self.filename = filename
        self.the_file = open(filename, "rb+")
        self.size = os.path.getsize(filename)
        self.buffer = buffer

    def close(self):
        if self.the_file and not self.the_file.closed:
            self.the_file.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def tell(self):
        return self.the_file.tell()

    def rewind(self):
        self.the_file.seek(0)

    def seek(self, offset, whence=0):
        self.the_file.seek(offset, whence)

    def write(self, data):
        if isinstance(data, str):
            data = data.encode("latin-1", "replace")
        self.the_file.write(data)

    def read_int(self, size):
        return int.from_bytes(self.the_file.read(size), "little")

    def read_string(self, size):
        """Read `size` bytes in `self.buffer`-sized chunks."""
        chunks = []
        remaining = size
        while remaining > 0:
            data = self.the_file.read(min(self.buffer, remaining))
            if not data:
                break
            chunks.append(data)
            remaining -= len(data)
        return b"".join(chunks)

    def int_to_string(self, number, size):
        return int(number).to_bytes(size, "little")
