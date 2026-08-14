# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Overview

A **Python 3 / PyQt5 desktop tool** that edits superstar stats in **WWE SmackDown vs
RAW 2006** data files (`DAT_.PAC`, `FDAT.PAC`). It is a modernized port of
eatrawmeat391's original Python 2.7 / PyQt4 tool.

The data files are **Yuke's PAC/PACH archives**; each superstar's stats live in a
159-byte record that is **BPE-compressed** inside the archive. The editor decompresses
those records, exposes the fields in a form, and on save recompresses (via the external
`bpe.exe`) and rebuilds the archive.

## Commands

Run from source (no build needed):

```bash
python layout_stat_editor_gui.py
```

Run the round-trip self-test (no GUI, no `bpe.exe` required — run this before building):

```bash
python selftest.py
```

Build the Windows executable (Windows only — PyInstaller cannot cross-compile):

```bash
build.bat
```

Build by hand:

```bash
pip install -r requirements.txt
pyinstaller stat_editor.spec --noconfirm --clean
```

The finished program lands at `dist/stat_editor_gui.exe`. Copy `bpe.exe` next to it to
enable saving.

## Architecture & data flow

**Open:** `PAC` reads the archive TOC → each entry with a `BPE ` magic is decompressed by
`extract_bpe()` → the 159-byte record is decoded by `Stat_Editor.stat_from_data()` into a
flat list → all records collect into `Stat_Editor.stat_list` (one list per superstar).

**Edit:** the GUI is a two-panel layout — a **searchable roster list** (`QListWidget`)
on the left, the editor form on the right. Picking a row selects a superstar; the GUI
reads and writes `stat_list` **by numeric index** (see `FIELDS` in
[`Stat_Editor.py`](Stat_Editor.py) and `STAT_FIELDS` in
[`layout_stat_editor_gui.py`](layout_stat_editor_gui.py)). "Set stat" copies widget
values back into the record's list; "Default" restores from `backup_stat`.

**Roster search.** The left panel's search box (`filter_superstar_list`) is a
case-insensitive **substring filter** over each row's whole `"0xNN : Name"` label, so a
name (`edge`) or a hex (`0a`) both narrow the list; a query matching nothing hides every
row. It only shows/hides rows — the parsed hex → `stat_list` index mapping is unchanged.
The roster labels are (re)built from `stat_list` in `update_superstar_list`, called on
open (and after Save, which reopens the file).

**Save:** `data_from_stat()` re-encodes each record → written to a temp file →
recompressed by shelling out to `bpe.exe` → a `BPE ` header is prepended →
`PAC.rebuild()` reassembles the archive as `<file>-NEW` (2048-byte aligned) → the
original is renamed `<file>.bak` and `-NEW` is moved into place.

**Record layout.** Each record is `RECORD_SIZE = 159` bytes, described by the `FIELDS`
table in `Stat_Editor.py` as `(index, offset, size, kind)` where `kind` is `int`, `str`
(NUL-padded), or `raw`. **`raw` fields are unknown blobs preserved byte-for-byte** so
nothing outside the known fields is corrupted — `selftest.py` verifies this.

## File guide

| File | Role |
|---|---|
| `layout_stat_editor_gui.py` | PyQt5 window + all form logic; app entry point (`main()`). Maps widgets ↔ `stat_list` indices, loads the `.txt` lookup tables. |
| `Stat_Editor.py` | Core model: 159-byte record layout (`FIELDS`, `RECORD_SIZE`), PAC decode → `stat_list`, re-encode, and save (BPE recompress + rebuild). |
| `pac.py` | Yuke PAC/PACH archive reader/rebuilder (`PAC` class). |
| `yuke_bpe.py` | Pure-Python BPE decompressor (`extract_bpe`). |
| `control.py` | `pac_file`: buffered binary file wrapper (seek/tell/read helpers). |
| `data_op.py` | Byte helpers: `read_int`, `read_string`, `fill_string`, `string_shortener`, `int_to_string`. |
| `str_op.py` | String/filename helpers; `string_get_file_extension()` (magic-byte → extension). |
| `apppaths.py` | Locates data files whether run from source or a PyInstaller bundle. |
| `country.txt`, `province.txt`, `weight.txt`, `attire.txt` | `HH = Name` lookup tables (hex byte → label) feeding GUI combo boxes. |
| `height.txt` | `HHHH = Name` lookup table (2-byte height value → label). |
| `stat_editor_icon.ico` | App icon. |
| `bpe.exe` | External recompressor — **required for Save only**. |
| `stat_editor.spec`, `build.bat` | PyInstaller build config + Windows build script. |
| `selftest.py` | No-GUI round-trip test; run before building. |
| `requirements.txt` | Runtime/build deps (PyQt5, pyinstaller). |

## Conventions & gotchas

- **Bytes everywhere, `latin-1`.** Names and raw fields are handled as `bytes`; strings
  are decoded/encoded with `latin-1` (see `data_op.py`, `str_op.py`).
- **Stats are displayed ×5.** The GUI shows a stat as `value * 5` and stores it back as
  `value // 5` (spinbox range 0–100, step 5). Integer division matters — a float here
  would corrupt the byte on save.
- **`stat[8]` and `stat[11]` are both written from the Show dropdown**, deliberately
  mirroring the original tool.
- **`bpe.exe` is only needed to save.** The editor opens and edits without it.
- **`.txt` lookup tables are preferred from the copy next to the exe** (see
  `apppaths.resource()`) so users can edit them without rebuilding; the bundled copies
  are the fallback.
- **Build is Windows-only** and should be preceded by a passing `selftest.py`.

## Keeping this file current

**Treat CLAUDE.md as part of the change, not an afterthought.** Whenever a change alters
behavior, adds/removes files, changes the data flow, changes GUI fields, or changes the
build/run/test commands, **update the relevant section of this file in the same change**
so it never goes stale. Examples:

- Adding a GUI search feature → document it under Architecture / conventions.
- Removing an unused field → update the record-layout notes and the file guide.
- Adding a dependency or build step → update Commands and `requirements.txt` notes.

## Git & branch conventions

**Commits** follow [Conventional Commits](https://www.conventionalcommits.org):
`type(scope): summary`, where `type` is one of `feat`, `fix`, `docs`, `refactor`,
`test`, `build`, `chore`, etc. (`scope` optional).

- **Subject line (first line): never exceed 100 characters.**
- **Body (the lines after the blank line, up to but not including the
  `Co-Authored-By: Claude` trailer): never exceed 200 characters in total.**

**Branches** use `type/YYYYMMDD-short-description`, for example:

- `feat/20260814-add-search`
- `fix/20260815-incorrect-data`

## Credits

Original tool by **eatrawmeat391**. This repo is the Python 3 / PyQt5 port.
