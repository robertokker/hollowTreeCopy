import os
import shutil
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import time
import json
import re

import webbrowser

class ToolTip(object):
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.waittime = 500     # miliseconds
        self.wraplength = 400   # pixels
        self.id = None
        self.tw = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        
        # Creates a toplevel window
        self.tw = tk.Toplevel(self.widget)
        
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        
        label = tk.Label(self.tw, text=self.text, justify='left',
                       background="#ffffe0", relief='solid', borderwidth=1,
                       font=("Consolas", 8))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()

class RuleListWidget(ttk.LabelFrame):
    def __init__(self, parent, title, rules=None):
        super().__init__(parent, text=title, padding=10)
        self.rules = rules if rules else []
        
        # --- Help Header ---
        header_frame = ttk.Frame(self)
        header_frame.pack(fill='x', pady=(0, 5))
        
        lbl_help = tk.Label(header_frame, text="Help: regexr.com", fg="#4a90e2", bg="#2b2b2b", cursor="hand2")
        lbl_help.pack(side='right')
        lbl_help.bind("<Button-1>", lambda e: webbrowser.open("https://regexr.com"))
        
        # Listbox with Scrollbar
        list_frame = ttk.Frame(self)
        list_frame.pack(fill='both', expand=True, pady=5)
        
        self.listbox = tk.Listbox(list_frame, height=5, bg="#1e1e1e", fg="white", selectbackground="#4a90e2")
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        
        self.listbox.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Entry + Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill='x', pady=5)
        
        self.entry = ttk.Entry(btn_frame)
        self.entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        self.entry.bind('<Return>', lambda e: self.add_rule())
        
        # Tooltip
        cheat_sheet = (
            "Character classes\n"
            ".   any char except newline\n"
            "\\w\\d\\s  word, digit, whitespace\n"
            "\\W\\D\\S  not word, digit, whitespace\n"
            "[abc]   any of a, b, or c\n"
            "[^abc]  not a, b, or c\n"
            "[a-g]   char between a & g\n\n"
            "Anchors\n"
            "^abc$   start / end of the string\n"
            "\\b\\B    word, not-word boundary\n\n"
            "Escaped characters\n"
            "\\.\\*\\\\    escaped special chars\n\n"
            "Groups & Lookaround\n"
            "(abc)   capture group\n"
            "(?:abc) non-capturing group\n"
            "(?=abc) positive lookahead\n"
            "(?!abc) negative lookahead\n\n"
            "Quantifiers\n"
            "a* a+ a?    0+, 1+, 0 or 1\n"
            "a{5} a{2,}  exactly 5, 2+\n"
            "ab|cd       match ab or cd"
        )
        ToolTip(self.entry, cheat_sheet)
        
        ttk.Button(btn_frame, text="+", width=3, command=self.add_rule).pack(side='left')
        ttk.Button(btn_frame, text="-", width=3, command=self.remove_rule).pack(side='left', padx=(5, 0))

        self.refresh_list()

    def add_rule(self):
        rule = self.entry.get().strip()
        if rule and rule not in self.rules:
            self.rules.append(rule)
            self.refresh_list()
            self.entry.delete(0, 'end')

    def remove_rule(self):
        sel = self.listbox.curselection()
        if sel:
            idx = sel[0]
            self.rules.pop(idx)
            self.refresh_list()

    def refresh_list(self):
        self.listbox.delete(0, 'end')
        for r in self.rules:
            self.listbox.insert('end', r)

    def get_rules(self):
        return self.rules

    def set_rules(self, rules):
        self.rules = rules
        self.refresh_list()


class HollowTreeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hollow Tree Generator v3.0 (Regex)")
        self.root.geometry("700x700")
        
        # State Variables
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready to Scan")
        self.progress_var = tk.DoubleVar(value=0)
        self.stop_requested = False
        self.scan_stats = None
        self.settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hollow_tree_settings.json")
        
        # Settings Defaults (Regex)
        self.default_full_rules = [r".*\.json$", r".*\.ocio$", r"^metadata$"]
        self.default_exclude_rules = [r".*\.tmp$", r".*\.bak$"]
        
        # Apply Theme
        self.apply_dark_theme()
        
        # Build UI
        self.setup_ui()
        
        # Load Settings (After UI to populate widgets)
        self.load_settings()
        
        # Bind Close Event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.save_settings()
        self.root.destroy()

    def load_settings(self):
        if not os.path.exists(self.settings_file):
            return
            
        try:
            with open(self.settings_file, 'r') as f:
                data = json.load(f)
            
            # Use defaults if keys missing, handle migration if needed
            full = data.get('full_copy_rules', [])
            if not full and 'full_exts' in data: # Migration attempt (lazy)
                full = self.default_full_rules 
                
            excl = data.get('exclude_rules', [])
            
            if not full: full = self.default_full_rules
            if not excl: excl = self.default_exclude_rules

            self.rule_full.set_rules(full)
            self.rule_exclude.set_rules(excl)
            
            self.log(f"Settings loaded from {self.settings_file}")
            
        except Exception as e:
            self.log(f"Error loading settings: {e}")

    def save_settings(self):
        data = {
            'full_copy_rules': self.rule_full.get_rules(),
            'exclude_rules': self.rule_exclude.get_rules()
        }
        
        try:
            print(f"Saving settings to: {self.settings_file}")
            with open(self.settings_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")
            messagebox.showerror("Settings Error", f"Could not save settings:\n{e}")

    def apply_dark_theme(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        bg = "#2b2b2b"
        fg = "#ffffff"
        darker_bg = "#1e1e1e"
        accent = "#4a90e2"
        
        self.root.configure(bg=bg)
        style.configure(".", background=bg, foreground=fg, fieldbackground=darker_bg, bordercolor=bg)
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("TLabelframe", background=bg, foreground=fg, bordercolor="#555555")
        style.configure("TLabelframe.Label", background=bg, foreground=accent)
        style.configure("TEntry", fieldbackground=darker_bg, foreground=fg, insertcolor=fg)
        style.configure("TButton", background="#3c3f41", foreground=fg, borderwidth=1)
        style.map("TButton", background=[('active', accent)])
        style.configure("Horizontal.TProgressbar", background=accent, troughcolor=darker_bg)
        style.configure("TNotebook", background=bg)
        style.configure("TNotebook.Tab", background="#3c3f41", foreground=fg, padding=[10, 2])
        style.map("TNotebook.Tab", background=[("selected", accent)])
        
    def setup_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)
        
        # --- Main Tab ---
        self.main_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.main_frame, text='Main')
        
        io_frame = ttk.Frame(self.main_frame)
        io_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(io_frame, text="Input Folder:").pack(anchor='w')
        inp_box = ttk.Frame(io_frame)
        inp_box.pack(fill='x', pady=(0, 10))
        ttk.Entry(inp_box, textvariable=self.input_path).pack(side='left', fill='x', expand=True, padx=(0, 5))
        ttk.Button(inp_box, text="Browse", command=self.browse_input).pack(side='right')
        
        ttk.Label(io_frame, text="Export Path:").pack(anchor='w')
        out_box = ttk.Frame(io_frame)
        out_box.pack(fill='x', pady=(0, 10))
        ttk.Entry(out_box, textvariable=self.output_path).pack(side='left', fill='x', expand=True, padx=(0, 5))
        ttk.Button(out_box, text="Browse", command=self.browse_output).pack(side='right')
        
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(fill='x', padx=10, pady=5)
        
        self.btn_scan = ttk.Button(btn_frame, text="1. Scan", command=self.start_scan)
        self.btn_scan.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        self.btn_copy = ttk.Button(btn_frame, text="2. Copy Files", command=self.start_copy, state='disabled')
        self.btn_copy.pack(side='right', fill='x', expand=True, padx=(5, 0))
        
        prog_frame = ttk.LabelFrame(self.main_frame, text="Status", padding=10)
        prog_frame.pack(fill='x', padx=10, pady=10)
        
        self.lbl_status = ttk.Label(prog_frame, textvariable=self.status_var)
        self.lbl_status.pack(anchor='w', pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(prog_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill='x')

        log_frame = ttk.LabelFrame(self.main_frame, text="Activity Log", padding=5)
        log_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.txt_log = tk.Text(log_frame, bg="#1e1e1e", fg="white", insertbackground="white", state='disabled', height=8)
        self.txt_log.pack(fill='both', expand=True)
        
        # --- Settings Tab (Regex Rules) ---
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text='Settings')
        
        self.rule_full = RuleListWidget(self.settings_frame, "Full Copy Rules (Regex)")
        self.rule_full.pack(fill='x', padx=10, pady=10)
        
        self.rule_exclude = RuleListWidget(self.settings_frame, "Exclude Rules (Regex)")
        self.rule_exclude.pack(fill='x', padx=10, pady=10)

    def browse_input(self):
        path = filedialog.askdirectory()
        if path: self.input_path.set(path)
            
    def browse_output(self):
        path = filedialog.askdirectory()
        if path: self.output_path.set(path)

    def log(self, msg):
        self.root.after(0, self._log_ts, msg)
        
    def _log_ts(self, msg):
        self.txt_log.config(state='normal')
        self.txt_log.insert('end', f"{msg}\n")
        self.txt_log.see('end')
        self.txt_log.config(state='disabled')
        
    def get_settings(self):
        return {
            'full_rules': self.rule_full.get_rules(),
            'exclude_rules': self.rule_exclude.get_rules()
        }

    # --- Validation ---
    def validate_paths(self):
        in_path = self.input_path.get()
        out_path = self.output_path.get()
        
        if not in_path or not out_path:
            messagebox.showerror("Error", "Please select both Input and Export paths.")
            return False
            
        abs_in = os.path.abspath(in_path)
        abs_out = os.path.abspath(out_path)
        
        if abs_in == abs_out:
            messagebox.showerror("Error", "Input and Export paths cannot be the same.")
            return False
            
        try:
            common = os.path.commonpath([abs_in, abs_out])
            if common == abs_in:
                messagebox.showerror("Error", "Export path cannot be inside the Input folder.")
                return False
        except ValueError: pass
        
        if not os.path.exists(abs_in):
             messagebox.showerror("Error", "Input directory does not exist.")
             return False
             
        return True

    def check_overwrite(self):
        out_path = self.output_path.get()
        if os.path.exists(out_path) and os.listdir(out_path):
             return messagebox.askyesno("Warning", "Export folder is NOT empty.\nFiles may be overwritten.\n\nContinue?")
        return True

    # --- Scanning Logic ---
    def start_scan(self):
        if not self.validate_paths():
            return
            
        self.save_settings()
        
        self.btn_scan.config(state='disabled')
        self.btn_copy.config(state='disabled')
        self.progress_bar.config(mode='indeterminate')
        self.progress_bar.start(10)
        self.status_var.set("Scanning file structure...")
        
        sets = self.get_settings()
        
        def run():
            stats = {'files': 0, 'full': 0, 'dummy': 0, 'skipped': 0, 'size_full': 0}
            src = self.input_path.get()
            
            # Pre-compile regex for performance checking
            try:
                full_re = [re.compile(r, re.IGNORECASE) for r in sets['full_rules']]
                excl_re = [re.compile(r, re.IGNORECASE) for r in sets['exclude_rules']]
            except re.error as e:
                self.log(f"Regex Error: {e}")
                self.root.after(0, lambda: messagebox.showerror("Regex Error", str(e)))
                self.root.after(0, lambda: self.reset_ui_state()) # Need a reset
                return

            self.log(f"--- START SCAN: {src} ---")
            
            try:
                for root, dirs, files in os.walk(src):
                    for f in files:
                        stats['files'] += 1
                        
                        # Match Exclusion
                        if any(r.search(f) for r in excl_re):
                            stats['skipped'] += 1
                            continue
                            
                        # Match Full Copy
                        if any(r.search(f) for r in full_re):
                            stats['full'] += 1
                            try:
                                stats['size_full'] += os.path.getsize(os.path.join(root, f))
                            except: pass
                        else:
                            stats['dummy'] += 1
                            
                        if stats['files'] % 2000 == 0:
                            self.root.after(0, lambda c=stats['files']: self.status_var.set(f"Scanning... Found {c} files"))
                            
            except Exception as e:
                self.log(f"Scan Error: {e}")
                
            self.root.after(0, self.scan_completed, stats)
            
        threading.Thread(target=run, daemon=True).start()

    def reset_ui_state(self):
        self.progress_bar.stop()
        self.btn_scan.config(state='normal')
        self.btn_copy.config(state='normal')

    def scan_completed(self, stats):
        self.reset_ui_state()
        self.progress_bar.config(mode='determinate', value=0)
        self.scan_stats = stats
        
        # Report
        mb = stats['size_full'] / (1024*1024)
        report = (
            f"Scan Complete.\n"
            f"Total Files: {stats['files']}\n"
            f"To Hollow (Dummy): {stats['dummy']}\n"
            f"To Full Copy: {stats['full']} (~{mb:.2f} MB)\n"
            f"To Skip: {stats['skipped']}"
        )
        self.log(report)
        self.log("--------------------------------")
        self.status_var.set(f"Scan Done. Ready to copy {stats['files'] - stats['skipped']} files.")

    # --- Copy Logic ---
    def start_copy(self):
        if not self.validate_paths():
            return
            
        if not self.check_overwrite():
            self.log("Copy cancelled by user.")
            return
            
        self.save_settings()
        
        self.btn_scan.config(state='disabled')
        self.btn_copy.config(state='disabled')
        self.status_var.set("Starting Copy...")
        
        sets = self.get_settings()
        total_to_process = self.scan_stats['dummy'] + self.scan_stats['full']
        if total_to_process == 0: total_to_process = 1
        
        def run():
            src_root = self.input_path.get()
            dest_root = self.output_path.get()
            count = 0
            
            # Pre-compile regex
            try:
                full_re = [re.compile(r, re.IGNORECASE) for r in sets['full_rules']]
                excl_re = [re.compile(r, re.IGNORECASE) for r in sets['exclude_rules']]
            except re.error: return # Should have caught in scan
            
            self.log(f"--- START COPY to {dest_root} ---")
            
            try:
                for dirpath, dirnames, filenames in os.walk(src_root):
                    rel_path = os.path.relpath(dirpath, src_root)
                    target_dir = os.path.join(dest_root, rel_path)
                    
                    if not os.path.exists(target_dir):
                        try: os.makedirs(target_dir)
                        except: pass
                        
                    for file in filenames:
                        count += 1
                        src_file = os.path.join(dirpath, file)
                        target_file = os.path.join(target_dir, file)
                        
                        # Exclusion
                        if any(r.search(file) for r in excl_re):
                            continue
                            
                        # Full Copy Logic
                        full = any(r.search(file) for r in full_re)
                            
                        try:
                            if full:
                                shutil.copy2(src_file, target_file)
                            else:
                                with open(target_file, 'w') as f: pass
                        except Exception as e:
                            self.log(f"Error copying {file}: {e}")
                        
                        # Update Progress
                        if count % 100 == 0:
                            pct = (count / total_to_process) * 100
                            self.root.after(0, self.update_progress, pct, count)
                            
            except Exception as e:
                self.log(f"Copy Error: {e}")
                
            self.root.after(0, self.copy_completed)
        
        threading.Thread(target=run, daemon=True).start()

    def update_progress(self, pct, count):
        self.progress_var.set(pct)
        self.status_var.set(f"Copying... {count}/{self.scan_stats['files']}")
        
    def copy_completed(self):
        self.progress_var.set(100)
        self.status_var.set("Processing Finished.")
        self.log("--- DONE ---")
        self.reset_ui_state()

if __name__ == "__main__":
    root = tk.Tk()
    app = HollowTreeApp(root)
    root.mainloop()
