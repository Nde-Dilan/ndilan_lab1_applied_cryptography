"""Tkinter front end. Talks only to imgcrypt.service."""

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from imgcrypt import service
from imgcrypt.constants import ENCRYPTED_EXTENSION
from imgcrypt.errors import ImageCryptError

ENCRYPT, DECRYPT = "encrypt", "decrypt"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Image Encryption Tool")
        self.resizable(False, False)

        self.action = tk.StringVar(value=ENCRYPT)
        self.src = tk.StringVar()
        self.dst = tk.StringVar()
        self.status = tk.StringVar(value="Choose an action and an input file.")
        self.percent = tk.StringVar(value="0%")
        self.events = queue.Queue()
        self.running = False
        self._dst_auto = True  # output name was suggested, not typed by the user

        self._build()
        for var in (self.action, self.src, self.dst):
            var.trace_add("write", lambda *_: self._refresh_start())
        self.action.trace_add("write", lambda *_: self._on_action_change())
        self.src.trace_add("write", lambda *_: self._suggest_output())
        self._refresh_start()

    def _build(self):
        pad = {"padx": 8, "pady": 4}
        frm = ttk.Frame(self, padding=10)
        frm.grid()

        self.radios = []
        row = ttk.Frame(frm)
        row.grid(row=0, column=0, columnspan=3, sticky="w", **pad)
        for text, value in (("Encrypt", ENCRYPT), ("Decrypt", DECRYPT)):
            rb = ttk.Radiobutton(row, text=text, value=value, variable=self.action)
            rb.pack(side="left", padx=(0, 16))
            self.radios.append(rb)

        ttk.Label(frm, text="Input file:").grid(row=1, column=0, sticky="e", **pad)
        self.src_entry = ttk.Entry(frm, textvariable=self.src, width=50)
        self.src_entry.grid(row=1, column=1, **pad)
        self.src_btn = ttk.Button(frm, text="Browse...", command=self._browse_src)
        self.src_btn.grid(row=1, column=2, **pad)

        ttk.Label(frm, text="Output file:").grid(row=2, column=0, sticky="e", **pad)
        self.dst_entry = ttk.Entry(frm, textvariable=self.dst, width=50)
        self.dst_entry.grid(row=2, column=1, **pad)
        self.dst_entry.bind("<Key>", lambda e: setattr(self, "_dst_auto", False))
        self.dst_btn = ttk.Button(frm, text="Browse...", command=self._browse_dst)
        self.dst_btn.grid(row=2, column=2, **pad)

        self.start_btn = ttk.Button(frm, text="Start", command=self._start)
        self.start_btn.grid(row=3, column=0, columnspan=3, **pad)

        self.bar = ttk.Progressbar(frm, length=400, maximum=100, mode="determinate")
        self.bar.grid(row=4, column=0, columnspan=2, sticky="we", **pad)
        ttk.Label(frm, textvariable=self.percent, width=5).grid(row=4, column=2, **pad)
        ttk.Label(frm, textvariable=self.status, wraplength=480).grid(
            row=5, column=0, columnspan=3, sticky="w", **pad)

    # -- widgets state ------------------------------------------------------
    def _refresh_start(self):
        ok = (not self.running and bool(self.src.get().strip())
              and bool(self.dst.get().strip()))
        self.start_btn.state(["!disabled"] if ok else ["disabled"])

    def _set_busy(self, busy):
        self.running = busy
        for w in (self.src_entry, self.dst_entry, self.src_btn, self.dst_btn, *self.radios):
            w.state(["disabled"] if busy else ["!disabled"])
        self._refresh_start()

    def _on_action_change(self):
        self.src.set("")
        self.dst.set("")
        self._dst_auto = True
        self.bar["value"] = 0
        self.percent.set("0%")
        self.status.set("Choose an input file.")

    def _suggest_output(self):
        src = self.src.get().strip()
        if not src or not self._dst_auto:
            return
        if self.action.get() == ENCRYPT:
            self.dst.set(service.suggest_encrypted_name(src))
        else:
            image_type = service.peek_image_type(src)
            self.dst.set(service.suggest_decrypted_name(src, image_type))
        self._dst_auto = True

    # -- file dialogs -------------------------------------------------------
    def _browse_src(self):
        if self.action.get() == ENCRYPT:
            types = [("Images", "*.png *.jpg *.jpeg"), ("All files", "*.*")]
        else:
            types = [("Encrypted files", f"*{ENCRYPTED_EXTENSION}"), ("All files", "*.*")]
        path = filedialog.askopenfilename(title="Select input file", filetypes=types)
        if path:
            self._dst_auto = True
            self.src.set(path)

    def _browse_dst(self):
        if self.action.get() == ENCRYPT:
            kwargs = dict(defaultextension=ENCRYPTED_EXTENSION,
                          filetypes=[("Encrypted files", f"*{ENCRYPTED_EXTENSION}")])
        else:
            kwargs = dict(defaultextension=".png",
                          filetypes=[("Images", "*.png *.jpg *.jpeg")])
        initial = Path(self.dst.get()).name if self.dst.get() else ""
        path = filedialog.asksaveasfilename(
            title="Select output file", initialfile=initial,
            confirmoverwrite=False, **kwargs)
        if path:
            self._dst_auto = False
            self.dst.set(path)

    # -- running ------------------------------------------------------------
    def _start(self):
        src, dst = self.src.get().strip(), self.dst.get().strip()
        if Path(src).resolve() == Path(dst).resolve():
            messagebox.showerror("Error", "Input and output must be different files.")
            return
        overwrite = False
        if Path(dst).exists():
            if not messagebox.askyesno("Overwrite?", f"'{Path(dst).name}' already exists. Overwrite it?"):
                return
            overwrite = True

        action = self.action.get()
        self.bar["value"] = 0
        self.percent.set("0%")
        self.status.set("Encrypting..." if action == ENCRYPT else "Decrypting...")
        self._set_busy(True)

        worker = threading.Thread(
            target=self._work, args=(action, src, dst, overwrite), daemon=True)
        worker.start()
        self.after(50, self._poll)

    def _work(self, action, src, dst, overwrite):
        func = service.encrypt_file if action == ENCRYPT else service.decrypt_file
        try:
            func(src, dst, progress=lambda f: self.events.put(("progress", f)),
                 overwrite=overwrite)
            self.events.put(("done", None))
        except ImageCryptError as e:
            self.events.put(("error", str(e)))
        except Exception as e:  # unexpected: still tell the user
            self.events.put(("error", f"Unexpected error: {e}"))

    def _poll(self):
        finished = False
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "progress":
                    self.bar["value"] = value * 100
                    self.percent.set(f"{int(value * 100)}%")
                elif kind == "done":
                    self.bar["value"] = 100
                    self.percent.set("100%")
                    verb = "Encryption" if self.action.get() == ENCRYPT else "Decryption"
                    self.status.set(f"{verb} complete: {self.dst.get()}")
                    finished = True
                elif kind == "error":
                    self.bar["value"] = 0
                    self.percent.set("0%")
                    self.status.set(f"Error: {value}")
                    messagebox.showerror("Error", value)
                    finished = True
        except queue.Empty:
            pass
        if finished:
            self._set_busy(False)
        else:
            self.after(50, self._poll)


def main():
    App().mainloop()
