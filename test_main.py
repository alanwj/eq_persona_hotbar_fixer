import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import main


class TestFilenameIdentification(unittest.TestCase):
    def test_is_global_keymap_ini_valid(self):
        self.assertTrue(main.is_global_keymap_ini("eqclient.ini"))
        self.assertTrue(main.is_global_keymap_ini("EQCLIENT.INI"))
        self.assertTrue(main.is_global_keymap_ini("eqclient-custom.ini"))
        self.assertTrue(main.is_global_keymap_ini("EQCLIENT-TEST.INI"))

    def test_is_global_keymap_ini_invalid(self):
        self.assertFalse(main.is_global_keymap_ini("ui_eqclient.ini"))
        self.assertFalse(main.is_global_keymap_ini("eqclient.txt"))
        self.assertFalse(main.is_global_keymap_ini("random_file.ini"))

    def test_is_persona_ini_valid(self):
        for cls in main.VALID_CLASSES:
            filename = f"Charname_Server_{cls}.ini"
            self.assertTrue(main.is_persona_ini(filename), f"Failed for class {cls}")

    def test_is_persona_ini_invalid(self):
        self.assertFalse(main.is_persona_ini("ui_Charname_Server_war.ini"))
        self.assertFalse(main.is_persona_ini("Charname_war.ini"))
        self.assertFalse(main.is_persona_ini("A_B_C_D_war.ini"))
        self.assertFalse(main.is_persona_ini("Charname_Server_xyz.ini"))
        self.assertFalse(main.is_persona_ini("Charname_Server_war.txt"))


class TestInitialDirectoryDetermination(unittest.TestCase):
    def test_cli_argument_priority(self):
        result = main.determine_initial_directory("C:/Custom/Path")
        self.assertEqual(result, "C:/Custom/Path")

    @patch("os.getcwd")
    @patch("os.listdir")
    def test_cwd_matching_ini(self, mock_listdir, mock_getcwd):
        mock_getcwd.return_value = "/fake/cwd"
        mock_listdir.return_value = ["somefile.txt", "eqclient.ini"]
        result = main.determine_initial_directory(None)
        self.assertEqual(result, "/fake/cwd")

    @patch("os.getcwd")
    @patch("os.listdir")
    @patch("os.path.isdir")
    def test_default_daybreak_folder_fallback(self, mock_isdir, mock_listdir, mock_getcwd):
        mock_getcwd.return_value = "/fake/cwd"
        mock_listdir.return_value = ["otherfile.txt"]
        mock_isdir.side_effect = lambda path: path == main.DEFAULT_EQ_PATH
        result = main.determine_initial_directory(None)
        self.assertEqual(result, main.DEFAULT_EQ_PATH)

    @patch("os.getcwd")
    @patch("os.listdir")
    @patch("os.path.isdir")
    def test_empty_fallback(self, mock_isdir, mock_listdir, mock_getcwd):
        mock_getcwd.return_value = "/fake/cwd"
        mock_listdir.return_value = ["otherfile.txt"]
        mock_isdir.return_value = False
        result = main.determine_initial_directory(None)
        self.assertEqual(result, "")


class TestGeneratorsAndParsers(unittest.TestCase):
    def test_case_sensitive_configparser(self):
        parser = main.CaseSensitiveConfigParser()
        parser.add_section("KeyMaps")
        parser.set("KeyMaps", "KEYMAPPING_HOT1_1_1", "2")
        self.assertIn("KEYMAPPING_HOT1_1_1", parser["KeyMaps"])
        self.assertNotIn("keymapping_hot1_1_1", parser["KeyMaps"])

    def test_generate_all_hotbar_keys(self):
        keys = main.generate_all_hotbar_keys()
        self.assertEqual(len(keys), 484)
        self.assertIn("KEYMAPPING_HOT1_1_1", keys)
        self.assertIn("KEYMAPPING_HOT11_12_2", keys)
        self.assertIn("KEYMAPPING_HOTPAGE1_1_1", keys)
        self.assertIn("KEYMAPPING_HOTPAGE11_10_2", keys)


class TestKeymapCopyLogic(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_keymap_rules_and_backup(self):
        # Create global file
        global_path = os.path.join(self.test_dir, "eqclient.ini")
        with open(global_path, "w", encoding="utf-8") as f:
            f.write("[KeyMaps]\n")
            f.write("KEYMAPPING_HOT1_1_2=99\n")
            f.write("KEYMAPPING_HOT2_1_1=88\n")

        # Create persona file
        persona_filename = "Char_Server_war.ini"
        persona_path = os.path.join(self.test_dir, persona_filename)
        with open(persona_path, "w", encoding="utf-8") as f:
            f.write("[KeyMaps]\n")
            f.write("KEYMAPPING_HOT1_1_1=55\n")

        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        app = main.EQPersonaHotbarFixerApp(root, initial_folder=self.test_dir)

        # Select items
        app.selected_global_file.set("eqclient.ini")
        app.persona_listbox.select_set(0)

        # Mock messagebox to prevent popups during automated test execution
        with patch("tkinter.messagebox.showinfo") as mock_info:
            app._on_copy_keymaps()
            self.assertTrue(mock_info.called)

        root.destroy()

        # Check backup file exists
        dir_files = os.listdir(self.test_dir)
        backups = [f for f in dir_files if f.endswith(f"-{persona_filename}")]
        self.assertEqual(len(backups), 1)

        # Inspect updated persona file
        updated_config = main.CaseSensitiveConfigParser()
        updated_config.read(persona_path, encoding="utf-8")
        km = updated_config["KeyMaps"]

        # Rule 1: Preserved existing key (HOT1_1_1)
        self.assertEqual(km.get("KEYMAPPING_HOT1_1_1"), "55")
        # Rule 2: Copied from global (HOT2_1_1)
        self.assertEqual(km.get("KEYMAPPING_HOT2_1_1"), "88")
        # Rule 3: Hotbar 1 primary default (button 2 primary = code 3)
        self.assertEqual(km.get("KEYMAPPING_HOT1_2_1"), "3")
        # Rule 4: Unassigned slot sealed with "0"
        self.assertEqual(km.get("KEYMAPPING_HOT3_1_1"), "0")


if __name__ == "__main__":
    unittest.main()
