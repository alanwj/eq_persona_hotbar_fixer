import argparse
import configparser
from datetime import datetime
import os
import shutil
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

DEFAULT_EQ_PATH = r"C:\Users\Public\Daybreak Game Company\Installed Games\EverQuest"

# 3-letter EQ class abbreviations used by the client for persona INI suffixes
VALID_CLASSES = {
    "brd", "bst", "ber", "clr", "dru", "enc", 
    "mag", "mnk", "nec", "pal", "rng", "rog", 
    "shd", "shm", "war", "wiz"
}

# Hardcoded EQ defaults for Hotbar 1 Primary Keys (Buttons 1-12 mapped to codes 2-13)
HOT1_DEFAULTS = {
    f"KEYMAPPING_HOT1_{btn}_1": str(btn + 1) for btn in range(1, 13)
}


class CaseSensitiveConfigParser(configparser.ConfigParser):
    """ConfigParser variant that preserves key casing (EverQuest INIs are case-sensitive)."""
    def optionxform(self, optionstr):
        return optionstr


def generate_all_hotbar_keys():
    """Generates all 484 possible hotbar and direct page key names:
    - 264 Hotbar buttons (KEYMAPPING_HOT1_1_1 to KEYMAPPING_HOT11_12_2)
    - 220 Direct Page selection keys (KEYMAPPING_HOTPAGE1_1_1 to KEYMAPPING_HOTPAGE11_10_2)
    """
    keys = []
    for bar in range(1, 12):
        # 1. Hotbuttons (Buttons 1 to 12, keys 1 and 2)
        for btn in range(1, 13):
            for key_num in (1, 2):
                keys.append(f"KEYMAPPING_HOT{bar}_{btn}_{key_num}")
                
        # 2. Direct Page Selection (Pages 1 to 10, keys 1 and 2)
        for page in range(1, 11):
            for key_num in (1, 2):
                keys.append(f"KEYMAPPING_HOTPAGE{bar}_{page}_{key_num}")
                
    return keys


def is_global_keymap_ini(filename: str) -> bool:
    """Checks if a file is a global keymap INI file (named eqclient.ini or eqclient-*.ini)."""
    lower_name = filename.lower()
    return lower_name == "eqclient.ini" or (lower_name.startswith("eqclient-") and lower_name.endswith(".ini"))


def is_persona_ini(filename: str) -> bool:
    """Checks if a file is a valid persona INI file (non-UI, exactly two underscores,
    and ends in a valid 3-letter EQ class abbreviation)."""
    name, ext = os.path.splitext(filename.lower())
    if ext != '.ini' or name.startswith('ui_'):
        return False
    
    parts = name.split('_')
    if len(parts) == 3:
        return parts[2] in VALID_CLASSES
    return False


def determine_initial_directory(cli_dir: str | None = None) -> str:
    """Determine the initial EverQuest folder based on priority rules:
    1. Command line argument (if provided).
    2. Current working directory (if it contains eqclient.ini or eqclient-*.ini).
    3. Default Daybreak installation path (if it exists).
    4. Fallback to empty string (no initial directory).
    """
    # 1. Command line parameter
    if cli_dir:
        return cli_dir

    # 2. Current working directory check for eqclient.ini or eqclient-*.ini
    try:
        cwd = os.getcwd()
        for filename in os.listdir(cwd):
            if is_global_keymap_ini(filename):
                return cwd
    except Exception:
        pass

    # 3. Default EverQuest installation path
    if os.path.isdir(DEFAULT_EQ_PATH):
        return DEFAULT_EQ_PATH

    # 4. Fallback: no initial directory
    return ""


