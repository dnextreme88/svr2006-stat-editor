# WWE Smackdown vs RAW 2006 Stat Editor

Originally written by **eatrawmeat391** using Python 2.7 + Pyt4, this is a Python 3 + PyQt5 port of his SVR 2006 Stat Editor. The goal is to make it modernized, clean the codebase and improve the GUI tool.

## Compiling — building the executable

You must build **on Windows**: PyInstaller cannot cross-compile, so a Windows `.exe` has to come from a Windows machine.

1. Install Python 3 from <https://www.python.org/downloads/windows/>. Tick **"Add python.exe to PATH"** during setup.
2. You need to have the `bpe.exe` on the repository root. Without it, the editor still opens and edits files but cannot save and create a built executable.
3. Double-click on **`build.bat`**. The finished program will be located at `/dist/stat_editor_gui.exe`.

### Doing it by hand

```bat
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python selftest.py
pyinstaller stat_editor.spec --noconfirm --clean
```

### Running from source (no build)

```bat
pip install PyQt5
python layout_stat_editor_gui.py
```

## File Structure

There are 5 `.txt` files baked into the exe and the program prefers that they do not get deleted as values are sourced here for some fields in the GUI. `HH` refers to its hex equivalent when viewed on a hex editor.

| File | Notes |
|---|---|
| `stat_editor_icon.ico` | app icon |
| `country.txt` | `HH = Name` |
| `province.txt` | `HH = Name` |
| `weight.txt` | `HH = Name` |
| `attire.txt` | `HH = Name` |
| `height.txt` | `HHHH = Name` |
| `bpe.exe` | **required for saving** — not redistributable inside the spec unless you copy it in |
| `Stat_Editor.py` | reads/writes the 159-byte stat records |
| `apppaths.py` | finds data files whether run from source or frozen |
| `control.py` | buffered binary file wrapper |
| `data_op.py`, `str_op.py` | byte and string helpers |
| `layout_stat_editor_gui.py` | PyQt5 window, all the form logic |
| `pac.py` | Yuke's PAC/PACH archive reader and rebuilder |
| `selftest.py` | round-trip tests — run before building |
| `yuke_bpe.py` | BPE decompressor |

## Changes from the original

Some of these are fixes the port required or deserved; others are new features the original never had.

**Required by Python 3**

- `cStringIO` / `str`-as-bytes → `bytes` and `io.BytesIO` throughout.
- Integer division: `spinbox.value() / 5` → `// 5` (in Python 3 the original would have written a float into a byte field and crashed on save).
- `numpy` dropped; `yuke_bpe` uses a `bytearray` scratch buffer instead. That removes a ~30 MB dependency from the build.
- PyQt4 → PyQt5: widgets moved to `QtWidgets`, and `len(combobox)` — which worked in PyQt4 — became `combobox.count()`.
- `xrange` → `range`, `print` statement → function.

**New features**

- **Change log.** A full-width panel beneath the form records every "Set stat" as per-field diffs (`Field: old ---> new`) and logs Open/Save operations; resizing the window taller grows the log.
- **Combo re-ordering.** The setting combo boxes and their labels were rearranged into a single-column order (Enable, Show, Tactic, Gender, Nickname Placement, Country, Province, Weight, Height, Attire 1, Attire 2, Selection Order) instead of the original's two-column grouping.
- **Editable Selection Order.** Offset `0x9C`, previously preserved as a raw blob, is now an editable ordinal dropdown — `0x00 : 1st` through `0xA6 : 167th`.
- **Nickname label.** The "Nick Name" field label was renamed to "Nickname".
- **Roster list layout.** The single top superstar dropdown was replaced with a two-panel layout: a scrollable roster list on the left and a single-column editor form on the right.
- **Roster search.** A search box above the roster filters it case-insensitively by name (e.g. `Edge`) or hex (e.g. `0A`).
- **Roster sort.** The roster can be sorted by hex, name, or Selection Order, in ascending or descending order.

**Bug fixes**

- **BPE decompressor.** The original pushed a pair onto the stack even after emitting a literal byte, which corrupts output and can run the stack index off the end of the buffer. The exe's actual bytecode jumps back to the loop head after a literal — the decompiler had flattened that branch into an `elif`. Fixed; all 40 BPE blobs in a real `gm_mode.pac` now decompress to exactly their declared size.
- **Disabled controls**. Controls are disabled until a file is loaded, so clicking "Set stat" with nothing open no longer throws.
- **File handles.** `pac_file` never closed its file; on save the original moved a file it still had open. Now closed explicitly.
- **Improve saving features**. Save failures show an error instead of leaving a half-written `-NEW` file and a dead progress bar.
- **Unknown archive type.** Feeding the tool a non-PAC file (e.g. a `DPAC`) left `name_size` undefined and crashed with an obscure `AttributeError`. It now reports what the file actually is.

**Preserved deliberately**

- Saving still shells out to `bpe.exe` to recompress, writes `<file>-NEW`, then renames the original to `<file>.bak` and moves `-NEW` into place.
- `stat[8]` and `stat[11]` are still both written from the Show dropdown, as in the original.
- The entire layout is preserved — those are copied through untouched, verified byte-for-byte by `selftest.py`.

## Testing

`python selftest.py` builds a `DAT_.PAC`, parses it, checks every one of the 159 bytes survives a decode/encode round trip, edits a record, and rebuilds the archive. It needs neither a GUI nor `bpe.exe`.

```
parse            OK  (3 records, names/ints decoded)
byte round-trip  OK  (all 159 bytes preserved, padding included)
edit + re-encode OK  (raw blocks untouched)
PAC rebuild      OK  (512 -> 2048 bytes, 2048-byte aligned)
```

## Credits

- To **eatrawmeat391** for his invaluable tool in easily modifying the superstars' attributes along with a simple GUI.
