"""WWE SmackDown vs RAW 2006 Stat Editor -- original by eatrawmeat391.

Python 3 / PyQt5 port of the py2exe-frozen PyQt4 original.
"""
import os
import shutil
import sys

from PyQt5.QtCore import QRect
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QAction, QApplication, QComboBox, QFileDialog, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from Stat_Editor import Stat_Editor
import apppaths

WINDOW_TITLE = "WWE Smackdown VS RAW 2006 Stat Editor"
FILE_FILTER = "SVR 2006 Stat File (DAT_.PAC FDAT.PAC)"

STAT_FIELDS = [
    # (attribute, label, stat_list index, grid row, grid col)
    ("strength", "STR ", 0, 0, 0),
    ("speed", "SPD ", 2, 0, 2),
    ("submission", "SUB ", 1, 1, 0),
    ("charisma", "CHA ", 5, 1, 2),
    ("durability", "DUR ", 4, 2, 0),
    ("hardcore", "HRD ", 7, 2, 2),
    ("technical", "TEC ", 3, 3, 0),
    ("stamina", "STA ", 6, 3, 2),
]


def load_id_list(filename, id_width):
    """Parse 'HH = Name' / 'HHHH = Name' lookup tables shipped beside the exe."""
    path = apppaths.resource(filename)
    items = []
    if not os.path.exists(path):
        return items
    with open(path, "r", encoding="latin-1") as text_file:
        for line in text_file:
            line = line.rstrip("\r\n")
            if not line.strip():
                continue
            try:
                ident = int(line[0:id_width], 16)
            except ValueError:
                continue
            name = line[id_width + 3:]
            fmt = "0x%.2X : %s" if id_width == 2 else "0x%.4X : %s"
            items.append(fmt % (ident, name))
    return items


