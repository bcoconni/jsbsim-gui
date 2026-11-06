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
from pathlib import Path

from . import __version__
from .app import App
from .controller import Controller
from .menu_bar import RecentFiles, open_file


def run():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        "--version",
        action="version",
        version=f"GUI {__version__} / JSBSim {Controller.get_version()}",
    )
    parser.add_argument(
        "--root",
        metavar="<path>",
        type=str,
        help="specifies the JSBSim root directory (where aircraft/, engine/, etc. reside)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--model", metavar="<aircraft_name>", type=str, help="load an aircraft model"
    )
    group.add_argument(
        "--script", metavar="<script_name>", type=str, help="load a script"
    )
    group.add_argument(
        "--resume",
        type=int,
        nargs="?",
        const=0,
        default=None,
        metavar="<index>",
        help="XXX resume from recent files by index (0 is the most recent)",
    )
    group.add_argument(
        "--list-recent-files",
        action="store_true",
        help="Display the list of recent files and exit",
    )
    args = parser.parse_args()

    if args.list_recent_files:
        file_list = RecentFiles().pretty_list()
        for i, file in enumerate(file_list):
            print(f"{i:2}: {file}")
        return
    elif args.resume is not None:
        recent_file = RecentFiles()[args.resume]
        app = App(recent_file[1])
        open_file(app, recent_file[0])
    else:
        app = App(Path(args.root) if args.root is not None else None)

        if args.model:
            app.load_model_from_cmdline(args.model)
        elif args.script:
            app.load_script_from_cmdline(args.script)
        else:
            app.display_logo()

    app.mainloop()


if __name__ == "__main__":
    run()
