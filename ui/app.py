"""Tkinter front end. Talks only to imgcrypt.service.

Layout is a four-step flow: 1 Choose action, 2 Select file, 3 Choose output
location, 4 Encrypt/Decrypt. A status line always says what happens next.
"""

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from imgcrypt import service
from imgcrypt.constants import ENCRYPTED_EXTENSION
from imgcrypt.errors import ImageCryptError

ENCRYPT, DECRYPT = "encrypt", "decrypt"

# status kind -> foreground colour
COLORS = {"info": "#444444", "ready": "#0b6b2b", "busy": "#0b4f9c",
          "ok": "#0b6b2b", "error": "#b00020"}

IDLE, BUSY, DONE, FAILED = "idle", "busy", "done", "failed"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Image Encryption Tool")
        self.resizable(False, False)

        self.action = tk.StringVar(value=ENCRYPT)
        self.src = tk.StringVar()
        self.dst = tk.StringVar()
        self.status = tk.StringVar()
        self.events = queue.Queue()
        self.phase = IDLE
        self.message = ""  # status text kept for the DONE / FAILED phases
        self._dst_auto = True  # output name was suggested, not typed by the user

        self._build()
        self.action.trace_add("write", lambda *_: self._on_action_change())
        self.src.trace_add("write", lambda *_: self._on_src_change())
        self.dst.trace_add("write", lambda *_: self._on_input_change())
        self._refresh()

    # -- layout -------------------------------------------------------------
    def _build(self):
        style = ttk.Style(self)
        style.configure("Step.TLabel", font=("Segoe UI", 11, "bold"))
        style.configure("Hint.TLabel", foreground="#666666")
        style.configure("Primary.TButton", font=("Segoe UI", 12, "bold"),
                        padding=(16, 10))

        frm = ttk.Frame(self, padding=20)
        frm.grid()
        frm.columnconfigure(0, weight=1)

        # Step 1: action
        self._step_label(frm, 0, "Step 1 · Choose action")
        row = ttk.Frame(frm)
        row.grid(row=1, column=0, sticky="w", pady=(4, 16))
        self.radios = []
        for text, value in (("Encrypt an image", ENCRYPT),
                            ("Decrypt a file", DECRYPT)):
            rb = ttk.Radiobutton(row, text=text, value=value, variable=self.action)
            rb.pack(side="left", padx=(0, 24))
            self.radios.append(rb)

        # Step 2: input file, one large click area
        self._step_label(frm, 2, "Step 2 · Select file")
        self.drop = tk.Frame(frm, bg="#f4f6fa", highlightthickness=2,
                             highlightbackground="#9aa7bd", cursor="hand2")
        self.drop.grid(row=3, column=0, sticky="we", pady=(4, 16), ipady=14)
        self.drop_title = tk.Label(self.drop, bg="#f4f6fa", font=("Segoe UI", 11),
                                   wraplength=440, justify="center")
        self.drop_title.pack(pady=(6, 8), padx=12)
        self.src_btn = ttk.Button(self.drop, text="Browse files…",
                                  command=self._browse_src)
        self.src_btn.pack(pady=(0, 6))
        for w in (self.drop, self.drop_title):
            w.bind("<Button-1>", lambda e: self._browse_src())

        # Step 3: output
        self._step_label(frm, 4, "Step 3 · Choose output location")
        out = ttk.Frame(frm)
        out.grid(row=5, column=0, sticky="we", pady=(4, 0))
        out.columnconfigure(0, weight=1)
        self.dst_entry = ttk.Entry(out, textvariable=self.dst, width=52)
        self.dst_entry.grid(row=0, column=0, sticky="we")
        self.dst_entry.bind("<Key>", lambda e: setattr(self, "_dst_auto", False))
        self.dst_btn = ttk.Button(out, text="Change…", command=self._browse_dst)
        self.dst_btn.grid(row=0, column=1, padx=(8, 0))
        self.dst_hint = ttk.Label(frm, style="Hint.TLabel",
                                  text="Suggested automatically; edit it if you like.")
        self.dst_hint.grid(row=6, column=0, sticky="w", pady=(2, 16))

        # Step 4: run
        self.step4 = self._step_label(frm, 7, "Step 4 · Encrypt")
        self.start_btn = ttk.Button(frm, style="Primary.TButton", command=self._start)
        self.start_btn.grid(row=8, column=0, sticky="we", pady=(4, 10))

        self.bar = ttk.Progressbar(frm, maximum=100, mode="determinate")
        self.bar.grid(row=9, column=0, sticky="we", pady=(0, 6))
        self.status_lbl = tk.Label(frm, textvariable=self.status, anchor="w",
                                   justify="left", wraplength=480,
                                   font=("Segoe UI", 10, "bold"))
        self.status_lbl.grid(row=10, column=0, sticky="we")

    def _step_label(self, parent, row, text):
        lbl = ttk.Label(parent, text=text, style="Step.TLabel")
        lbl.grid(row=row, column=0, sticky="w")
        return lbl

    # -- state --------------------------------------------------------------
    def _verb(self):
        return "Encrypt" if self.action.get() == ENCRYPT else "Decrypt"

    def _problem(self):
        """Why the primary button is disabled, or None when inputs are valid."""
        src, dst = self.src.get().strip(), self.dst.get().strip()
        noun = "an image to encrypt" if self.action.get() == ENCRYPT else "a file to decrypt"
        if not src:
            return f"Next: click “Browse files…” and choose {noun}."
        if not Path(src).is_file():
            return "That input file no longer exists. Choose another file."
        if not dst:
            return "Next: choose where to save the result."
        if not Path(dst).resolve().parent.is_dir():
            return "The output folder does not exist. Click “Change…” to pick one."
        if Path(src).resolve() == Path(dst).resolve():
            return "Output must be a different file than the input. Change the output name."
        return None

    def _refresh(self):
        verb = self._verb()
        busy = self.phase == BUSY
        problem = self._problem()

        self.step4.config(text=f"Step 4 · {verb}")
        self.start_btn.config(text=f"{verb} file")
        ok = problem is None and not busy
        self.start_btn.state(["!disabled"] if ok else ["disabled"])

        for w in (self.dst_entry, self.dst_btn, self.src_btn, *self.radios):
            w.state(["disabled"] if busy else ["!disabled"])
        if not busy and not self.src.get().strip():
            self.dst_entry.state(["disabled"])
            self.dst_btn.state(["disabled"])

        name = Path(self.src.get()).name if self.src.get().strip() else ""
        self.drop_title.config(
            text=f"Selected: {name}" if name else
            ("No file selected\nClick here or use Browse files…"),
            fg="#111111" if name else "#666666",
            font=("Segoe UI", 11, "bold" if name else "normal"))
        self.src_btn.config(text="Choose a different file…" if name else "Browse files…")

        if self.phase in (DONE, FAILED):
            kind = "ok" if self.phase == DONE else "error"
            self._set_status(self.message, kind)
        elif busy:
            pass  # progress events own the status text
        elif problem:
            self._set_status(problem, "info")
        else:
            self._set_status(f"Ready to {verb.lower()}. Click “{verb} file”.", "ready")

    def _set_status(self, text, kind):
        self.status.set(text)
        self.status_lbl.config(fg=COLORS[kind])

    def _reset_progress(self):
        self.bar["value"] = 0

    def _on_input_change(self):
        if self.phase != BUSY:
            if self.phase != IDLE:
                self.phase = IDLE
                self._reset_progress()
            self._refresh()

    def _on_src_change(self):
        self._suggest_output()
        self._on_input_change()

    def _on_action_change(self):
        self._dst_auto = True
        self.src.set("")
        self.dst.set("")
        self.phase = IDLE
        self._reset_progress()
        self._refresh()

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
        if self.phase == BUSY:
            return
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
        overwrite = False
        if Path(dst).exists():
            if not messagebox.askyesno(
                    "Replace existing file?",
                    f"'{Path(dst).name}' already exists. Replace it?"):
                self._set_status("Nothing was saved. Change the output name, "
                                 f"or click “{self._verb()} file” again to replace it.",
                                 "info")
                return
            overwrite = True

        action = self.action.get()
        self._reset_progress()
        self.phase = BUSY
        self._set_status(f"{self._verb()}ing… 0%", "busy")
        self._refresh()

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
        gerund = "Encrypting" if self.action.get() == ENCRYPT else "Decrypting"
        noun = "Encryption" if self.action.get() == ENCRYPT else "Decryption"
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "progress":
                    pct = int(value * 100)
                    self.bar["value"] = pct
                    self._set_status(f"{gerund}… {pct}%", "busy")
                elif kind == "done":
                    self.bar["value"] = 100
                    self.phase = DONE
                    self.message = (f"{noun} complete. Saved to {self.dst.get()}\n"
                                    "To process another file, click “Browse files…”.")
                    finished = True
                elif kind == "error":
                    self.bar["value"] = 0
                    self.phase = FAILED
                    self.message = (f"{noun} failed: {value}\n"
                                    "Check the file, or choose a different one, then try again.")
                    finished = True
        except queue.Empty:
            pass
        if finished:
            self._refresh()
        else:
            self.after(50, self._poll)


def main():
    App().mainloop()
