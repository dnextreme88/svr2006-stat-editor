"""Locate data files whether running from source or from a PyInstaller bundle."""
import os
import sys


def app_dir():
    """Folder the user sees: next to the .exe when frozen, else the source dir."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def bundle_dir():
    """PyInstaller's temporary extraction dir (onefile), else the app dir."""
    return getattr(sys, "_MEIPASS", app_dir())


def resource(name):
    """Prefer a file sitting next to the exe so users can edit the .txt lists,
    fall back to the copy baked into the bundle."""
    external = os.path.join(app_dir(), name)
    if os.path.exists(external):
        return external
    return os.path.join(bundle_dir(), name)


def tmp_dir():
    path = os.path.join(app_dir(), "tmp")
    if not os.path.exists(path):
        os.makedirs(path)
    return path
