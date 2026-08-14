"""Reads and writes the SVR 2006 superstar stat table.  Python 3 port.

Record layout (159 bytes per superstar).  Indices marked "raw" are blobs the
editor preserves untouched so nothing outside the known fields is corrupted.

  idx  off  size  field
    0    0    1   Strength      (0-20, displayed x5)
    1    1    1   Submission
    2    2    1   Speed
    3    3    1   Technical
    4    4    1   Durability
    5    5    1   Charisma
    6    6    1   Stamina
    7    7    1   Hardcore
    8    8    1   Show
    9    9    1   Tactic
   10   10    2   raw
   11   12    1   Show (mirror)
   12   13    1   raw
   13   14    2   Height
   14   16    2   raw
   15   18   22   Name
   16   40   24   raw
   17   64   20   Nickname
   18   84   26   raw
   19  110   10   HUD name
   20  120   16   raw
   21  136    1   Gender
   22  137    1   Weight
   23  138    6   raw
   24  144    1   Enable
   25  145    1   Attire 1 ID
   26  146    1   Attire 2 ID
   27  147    6   raw
   28  153    1   Country
   29  154    1   Province
   30  155    2   raw
   31  157    1   Nickname placement
   32  158    1   raw
"""
import ctypes
import os
import shutil
import subprocess
import sys

from pac import PAC
from yuke_bpe import extract_bpe
from data_op import read_int, read_string, fill_string, string_shortener, int_to_string
import apppaths

# (index, offset, size, kind) -- kind: "int", "str" (NUL-padded), "raw"
FIELDS = [
    (0, 0, 1, "int"), (1, 1, 1, "int"), (2, 2, 1, "int"), (3, 3, 1, "int"),
    (4, 4, 1, "int"), (5, 5, 1, "int"), (6, 6, 1, "int"), (7, 7, 1, "int"),
    (8, 8, 1, "int"), (9, 9, 1, "int"),
    (10, 10, 2, "raw"),
    (11, 12, 1, "int"),
    (12, 13, 1, "raw"),
    (13, 14, 2, "int"),
    (14, 16, 2, "raw"),
    (15, 18, 22, "str"),
    (16, 40, 24, "raw"),
    (17, 64, 20, "str"),
    (18, 84, 26, "raw"),
    (19, 110, 10, "str"),
    (20, 120, 16, "raw"),
    (21, 136, 1, "int"), (22, 137, 1, "int"),
    (23, 138, 6, "raw"),
    (24, 144, 1, "int"), (25, 145, 1, "int"), (26, 146, 1, "int"),
    (27, 147, 6, "raw"),
    (28, 153, 1, "int"), (29, 154, 1, "int"),
    (30, 155, 2, "raw"),
    (31, 157, 1, "int"),
    (32, 158, 1, "raw"),
]

RECORD_SIZE = 159


def call_cmd_ignore_error(cmd_call):
    """Run a child process, suppressing its console window and crash dialog."""
    subprocess_flags = 0
    if sys.platform.startswith("win"):
        SEM_NOGPFAULTERRORBOX = 2
        ctypes.windll.kernel32.SetErrorMode(SEM_NOGPFAULTERRORBOX)
        subprocess_flags = 0x08000000  # CREATE_NO_WINDOW
    return subprocess.call(cmd_call,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           creationflags=subprocess_flags)


def bpe_exe():
    """bpe.exe next to the exe, else the copy inside the bundle, else PATH."""
    path = apppaths.resource("bpe.exe")
    return path if os.path.exists(path) else "bpe"


class Stat_Editor(object):

    def __init__(self, filename="DAT_.pac"):
        self.filename = filename
        self.basename = os.path.basename(self.filename.upper())
        self.dirname = os.path.dirname(self.filename)
        self.file = PAC(self.filename)
        self.stat_list = []
        self.get_stat_data()

    def get_stat_data(self):
        for name in self.file.namelist():
            data = self.file.read(name)
            if data[0:4] == b"BPE ":
                data = extract_bpe(data)
            self.stat_list.append(self.stat_from_data(data))

    def stat_from_data(self, data):
        if len(data) < RECORD_SIZE:
            raise ValueError("stat record is %d bytes, expected %d"
                             % (len(data), RECORD_SIZE))
        out = []
        for _idx, off, size, kind in FIELDS:
            if kind == "int":
                out.append(read_int(data, off, size))
            elif kind == "str":
                out.append(string_shortener(read_string(data, off, size)))
            else:
                out.append(read_string(data, off, size))
        return out

    def data_from_stat(self, stat):
        out = bytearray()
        for idx, _off, size, kind in FIELDS:
            value = stat[idx]
            if kind == "int":
                out += int_to_string(value, size)
            elif kind == "str":
                out += fill_string(value, size)
            else:
                out += fill_string(value, size)
        return bytes(out)

    def set_stat_data(self):
        """Generator: writes every record, yielding progress 0-100."""
        file_list = self.file.namelist()
        work_dir = os.path.join(apppaths.tmp_dir(), "@%s" % self.basename)
        if not os.path.exists(work_dir):
            os.makedirs(work_dir)

        for x, name in enumerate(file_list):
            temp_bpe_file = os.path.join(work_dir, name)
            temp_unbpe_file = "%s.unpacked" % temp_bpe_file

            with open(temp_unbpe_file, "wb") as output:
                output.write(self.data_from_stat(self.stat_list[x]))

            call_cmd_ignore_error([bpe_exe(), temp_unbpe_file, temp_bpe_file,
                                   "4000", "8192", "200", "3"])

            with open(temp_unbpe_file, "rb") as fh:
                unbpe_size = len(fh.read())
            with open(temp_bpe_file, "rb") as fh:
                bpe_data = fh.read()

            header = (b"BPE \x00\x01\x00\x00"
                      + int_to_string(len(bpe_data), 4)
                      + int_to_string(unbpe_size, 4))
            with open(temp_bpe_file, "wb") as fh:
                fh.write(header)
                fh.write(bpe_data)

            yield float(x) / float(len(file_list)) * 100.0

        self.file.rebuild(False, False, work_dir)
        shutil.rmtree(work_dir)
        yield 100.0

    def close(self):
        self.file.close()
