# A Graphical User Interface for JSBSim
#
# Copyright (c) 2023 Bertrand Coconnier
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
import tkinter as tk
from tkinter import filedialog as fd
from tkinter.messagebox import showerror, showinfo

import jsbsim
from PIL import Image, ImageTk


class Controller:
    @staticmethod
    def get_version():
        return jsbsim.__version__
    @staticmethod
    def get_default_root_dir():
        return jsbsim.get_default_root_dir()


class MenuBar(tk.Menu):
    def __init__(self, root, root_dir):
        super().__init__(root)
        self.root_dir = root_dir

        file_menu = tk.Menu(self, tearoff=False)
        file_menu.add_command(label="Open...", command=self.select_script_file)
        file_menu.add_command(label="Exit", command=root.destroy)
        self.add_cascade(label="File", menu=file_menu)

    def select_script_file(self):
        filename = fd.askopenfilename(
            title="Open a script",
            initialdir=self.root_dir,
            filetypes=(("script files", "*.xml"),),
        )
        if filename:
            showinfo(
                title="Selected script",
                message=os.path.relpath(filename, self.root_dir),
            )


class App(tk.Tk):
    def __init__(self, root_dir=None):
        super().__init__()
        self.title(f"JSBSim {Controller.get_version()}")

        menubar = MenuBar(self, root_dir)
        self.config(menu=menubar)

        with Image.open("logo_JSBSIM_globe.png") as image:
            logo_resized = image.resize((image.width * 400 // image.height, 400))
            logo_image = ImageTk.PhotoImage(logo_resized)
            logo = tk.Label(self, image=logo_image, width=600, background="white")
            logo.image = logo_image
            logo.pack()

        if root_dir:
            self.root_dir = root_dir
        else:
            try:
                self.root_dir = Controller.get_default_root_dir()
            except IOError as e:
                showerror("Error", message=e)
                self.destroy()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--version", action="version",
                        version=f"JSBSim UI {Controller.get_version()}")
    parser.add_argument("--root", metavar="<path>",
                        help="specifies the JSBSim root directory (where aircraft/, engine/, etc. reside)")
    args = parser.parse_args()

    app = App(args.root)
    app.mainloop()
