"""GUI responsiveness regression: a slow device probe must not block Qt."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sys
import unittest
from unittest.mock import patch
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from pocsag_gui import HackRFIndicator

class GuiTests(unittest.TestCase):
    def test_slow_probe_keeps_event_loop_responsive(self):
        app = QApplication.instance() or QApplication([])
        ticks = []
        with patch("pocsag_gui.tool_path", return_value=sys.executable):
            indicator = HackRFIndicator()
            heartbeat = QTimer()
            heartbeat.timeout.connect(lambda: ticks.append(1))
            heartbeat.start(50)
            QTimer.singleShot(500, app.quit)
            app.exec()
            heartbeat.stop()
            indicator._timer.stop()
            indicator._probe.kill()
            indicator._probe.waitForFinished(1000)
            self.assertGreaterEqual(len(ticks), 5)

if __name__ == "__main__": unittest.main()
