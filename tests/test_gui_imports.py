import unittest


class GuiImportTests(unittest.TestCase):
    def test_gui_modules_import(self) -> None:
        from openmorfeus.gui import MainWindow
        from openmorfeus.sweep_gui import SweepDialog

        self.assertIsNotNone(MainWindow)
        self.assertIsNotNone(SweepDialog)


if __name__ == "__main__":
    unittest.main()
