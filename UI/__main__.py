# A Graphical User Interface for JSBSim
#
# Copyright (c) 2023-2024 Bertrand Coconnier
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, see <http://www.gnu.org/licenses/>

import argparse
import os
import sys
from typing import List, Optional

from PySide6.QtCore import QFile, Qt
from PySide6.QtGui import QAction, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtXml import QDomDocument

from .controller import Controller
from .hierarchical_tree import HierarchicalTree, PropertyExplorer


class JSBSimGUI(QMainWindow):
    def __init__(self, root_dir: Optional[str] = None):
        super().__init__()

        self.setWindowTitle(f"JSBSim {Controller.get_version()}")
        self._file_menu = self.menuBar().addMenu("&File")
        self._file_menu.addAction(
            QAction(
                "&Open...",
                self,
                shortcut=QKeySequence(Qt.CTRL | Qt.Key_O),
                triggered=self.open_file,
            )
        )
        self._file_menu.addAction(
            QAction(
                "E&xit",
                self,
                shortcut=QKeySequence(Qt.CTRL | Qt.Key_Q),
                triggered=self.close,
            )
        )

        self._help_menu = self.menuBar().addMenu("&Help")
        self._help_menu.addAction(QAction("&About", self, triggered=self.about))

        if root_dir:
            self.root_dir = root_dir
            if not os.path.exists(self.root_dir):
                QMessageBox.critical(
                    self, "Error", f'The directory "{self.root_dir}" does not exist'
                )
                return
        else:
            try:
                self.root_dir = Controller.get_default_root_dir()
            except IOError as e:
                QMessageBox.critical(self, "Error", e)
                return

        self._controller = Controller(self.root_dir, 0)

        label = QLabel()
        label.setPixmap(QPixmap("logo/wizard_installer/logo_JSBSIM_globe_410x429.bmp"))
        self.setCentralWidget(label)

        self.statusBar().showMessage(f"JSBSim root directory: {self.root_dir}")

    def open_file(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open a script / aircraft", self.root_dir, "script files (*.xml)"
        )

        if not file_name:
            return

        in_file = QFile(file_name)
        if not in_file.open(QFile.ReadOnly | QFile.Text):
            reason = in_file.errorString()
            QMessageBox.warning(
                self,
                "Script / aircraft file",
                f"Cannot read file {file_name}:\n{reason}.",
            )
            return

        self.statusBar().showMessage(f"Opening {file_name}")
        xml = QDomDocument()

        ok, error, error_line, error_column = xml.setContent(in_file, True)
        if not ok:
            QMessageBox.warning(
                self,
                "Script / aircraft file",
                f"Parse error at line {error_line}, "
                f"column {error_column}:\n{error}",
            )
            return

        root = xml.documentElement()
        if root.tagName() == "runscript":
            use = root.firstChildElement("use")
            aircraft_name = use.attribute("aircraft")
            self.statusBar().showMessage(f"Opening aircraft {aircraft_name}")
            self._controller.load_script(file_name)
        elif root.tagName() == "fdm_config":
            aircraft_name = os.path.splitext(os.path.basename(file_name))[0]
            self.statusBar().showMessage(f"Opening aircraft {aircraft_name}")
            self._controller.load_aircraft(file_name)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.addWidget(QLabel("Project files"))
        project_files = HierarchicalTree(
            self._controller.get_input_files(), ["Files"], True
        )
        project_files.setHeaderHidden(True)
        layout.addWidget(project_files)
        property_explorer = PropertyExplorer(
            self._controller.get_property_list(),
            self._controller.get_property_root().get_fully_qualified_name(),
        )
        layout.addLayout(property_explorer)

    def about(self) -> None:
        QMessageBox.about(
            self,
            "About JSBSim GUI",
            "JSBSim GUI - A Graphical User Interface for JSBSim\n"
            f"Version: {Controller.get_version()}\n"
            "\n"
            "This program is free software; you can redistribute it and/or modify it under"
            "the terms of the GNU General Public License as published by the Free Software"
            "Foundation; either version 3 of the License, or (at your option) any later"
            "version.\n\n"
            "This program is distributed in the hope that it will be useful, but WITHOUT"
            "ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS"
            "FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more"
            "details.\n\n"
            "You should have received a copy of the GNU General Public License along with"
            "this program; if not, see <http://www.gnu.org/licenses/>",
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        "--version", action="version", version=f"JSBSim UI {Controller.get_version()}"
    )
    parser.add_argument(
        "--root",
        metavar="<path>",
        help="specifies the JSBSim root directory (where aircraft/, engine/, etc. reside)",
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    main = JSBSimGUI(args.root)
    main.show()
    sys.exit(app.exec())
