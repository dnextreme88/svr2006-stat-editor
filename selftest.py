"""Round-trip self-test for the Python 3 port (no GUI, no bpe.exe needed)."""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pac import PAC
from data_op import read_int, int_to_string, fill_string, string_shortener
from Stat_Editor import Stat_Editor, FIELDS, RECORD_SIZE


def make_stat_record(name, nick, hud, seed):
    rec = bytearray(RECORD_SIZE)
    for i in range(10):
        rec[i] = (seed + i) % 21
    rec[12] = seed % 4
    rec[14:16] = int(0x0C63 + seed).to_bytes(2, "little")
    rec[18:18 + 22] = fill_string(name, 22)
    rec[64:64 + 20] = fill_string(nick, 20)
    rec[110:110 + 10] = fill_string(hud, 10)
    rec[136] = 0
    rec[137] = 3
    rec[144] = 3
    rec[145] = 1
    rec[146] = 2
    rec[153] = 5
    rec[154] = 7
    rec[157] = 1
    # sentinel bytes in the "raw" regions -- must survive a round trip
    rec[40:64] = bytes(range(24))
    rec[84:110] = bytes(range(26))
    rec[120:136] = bytes(range(16))
    return bytes(rec)


def build_pac(path, blobs):
    """Write a minimal 'PAC ' archive containing `blobs`."""
    name_size, offset_size, size_size = 2, 3, 3
    header = bytearray(b"PAC ")
    header += len(blobs).to_bytes(4, "little")
    body = bytearray()
    toc = bytearray()
    addr = 0
    for i, blob in enumerate(blobs):
        toc += i.to_bytes(name_size, "little")
        toc += addr.to_bytes(offset_size, "little")
        toc += len(blob).to_bytes(size_size, "little")
        pad = (4 - len(blob) % 4) % 4
        body += blob + b"\x00" * pad
        addr += len(blob) + pad
    with open(path, "wb") as fh:
        fh.write(header)
        fh.write(toc)
        fh.write(body)


def main():
    tmp = tempfile.mkdtemp(prefix="statedit_")
    try:
        records = [
            make_stat_record("Rey Mysterio", "Biggest Lil Man", "Mysterio", 3),
            make_stat_record("Eddie Guerrero", "Latino Heat", "Guerrero", 7),
            make_stat_record("JBL", "Wrestling God", "JBL", 11),
        ]
        pac_path = os.path.join(tmp, "DAT_.PAC")
        build_pac(pac_path, records)

        editor = Stat_Editor(pac_path)
        assert len(editor.stat_list) == 3, editor.stat_list

        s = editor.stat_list[0]
        assert s[15] == "Rey Mysterio", s[15]
        assert s[17] == "Biggest Lil Man", s[17]
        assert s[19] == "Mysterio", s[19]
        assert s[0] == 3 and s[1] == 4, (s[0], s[1])
        assert s[13] == 0x0C63 + 3, hex(s[13])
        assert s[22] == 3 and s[24] == 3 and s[25] == 1 and s[26] == 2
        assert s[28] == 5 and s[29] == 7 and s[31] == 1
        print("parse            OK  (%d records, names/ints decoded)" % len(editor.stat_list))

        # every byte must round-trip when nothing is edited
        for i, rec in enumerate(records):
            rebuilt = editor.data_from_stat(editor.stat_list[i])
            assert rebuilt == rec, "record %d differs at byte %d" % (
                i, next(j for j in range(RECORD_SIZE) if rebuilt[j] != rec[j]))
        print("byte round-trip  OK  (all %d bytes preserved, padding included)" % RECORD_SIZE)

        # edit, re-encode, re-parse
        editor.stat_list[1][0] = 20
        editor.stat_list[1][15] = "Latino Heat"
        editor.stat_list[1][13] = 0x0D00
        edited = editor.data_from_stat(editor.stat_list[1])
        reparsed = editor.stat_from_data(edited)
        assert reparsed[0] == 20 and reparsed[15] == "Latino Heat"
        assert reparsed[13] == 0x0D00
        assert reparsed[16] == bytes(range(24)), "raw block was clobbered"
        print("edit + re-encode OK  (raw blocks untouched)")

        # PAC rebuild round-trip
        out_dir = os.path.join(tmp, "extracted")
        editor.file.extract_all(is_gui=True, _dirname=out_dir)
        editor.file.rebuild(False, True, out_dir)
        with open(pac_path, "rb") as fh:
            original = fh.read()
        with open(pac_path + "-NEW", "rb") as fh:
            rebuilt = fh.read()
        assert rebuilt[:len(original)] == original, "rebuilt archive differs"
        print("PAC rebuild      OK  (%d -> %d bytes, 2048-byte aligned)"
              % (len(original), len(rebuilt)))

        editor.close()
        print("\nAll self-tests passed.")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