class Application(object):

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.win = QMainWindow()
        self.filename = ""
        self.dirname = ""
        self.file = None
        self.backup_stat = []

        icon_path = apppaths.resource("stat_editor_icon.ico")
        if os.path.exists(icon_path):
            self.app.setWindowIcon(QIcon(icon_path))
            self.win.setWindowIcon(QIcon(icon_path))

        # On-screen position (x=20, y=40) + a fallback size; the width/height
        # here are overridden by the resize() at the end of __init__.
        self.win.setGeometry(QRect(20, 40, 800, 640))
        # Minimum WIDTH floor (the window can never be narrower than this). The
        # minimum HEIGHT is set later from the form's natural height, so the
        # window can't shrink into the combos -- see setMinimumHeight below.
        self.win.setMinimumWidth(600)
        self.win.setWindowTitle(WINDOW_TITLE)

        self.bar = self.win.menuBar()
        self.file_menu = self.bar.addMenu("File")
        self.open_action = QAction("Open", self.win)
        self.open_action.setShortcut("CTRL+O")
        self.save_action = QAction("Save", self.win)
        self.save_action.setShortcut("CTRL+S")
        self.exit_action = QAction("Exit", self.win)
        self.file_menu.addAction(self.open_action)
        self.file_menu.addAction(self.save_action)
        self.file_menu.addAction(self.exit_action)
        self.open_action.triggered.connect(lambda checked=False: self.open_file())
        self.save_action.triggered.connect(lambda checked=False: self.save_file())
        self.exit_action.triggered.connect(self.win.close)

        self.widget = QWidget()
        self.main_layout = QHBoxLayout()

        # --- left panel: search box + roster list -----------------------------
        self.left_layout = QVBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search by value (eg. Edge) or hex (eg. 0A)")
        self.search_box.textChanged.connect(self.filter_superstar_list)
        self.left_layout.addWidget(self.search_box)
        self.list_superstar = QListWidget()
        self.list_superstar.setMinimumWidth(180)
        self.list_superstar.currentRowChanged.connect(
            self.superstar_selectionchange)
        self.left_layout.addWidget(self.list_superstar)

        # --- right panel: editor form -----------------------------------------
        self.right_layout = QVBoxLayout()
        self.stat_grid = QGridLayout()
        self.name_grid = QGridLayout()
        self.setting_grid = QGridLayout()
        self.setting_row = 0

        # buttons (were beside the old ID combo; now atop the right panel)
        self.button_layout = QHBoxLayout()
        self.button_set = QPushButton("Set stat")
        self.button_set.clicked.connect(self.set_stat)
        self.button_layout.addWidget(self.button_set)
        self.button_default = QPushButton("Default")
        self.button_default.clicked.connect(self.set_default)
        self.button_layout.addWidget(self.button_default)

        # --- attributes -------------------------------------------------------
        self.stat_spinboxes = {}
        for suffix, label, index, row, col in STAT_FIELDS:
            self.stat_grid.addWidget(QLabel(label), row, col)
            spin = QSpinBox()
            spin.setRange(0, 100)
            spin.setSingleStep(5)
            self.stat_grid.addWidget(spin, row, col + 1)
            setattr(self, "spinbox_%s" % suffix, spin)
            self.stat_spinboxes[index] = spin

        # --- names ------------------------------------------------------------
        self.name_grid.addWidget(QLabel("Name"), 0, 0)
        self.line_edit_name = QLineEdit()
        self.line_edit_name.setMaxLength(22)
        self.name_grid.addWidget(self.line_edit_name, 0, 1, 1, 2)
        self.name_grid.addWidget(QLabel("Nick Name"), 1, 0)
        self.line_edit_nickname = QLineEdit()
        self.line_edit_nickname.setMaxLength(20)
        self.name_grid.addWidget(self.line_edit_nickname, 1, 1, 1, 2)
        self.name_grid.addWidget(QLabel("HUD Name"), 2, 0)
        self.line_edit_hud_name = QLineEdit()
        self.line_edit_hud_name.setMaxLength(10)
        self.name_grid.addWidget(self.line_edit_hud_name, 2, 1, 1, 2)

        # --- settings (single column) -----------------------------------------
        self.combobox_show = self._combo(
            "Show", ["0x00 : RAW", "0x01 : Smackdown",
                     "0x02 : Legend", "0x03 : No Show"])
        self.combobox_tactic = self._combo(
            "Tactic", ["0x00 : Clean", "0x01 : Dirty"])
        self.combobox_gender = self._combo(
            "Gender", ["0x00 : Male", "0x01 : Female"])
        self.combobox_enable = self._combo(
            "Enable", ["0x00 : Disable", "0x03 : Enable"])
        self.combobox_country = self._combo(
            "Country", load_id_list("country.txt", 2))
        self.combobox_province = self._combo(
            "Province", load_id_list("province.txt", 2))
        self.combobox_weight = self._combo(
            "Weight", load_id_list("weight.txt", 2))
        self.combobox_nickname_placement = self._combo(
            "Nickname Placement",
            ["0x00 : None", "0x01 : Prefix", "0x02 : Suffix"])
        attire = load_id_list("attire.txt", 2)
        self.combobox_attire1 = self._combo("Attire 1 ID", attire)
        self.combobox_attire2 = self._combo("Attire 2 ID", attire)
        self.combobox_height = self._combo(
            "Height", load_id_list("height.txt", 4))

        # Let the input columns absorb spare width so labels stay compact-left.
        self.name_grid.setColumnStretch(1, 1)
        self.stat_grid.setColumnStretch(1, 1)
        self.stat_grid.setColumnStretch(3, 1)
        self.setting_grid.setColumnStretch(1, 1)

        self.right_layout.addLayout(self.button_layout)
        self.right_layout.addLayout(self.name_grid)
        self.right_layout.addLayout(self.stat_grid)
        self.right_layout.addLayout(self.setting_grid)
        self.right_layout.addStretch(1)

        # Left panel expands; the form is capped so the roster list stays roomy.
        self.left_widget = QWidget()
        self.left_widget.setLayout(self.left_layout)
        self.right_widget = QWidget()
        self.right_widget.setLayout(self.right_layout)
        self.right_widget.setMaximumWidth(300)
        self.main_layout.addWidget(self.left_widget, 1)
        self.main_layout.addWidget(self.right_widget, 0)

        # --- change log: full-width black panel below both columns ------------
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(120)
        self.log_view.setStyleSheet(
            "QPlainTextEdit { background-color: #000000; color: #FFFFFF; }")
        self.log_view.setFont(QFont("Consolas", 9))

        # Stack the two-column area above the full-width log. Stretch 0/1 sends
        # all vertical growth to the log, so resizing taller grows the log panel
        # (not the roster list, which keeps the columns' natural height).
        self.outer_layout = QVBoxLayout()
        self.outer_layout.addLayout(self.main_layout, 0)
        self.outer_layout.addWidget(self.log_view, 1)
        self.widget.setLayout(self.outer_layout)
        self.win.setCentralWidget(self.widget)
        self.set_enabled(False)
        # Form's natural height (+ a little space below the Height combo). This
        # is both the startup height and the vertical floor: making it the
        # minimum height stops the window shrinking into the combos, and any
        # extra height beyond it grows the log (see the stretch on outer_layout).
        fit_height = (self.widget.sizeHint().height()
                      + self.bar.sizeHint().height() + 10)
        self.win.setMinimumHeight(fit_height)
        # Actual startup window size (wins over setGeometry above). The first
        # number is the width to open at -- edit it to make the window wider or
        # narrower; it won't go below setMinimumSize or the content's own limits.
        self.win.resize(600, fit_height)
        self.win.show()

    def _combo(self, label, items):
        """Add a labelled combo box as its own full-width row in setting_grid."""
        self.setting_grid.addWidget(QLabel(label), self.setting_row, 0)
        combo = QComboBox()
        for item in items:
            combo.addItem(item)
        self.setting_grid.addWidget(combo, self.setting_row, 1)
        self.setting_row += 1
        return combo

    def run(self):
        return self.app.exec_()

    # -- helpers --------------------------------------------------------------

    def all_comboboxes(self):
        return [self.combobox_show, self.combobox_tactic, self.combobox_gender,
                self.combobox_enable, self.combobox_country,
                self.combobox_province, self.combobox_weight,
                self.combobox_nickname_placement, self.combobox_attire1,
                self.combobox_attire2, self.combobox_height]

    def set_enabled(self, enabled):
        """Grey out the editor until a file is loaded."""
        for widget in (list(self.stat_spinboxes.values())
                       + self.all_comboboxes()
                       + [self.line_edit_name, self.line_edit_nickname,
                          self.line_edit_hud_name, self.button_set,
                          self.button_default, self.list_superstar,
                          self.search_box]):
            widget.setEnabled(enabled)

    @staticmethod
    def combo_box_get_int(text):
        return int(str(text).split(" : ")[0], 16)

    def combo_box_get_value(self, combo_box):
        return self.combo_box_get_int(combo_box.currentText())

    def is_value_in_combo_box(self, combo_box, value):
        for x in range(combo_box.count()):
            if self.combo_box_get_int(combo_box.itemText(x)) == value:
                return True
        return False

    def combo_box_set_value(self, combo_box, value):
        for x in range(combo_box.count()):
            if self.combo_box_get_int(combo_box.itemText(x)) == value:
                combo_box.setCurrentIndex(x)
                return

    def message(self, title, text):
        msg = QMessageBox(self.win)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def log_message(self, text):
        """Append a plain status line to the black log panel."""
        self.log_view.appendPlainText(text)
        self.app.processEvents()   # paint it before any blocking work follows

    # -- file handling --------------------------------------------------------

    def open_file(self, filename=None):
        # `filename` is only passed on the reopen after Save; a bare menu click
        # opens the picker and gets its own "Opening.../Opened" log lines.
        interactive = filename is None
        if interactive:
            self.log_message("Opening file...")
            filename, _ = QFileDialog.getOpenFileName(
                self.win, "Open file", self.dirname, FILE_FILTER)
        if not filename:
            return
        self.filename = str(filename)
        self.dirname = os.path.dirname(self.filename)
        try:
            self.file = Stat_Editor(self.filename)
        except Exception as exc:
            self.file = None
            self.set_enabled(False)
            QMessageBox.critical(self.win, "Could not open file",
                                 "%s\n\n%s" % (self.filename, exc))
            return
        self.backup_stat = [list(stat) for stat in self.file.stat_list]
        self.update_combobox_height()
        self.update_superstar_list()
        self.set_enabled(True)
        if interactive:
            self.log_message("Opened %s" % self.filename)
            self.log_message("--------------------")

    def save_file(self):
        if self.file is None:
            return
        self.log_message("Saving file...")
        self.progress = QProgressBar()
        self.progress.setWindowTitle("Generating...")
        self.progress.setGeometry(200, 80, 250, 20)
        self.progress.show()
        try:
            for percent in self.file.set_stat_data():
                self.progress.setValue(int(percent))
                self.app.processEvents()
        except Exception as exc:
            self.progress.deleteLater()
            QMessageBox.critical(self.win, "Save failed", str(exc))
            return
        self.progress.deleteLater()
        self.progress = None

        self.file.close()
        self.file = None
        shutil.move(self.filename, "%s.bak" % self.filename)
        shutil.move("%s-NEW" % self.filename, self.filename)
        saved_as = self.filename
        self.open_file(saved_as)
        self.log_message(
            "Saved file at %s. Restore your backup anytime at %s.bak by "
            "omitting .bak on the filename" % (saved_as, saved_as))
        self.message("New file generated",
                     "File saved successfully. A backup file "
                     "'%s.bak' was also created." % saved_as)

    # -- view refresh ---------------------------------------------------------

    def update_superstar_list(self):
        self.list_superstar.blockSignals(True)
        self.list_superstar.clear()
        for x in range(len(self.file.stat_list)):
            self.list_superstar.addItem(
                "0x%.2X : %s" % (x, self.file.stat_list[x][15]))
        self.list_superstar.blockSignals(False)
        self.list_superstar.setCurrentRow(0)
        self.filter_superstar_list(self.search_box.text())

    def filter_superstar_list(self, text):
        """Hide roster rows whose label doesn't contain the query.

        The query is matched case-insensitively against the whole
        ``"0xNN : Name"`` label, so a name (``edge``) or a hex (``0a``)
        both filter the list; no match hides every row.
        """
        query = str(text).lower()
        for row in range(self.list_superstar.count()):
            item = self.list_superstar.item(row)
            item.setHidden(query not in item.text().lower())

    def update_combobox_height(self):
        self.combobox_height.clear()
        for item in load_id_list("height.txt", 4):
            self.combobox_height.addItem(item)
        for x in range(len(self.file.stat_list)):
            height = self.file.stat_list[x][13]
            if not self.is_value_in_combo_box(self.combobox_height, height):
                label = self.file.stat_list[x][19] or ("ID: 0x%.2X" % x)
                self.combobox_height.addItem("0x%.4X : %s" % (height, label))

    def GUI_set_stat(self, stat_list, index):
        stat = stat_list[index]
        for stat_index, spin in self.stat_spinboxes.items():
            spin.setValue(stat[stat_index] * 5)
        self.combo_box_set_value(self.combobox_show, stat[8])
        self.combo_box_set_value(self.combobox_tactic, stat[9])
        self.combo_box_set_value(self.combobox_height, stat[13])
        self.line_edit_name.setText(stat[15])
        self.line_edit_nickname.setText(stat[17])
        self.line_edit_hud_name.setText(stat[19])
        self.combo_box_set_value(self.combobox_gender, stat[21])
        self.combo_box_set_value(self.combobox_weight, stat[22])
        self.combo_box_set_value(self.combobox_enable, stat[24])
        self.combo_box_set_value(self.combobox_attire1, stat[25])
        self.combo_box_set_value(self.combobox_attire2, stat[26])
        self.combo_box_set_value(self.combobox_country, stat[28])
        self.combo_box_set_value(self.combobox_province, stat[29])
        self.combo_box_set_value(self.combobox_nickname_placement, stat[31])

    def current_index(self):
        """Roster index (parsed hex) of the selected list row, or None."""
        item = self.list_superstar.currentItem()
        if item is None:
            return None
        return self.combo_box_get_int(item.text())

    def superstar_selectionchange(self):
        index = self.current_index()
        if self.file is None or index is None:
            return
        self.GUI_set_stat(self.file.stat_list, index)

    # -- editing --------------------------------------------------------------

    def combo_text_for_value(self, combo_box, value):
        """Label a stored combo value the way the dropdown shows it."""
        for x in range(combo_box.count()):
            if self.combo_box_get_int(combo_box.itemText(x)) == value:
                return combo_box.itemText(x)
        return "0x%.2X" % value

    def combo_diff_fields(self):
        """(label, combo, stat index) for the plain combo boxes (Show is special)."""
        return [
            ("Tactic", self.combobox_tactic, 9),
            ("Gender", self.combobox_gender, 21),
            ("Enable", self.combobox_enable, 24),
            ("Country", self.combobox_country, 28),
            ("Province", self.combobox_province, 29),
            ("Weight", self.combobox_weight, 22),
            ("Nickname Placement", self.combobox_nickname_placement, 31),
            ("Attire 1 ID", self.combobox_attire1, 25),
            ("Attire 2 ID", self.combobox_attire2, 26),
            ("Height", self.combobox_height, 13),
        ]

    def set_stat(self):
        index = self.current_index()
        if self.file is None or index is None:
            return
        stat = self.file.stat_list[index]
        old = list(stat)          # snapshot before applying, for the diff log
        diffs = []

        for label, line_edit, i in (("Name", self.line_edit_name, 15),
                                    ("Nick Name", self.line_edit_nickname, 17),
                                    ("HUD Name", self.line_edit_hud_name, 19)):
            new = str(line_edit.text())
            if new != old[i]:
                diffs.append("%s: %s -> %s" % (label, old[i], new))
            stat[i] = new

        # attributes (shown/logged x5)
        for suffix, label, i, row, col in STAT_FIELDS:
            new = self.stat_spinboxes[i].value() // 5
            if new != old[i]:
                diffs.append("%s: %d -> %d" % (label.strip(), old[i] * 5, new * 5))
            stat[i] = new

        # Show combobox is separated as it writes both stat[8] and its mirror stat[11]
        new_show = self.combo_box_get_value(self.combobox_show)
        if new_show != old[8]:
            diffs.append("Show: %s -> %s" % (
                self.combo_text_for_value(self.combobox_show, old[8]),
                self.combobox_show.currentText()))
        stat[8] = stat[11] = new_show

        # Rest of the comboboxes
        for label, combo, i in self.combo_diff_fields():
            new = self.combo_box_get_value(combo)
            if new != old[i]:
                diffs.append("%s: %s -> %s" % (
                    label, self.combo_text_for_value(combo, old[i]),
                    combo.currentText()))
            stat[i] = new

        if diffs:
            self.log_change(index, old[15], diffs)
        self.message("Stat Set", "Stat set for ID : 0x%.2X" % index)

    def log_change(self, index, name, diffs):
        """Append a diff block for one 'Set stat' to the black log panel."""
        block = "Changed: 0x%.2X : %s\n\n%s\n--------------------" % (
            index, name, "\n".join(diffs))
        self.log_view.appendPlainText(block)

    def set_default(self):
        index = self.current_index()
        if self.file is None or index is None:
            return
        self.GUI_set_stat(self.backup_stat, index)
        self.message("Back to default",
                     "Stat set to default for ID : 0x%.2X. "
                     "Click 'Set Stat' to confirm." % index)


def main():
    app = Application()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
