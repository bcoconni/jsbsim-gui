# A Graphical User Interface for JSBSim
#
# Copyright (c) 2026 Bertrand Coconnier
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

import enum
import threading
import tkinter as tk
from tkinter import DISABLED, EW, NORMAL, NSEW, ttk

import ollama

from .hierarchical_tree import TextBox
from .textview import TextView


class Format(str, enum.Enum):
    BOLD = "BOLD"
    H1 = "H1"
    H2 = "H2"
    H3 = "H3"
    REGULAR = ""


class ChatConsole(tk.Frame):
    def __init__(self, master: tk.Widget, **kw):
        super().__init__(master)
        self._chat_area = TextView(
            self, wrap=tk.WORD, state=DISABLED, font=("Helvetica", 10), **kw
        )
        self._chat_area.tag_configure("user_prompt", background="#dddddd", spacing2=6)
        self._chat_area.tag_configure(
            "H1", font=("Helvetica", 16, "bold"), spacing3=6, foreground="#ff0000"
        )
        self._chat_area.tag_configure(
            "H2", font=("Helvetica", 14, "bold"), spacing3=6, foreground="#00ff00"
        )
        self._chat_area.tag_configure(
            "H3", font=("Helvetica", 12, "bold"), spacing3=6, foreground="#0000ff"
        )
        self._chat_area.tag_configure("BOLD", font=("Helvetica", 10, "bold"))
        self._chat_area.grid(column=0, row=0, columnspan=2, sticky=NSEW)
        self._prompt_entry = TextBox(self)
        self._prompt_entry.grid(column=0, row=1, sticky=EW)
        self._prompt_entry.bind("<Return>", lambda _event: self._start_chat_thread())
        self._send_button = ttk.Button(
            self, text="Send", command=self._start_chat_thread
        )
        self._send_button.grid(column=1, row=1, sticky=tk.E)
        self.grid_columnconfigure(0, weight=1)

        self._conversation_history = [
            {
                "role": "system",
                "content": "You are an expert in flight dynamics modelling using JSBSim",
            }
        ]

    def _start_chat_thread(self) -> None:
        prompt = self._prompt_entry.get().strip()
        if not prompt:
            return

        self._chat_area.append_content(f"{prompt}\n", "user_prompt")
        self._chat_area.append_content("\n")
        self._prompt_entry.delete(0, tk.END)
        self._conversation_history.append({"role": "user", "content": prompt})

        self._prompt_entry.configure(state=DISABLED)
        self._send_button.configure(state=DISABLED)

        threading.Thread(target=self._fetch_ollama_response, daemon=True).start()

    def _display_response(self, response: str) -> None:
        self._chat_area.append_content(f"{response}\n\n")
        self._prompt_entry.configure(state=NORMAL)
        self._send_button.configure(state=NORMAL)
        self._prompt_entry.focus()

    def _fetch_ollama_response(self) -> None:
        try:
            stream = ollama.chat(
                model="gemma4:26b-mlx", messages=self._conversation_history, stream=True
            )
            ai_response = ""
            format = Format.REGULAR

            for response in stream:
                chunk: str = response["message"]["content"]
                ai_response += chunk

                # Display the MarkDown format
                while chunk:
                    if chunk.startswith("###"):
                        format = Format.H3
                        chunk = chunk[3:]
                        continue

                    if chunk.startswith("##"):
                        format = Format.H2
                        chunk = chunk[2:]
                        continue

                    if chunk.startswith("#"):
                        format = Format.H1
                        chunk = chunk[1:]
                        continue

                    bold_mark = chunk.find("**")
                    if bold_mark != -1:
                        self.after(
                            0, self._chat_area.append_content, chunk[:bold_mark], format
                        )
                        format = (
                            Format.BOLD if format == Format.REGULAR else Format.REGULAR
                        )
                        chunk = chunk[bold_mark + 2 :]
                        continue

                    cr_mark = chunk.find("\n")
                    if cr_mark != -1:
                        self.after(
                            0,
                            self._chat_area.append_content,
                            chunk[: cr_mark + 1],
                            format,
                        )
                        format = Format.REGULAR
                        chunk = chunk[cr_mark + 1 :]

                    self.after(0, self._chat_area.append_content, chunk, format)
                    break

            self._conversation_history.append(
                {"role": "assistant", "content": ai_response}
            )
            self.after(0, self._display_response, "")
        except Exception as e:
            error_msg = f"Ollama error: {str(e)}"
            self.after(0, self._display_response, error_msg)
