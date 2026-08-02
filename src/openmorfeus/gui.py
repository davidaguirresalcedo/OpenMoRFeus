"""Optional PyQt6 graphical interface for OpenMoRFeus."""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence

from PyQt6.QtCore import (
    QObject,
    QRunnable,
    QThreadPool,
    QTimer,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .device import LcdTimeout, OperatingMode
from .gui_controller import (
    GuiDeviceState,
    apply_state,
    read_state,
)
from .sweep_gui import SweepDialog


class WorkerSignals(QObject):
    """Signals emitted by one background hardware operation."""

    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)
    finished = pyqtSignal()


class OperationWorker(QRunnable):
    """Run a blocking hardware operation outside the GUI thread."""

    def __init__(
        self,
        operation: Callable[[], GuiDeviceState],
    ):
        super().__init__()
        self._operation = operation
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        try:
            result = self._operation()
        except Exception as exc:
            self.signals.failed.emit(
                f"{type(exc).__name__}: {exc}"
            )
        else:
            self.signals.succeeded.emit(result)
        finally:
            self.signals.finished.emit()


class MainWindow(QMainWindow):
    """Main OpenMoRFeus control window."""

    def __init__(self) -> None:
        super().__init__()

        self._thread_pool = QThreadPool.globalInstance()
        self._busy = False

        self.setWindowTitle("OpenMoRFeus")
        self.setMinimumSize(560, 390)

        self._build_interface()
        self.statusBar().showMessage("Ready")

        QTimer.singleShot(100, self.refresh_state)

    def _build_interface(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)

        title = QLabel(
            "<h2>OpenMoRFeus</h2>"
            "<p>Hardware-validated moRFeus controller</p>"
        )
        root.addWidget(title)

        connection_group = QGroupBox("Connection")
        connection_layout = QHBoxLayout(connection_group)

        connection_layout.addWidget(QLabel("Device index:"))

        self.device_index = QSpinBox()
        self.device_index.setRange(0, 31)
        self.device_index.setValue(0)
        connection_layout.addWidget(self.device_index)

        connection_layout.addStretch()

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(
            self.refresh_state
        )
        connection_layout.addWidget(self.refresh_button)

        root.addWidget(connection_group)

        self.settings_group = QGroupBox(
            "Documented device settings"
        )
        form = QFormLayout(self.settings_group)

        self.frequency_input = QDoubleSpinBox()
        self.frequency_input.setDecimals(6)
        self.frequency_input.setRange(85.0, 5400.0)
        self.frequency_input.setSingleStep(0.1)
        self.frequency_input.setSuffix(" MHz")
        self.frequency_input.setKeyboardTracking(False)
        form.addRow("Frequency:", self.frequency_input)

        self.mode_input = QComboBox()
        self.mode_input.addItem(
            "Mixer",
            OperatingMode.MIXER,
        )
        self.mode_input.addItem(
            "Generator",
            OperatingMode.GENERATOR,
        )
        form.addRow("Operating mode:", self.mode_input)

        self.mixer_current_input = QSpinBox()
        self.mixer_current_input.setRange(0, 7)
        form.addRow(
            "Mixer current:",
            self.mixer_current_input,
        )

        self.bias_tee_input = QComboBox()
        self.bias_tee_input.addItem("Off", False)
        self.bias_tee_input.addItem("On", True)
        form.addRow("Bias Tee:", self.bias_tee_input)

        self.lcd_timeout_input = QComboBox()
        self.lcd_timeout_input.addItem(
            "Always on",
            LcdTimeout.ALWAYS_ON,
        )
        self.lcd_timeout_input.addItem(
            "10 seconds",
            LcdTimeout.TEN_SECONDS,
        )
        self.lcd_timeout_input.addItem(
            "60 seconds",
            LcdTimeout.SIXTY_SECONDS,
        )
        form.addRow(
            "LCD timeout:",
            self.lcd_timeout_input,
        )

        root.addWidget(self.settings_group)

        buttons = QHBoxLayout()
        buttons.addStretch()

        self.sweep_button = QPushButton(
            "Sweep generator…"
        )
        self.sweep_button.clicked.connect(
            self.open_sweep_dialog
        )
        buttons.addWidget(self.sweep_button)

        self.apply_button = QPushButton(
            "Apply and verify"
        )
        self.apply_button.clicked.connect(
            self.apply_current_state
        )
        buttons.addWidget(self.apply_button)

        root.addLayout(buttons)
        root.addStretch()

        self.setCentralWidget(central)

    def _connection_parameters(
        self,
    ) -> dict[str, int | float]:
        return {
            "index": self.device_index.value(),
            "response_timeout_s": 1.0,
            "poll_interval_s": 0.005,
        }

    def _state_from_widgets(self) -> GuiDeviceState:
        mode = self.mode_input.currentData()
        bias_tee = self.bias_tee_input.currentData()
        lcd_timeout = self.lcd_timeout_input.currentData()

        if not isinstance(mode, OperatingMode):
            raise RuntimeError(
                "invalid operating-mode selection"
            )

        if not isinstance(bias_tee, bool):
            raise RuntimeError(
                "invalid Bias Tee selection"
            )

        if not isinstance(lcd_timeout, LcdTimeout):
            raise RuntimeError(
                "invalid LCD timeout selection"
            )

        return GuiDeviceState(
            frequency_hz=round(
                self.frequency_input.value()
                * 1_000_000
            ),
            mode=mode,
            mixer_current=(
                self.mixer_current_input.value()
            ),
            bias_tee_enabled=bias_tee,
            lcd_timeout=lcd_timeout,
        )

    def _set_combo_value(
        self,
        combo: QComboBox,
        value: object,
    ) -> None:
        index = combo.findData(value)

        if index < 0:
            raise RuntimeError(
                f"GUI has no option for value {value!r}"
            )

        combo.setCurrentIndex(index)

    def _display_state(
        self,
        state: GuiDeviceState,
    ) -> None:
        self.frequency_input.setValue(
            state.frequency_hz / 1_000_000
        )
        self._set_combo_value(
            self.mode_input,
            state.mode,
        )
        self.mixer_current_input.setValue(
            state.mixer_current
        )
        self._set_combo_value(
            self.bias_tee_input,
            state.bias_tee_enabled,
        )
        self._set_combo_value(
            self.lcd_timeout_input,
            state.lcd_timeout,
        )

        self.statusBar().showMessage(
            "Device state synchronized"
        )

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.device_index.setEnabled(not busy)
        self.settings_group.setEnabled(not busy)
        self.refresh_button.setEnabled(not busy)
        self.sweep_button.setEnabled(not busy)
        self.apply_button.setEnabled(not busy)

    def _start_operation(
        self,
        message: str,
        operation: Callable[[], GuiDeviceState],
    ) -> None:
        if self._busy:
            return

        self._set_busy(True)
        self.statusBar().showMessage(message)

        worker = OperationWorker(operation)
        worker.signals.succeeded.connect(
            self._display_state
        )
        worker.signals.failed.connect(
            self._operation_failed
        )
        worker.signals.finished.connect(
            self._operation_finished
        )

        self._thread_pool.start(worker)

    def _operation_failed(self, message: str) -> None:
        self.statusBar().showMessage(
            "Hardware operation failed"
        )

        QMessageBox.critical(
            self,
            "OpenMoRFeus error",
            message,
        )

    def _operation_finished(self) -> None:
        self._set_busy(False)

    def open_sweep_dialog(self) -> None:
        """Open the modal, background-operated sweep dialog."""

        if self._busy:
            return

        dialog = SweepDialog(
            connection_parameters=(
                self._connection_parameters()
            ),
            initial_frequency_hz=round(
                self.frequency_input.value()
                * 1_000_000
            ),
            parent=self,
        )

        dialog.exec()

        # Synchronize the main controls after completion,
        # restoration, interruption, or manual closure.
        self.refresh_state()

    def refresh_state(self) -> None:
        parameters = self._connection_parameters()

        self._start_operation(
            "Reading device state…",
            lambda: read_state(**parameters),
        )

    def apply_current_state(self) -> None:
        desired = self._state_from_widgets()
        parameters = self._connection_parameters()

        self._start_operation(
            "Applying and verifying settings…",
            lambda: apply_state(
                desired,
                **parameters,
            ),
        )


def main(
    argv: Sequence[str] | None = None,
) -> int:
    arguments = (
        list(argv)
        if argv is not None
        else sys.argv
    )

    application = QApplication(arguments)
    application.setApplicationName("OpenMoRFeus")
    application.setOrganizationName("OpenMoRFeus")

    window = MainWindow()
    window.show()

    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