class EQPersonaHotbarFixerApp:
    def __init__(self, root: tk.Tk, initial_folder: str = ""):
        self.root = root
        self.root.title("EQ Persona Hotbar Fixer")
        self.root.geometry("600x450")
        self.root.minsize(450, 350)
        self.root.resizable(True, True)

        self.eq_folder = tk.StringVar(value=initial_folder)
        self.selected_global_file = tk.StringVar()

        self._create_widgets()

        # Update file lists whenever folder variable changes
        self.eq_folder.trace_add("write", lambda *args: self._refresh_file_lists())
        self._refresh_file_lists()

    def _create_widgets(self):
        # Main container frame with padding
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Section 1: EverQuest Folder Selection ---
        folder_frame = ttk.Frame(main_frame)
        folder_frame.pack(fill=tk.X, anchor=tk.N, pady=(0, 10))
        folder_frame.columnconfigure(0, weight=1)

        folder_label = ttk.Label(folder_frame, text="EverQuest Folder")
        folder_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))

        self.folder_entry = ttk.Entry(folder_frame, textvariable=self.eq_folder)
        self.folder_entry.grid(row=1, column=0, sticky=tk.EW, padx=(0, 5))

        browse_button = ttk.Button(folder_frame, text="Browse...", command=self._browse_folder)
        browse_button.grid(row=1, column=1, sticky=tk.E)

        # --- Section 2: Global Keymap Files ---
        global_frame = ttk.Frame(main_frame)
        global_frame.pack(fill=tk.X, anchor=tk.N, pady=(0, 10))
        global_frame.columnconfigure(0, weight=1)

        global_label = ttk.Label(global_frame, text="Global Keymap Files")
        global_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        self.global_combo = ttk.Combobox(
            global_frame,
            textvariable=self.selected_global_file,
            state="readonly"
        )
        self.global_combo.grid(row=1, column=0, sticky=tk.EW)

        # --- Section 3: Persona Keymap Files ---
        persona_frame = ttk.Frame(main_frame)
        persona_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        persona_label = ttk.Label(persona_frame, text="Persona Keymap Files")
        persona_label.pack(anchor=tk.W, pady=(0, 5))

        list_container = ttk.Frame(persona_frame)
        list_container.pack(fill=tk.BOTH, expand=True)

        self.persona_listbox = tk.Listbox(
            list_container,
            selectmode=tk.EXTENDED,
            exportselection=False
        )
        self.persona_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(
            list_container,
            orient=tk.VERTICAL,
            command=self.persona_listbox.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.persona_listbox.config(yscrollcommand=scrollbar.set)

        # --- Section 4: Action Button ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, anchor=tk.S)

        self.copy_button = ttk.Button(
            button_frame,
            text="Copy Keymaps",
            command=self._on_copy_keymaps
        )
        self.copy_button.pack(side=tk.RIGHT)

    def _browse_folder(self):
        initial_dir = self.eq_folder.get()
        kwargs = {"title": "Select EverQuest Folder"}
        if initial_dir and os.path.isdir(initial_dir):
            kwargs["initialdir"] = initial_dir

        selected_directory = filedialog.askdirectory(**kwargs)
        if selected_directory:
            self.eq_folder.set(selected_directory)

    def _refresh_file_lists(self):
        folder = self.eq_folder.get().strip()

        global_files = []
        persona_files = []

        if folder and os.path.isdir(folder):
            try:
                all_files = os.listdir(folder)
                global_files = sorted([f for f in all_files if is_global_keymap_ini(f)])
                persona_files = sorted([f for f in all_files if is_persona_ini(f)])
            except OSError:
                pass

        # Update global keymap combo box
        self.global_combo['values'] = global_files
        if global_files:
            default_global = global_files[0]
            for gf in global_files:
                if gf.lower() == "eqclient.ini":
                    default_global = gf
                    break
            self.selected_global_file.set(default_global)
        else:
            self.selected_global_file.set("")

        # Update persona keymap list box
        self.persona_listbox.delete(0, tk.END)
        for pf in persona_files:
            self.persona_listbox.insert(tk.END, pf)

    def _on_copy_keymaps(self):
        eq_dir = self.eq_folder.get().strip()
        if not eq_dir or not os.path.isdir(eq_dir):
            messagebox.showwarning("Invalid Directory", "Please select a valid EverQuest folder first.")
            return

        global_filename = self.selected_global_file.get().strip()
        if not global_filename:
            messagebox.showwarning("No Global Keymap Selected", "Please select a global keymap file.")
            return

        selected_indices = self.persona_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Persona Files Selected", "Please select at least one persona keymap file from the list.")
            return

        selected_persona_files = [self.persona_listbox.get(idx) for idx in selected_indices]
        global_path = os.path.join(eq_dir, global_filename)

        if not os.path.exists(global_path):
            messagebox.showerror("File Not Found", f"Global keymap file not found:\n{global_path}")
            return

        # Load global keymaps
        global_keymaps = {}
        global_config = CaseSensitiveConfigParser()
        try:
            global_config.read(global_path, encoding='utf-8')
            if global_config.has_section('KeyMaps'):
                global_keymaps = global_config['KeyMaps']
        except Exception as e:
            messagebox.showerror("Error Reading Global File", f"Failed to read global keymap file:\n{e}")
            return

        master_hotbar_keys = generate_all_hotbar_keys()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        success_count = 0
        failed_files = []
        total_copied = 0
        total_secured = 0

        for persona_filename in selected_persona_files:
            persona_path = os.path.join(eq_dir, persona_filename)
            if not os.path.exists(persona_path):
                failed_files.append((persona_filename, "File not found"))
                continue

            # Create backup file: <timestamp>-<original filename>
            backup_filename = f"{timestamp}-{persona_filename}"
            backup_path = os.path.join(eq_dir, backup_filename)
            try:
                shutil.copy2(persona_path, backup_path)
            except Exception as e:
                failed_files.append((persona_filename, f"Backup failed: {e}"))
                continue

            # Read target persona file
            persona_config = CaseSensitiveConfigParser()
            try:
                persona_config.read(persona_path, encoding='utf-8')
                if not persona_config.has_section('KeyMaps'):
                    persona_config.add_section('KeyMaps')
                persona_keymaps = persona_config['KeyMaps']

                copied_count = 0
                secured_count = 0

                for key in master_hotbar_keys:
                    # Rule 1: Explicitly defined in persona -> preserve it
                    if key in persona_keymaps:
                        continue
                    
                    # Rule 2: Explicitly defined in global -> copy it
                    if key in global_keymaps:
                        persona_keymaps[key] = global_keymaps[key]
                        copied_count += 1
                    # Rule 3: Missing in both, but Hotbar 1 primary -> use default (2-13)
                    elif key in HOT1_DEFAULTS:
                        persona_keymaps[key] = HOT1_DEFAULTS[key]
                        copied_count += 1
                    # Rule 4: Missing in both -> explicitly set '0' to sever fallbacks
                    else:
                        persona_keymaps[key] = "0"
                        secured_count += 1

                with open(persona_path, 'w', encoding='utf-8') as configfile:
                    persona_config.write(configfile, space_around_delimiters=False)

                success_count += 1
                total_copied += copied_count
                total_secured += secured_count
            except Exception as e:
                failed_files.append((persona_filename, f"Processing failed: {e}"))

        # Build summary report
        msg_lines = [
            "Keymaps copy process complete!",
            f"Files updated: {success_count}/{len(selected_persona_files)}",
            f"Active/Default keybinds applied: {total_copied}",
            f"Fallback slots sealed with '0': {total_secured}"
        ]
        if failed_files:
            msg_lines.append("\nErrors encountered:")
            for fname, err in failed_files:
                msg_lines.append(f" - {fname}: {err}")
            messagebox.showwarning("Completed with Errors", "\n".join(msg_lines))
        else:
            messagebox.showinfo("Success", "\n".join(msg_lines))


def main():
    parser = argparse.ArgumentParser(description="EQ Persona Hotbar Fixer")
    parser.add_argument("folder", nargs="?", help="Optional path to EverQuest folder")
    args = parser.parse_args()

    initial_dir = determine_initial_directory(args.folder)

    root = tk.Tk()
    
    # Configure modern ttk theme if available
    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")
    
    app = EQPersonaHotbarFixerApp(root, initial_folder=initial_dir)
    root.mainloop()


if __name__ == "__main__":
    main()




