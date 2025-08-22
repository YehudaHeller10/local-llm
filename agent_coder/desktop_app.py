import os
from typing import List, Dict

from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import QAction, QDesktopServices, QTextCursor

from llm import GPT4AllClient
from file_paths import get_android_project_file_map, read_file_safely, scaffold_project_from_template, _project_root
from ui_utils import build_user_prompt


class LLMWorker(QtCore.QObject):
	progress = QtCore.Signal(str)
	chunk = QtCore.Signal(str)
	finished = QtCore.Signal()
	error = QtCore.Signal(str)

	def __init__(self, client: GPT4AllClient, system_prompt: str, prompt: str, max_tokens: int, temp: float) -> None:
		super().__init__()
		self.client = client
		self.system_prompt = system_prompt
		self.prompt = prompt
		self.max_tokens = max_tokens
		self.temp = temp

	@QtCore.Slot()
	def run(self) -> None:
		try:
			self.progress.emit("🧠 Loading model...")
			# model should already be loaded by UI
			self.progress.emit("🚀 Generating...")
			for token in self.client.generate_stream(
				prompt=self.client.build_prompt(self.system_prompt, [
					{"role": "user", "content": self.prompt}
				]),
				max_tokens=self.max_tokens,
				temp=self.temp,
			):
				self.chunk.emit(token)
			self.finished.emit()
		except Exception as exc:
			self.error.emit(str(exc))


class MainWindow(QtWidgets.QMainWindow):
	def __init__(self) -> None:
		super().__init__()
		self.setWindowTitle("Agent Coder (GPT4All) - Desktop")
		self.resize(1100, 720)

		root = _project_root()
		self.client = GPT4AllClient(models_dir=os.path.join(root, "models"))
		self._thread: QtCore.QThread | None = None
		self._worker: LLMWorker | None = None

		self._build_ui(root)
		self._refresh_models()
		self._update_file_map()

	def _build_ui(self, root: str) -> None:
		central = QtWidgets.QWidget()
		layout = QtWidgets.QHBoxLayout(central)

		# Menu
		menubar = self.menuBar()
		file_menu = menubar.addMenu("File")
		open_models_action = QAction("Open models folder", self)
		open_models_action.triggered.connect(self._open_models_dir)
		file_menu.addAction(open_models_action)

		# Left: Chat area
		left = QtWidgets.QVBoxLayout()
		self.chat_view = QtWidgets.QTextBrowser()
		self.chat_view.setOpenExternalLinks(True)
		self.chat_view.setReadOnly(True)
		self.progress_label = QtWidgets.QLabel("")
		self.input_line = QtWidgets.QLineEdit()
		self.input_line.setPlaceholderText("Ask about this file or request an edit...")
		send_btn = QtWidgets.QPushButton("Send")
		send_btn.clicked.connect(self.on_send_clicked)

		left.addWidget(QtWidgets.QLabel("Chat"))
		left.addWidget(self.chat_view, 1)
		left.addWidget(self.progress_label)
		left_io = QtWidgets.QHBoxLayout()
		left_io.addWidget(self.input_line, 1)
		left_io.addWidget(send_btn)
		left.addLayout(left_io)

		# Right: Controls
		right = QtWidgets.QFormLayout()
		self.models_dir_edit = QtWidgets.QLineEdit(os.path.join(root, "models"))
		self.model_combo = QtWidgets.QComboBox()
		self.temp_spin = QtWidgets.QDoubleSpinBox()
		self.temp_spin.setRange(0.0, 1.2)
		self.temp_spin.setSingleStep(0.05)
		self.temp_spin.setValue(0.2)
		self.max_tokens_spin = QtWidgets.QSpinBox()
		self.max_tokens_spin.setRange(128, 4096)
		self.max_tokens_spin.setSingleStep(64)
		self.max_tokens_spin.setValue(1024)
		self.system_prompt_edit = QtWidgets.QPlainTextEdit("You are a helpful Android coding assistant. Be concise. Provide edits in fenced code blocks.")
		self.system_prompt_edit.setFixedHeight(90)

		self.project_name_edit = QtWidgets.QLineEdit("my_project")
		self.base_template_edit = QtWidgets.QLineEdit(os.path.join(root, "Empty_Activity_android_studio_base_template"))
		self.copy_btn = QtWidgets.QPushButton("Create project from base (copy)")
		self.copy_btn.clicked.connect(self.on_copy_clicked)

		self.file_combo = QtWidgets.QComboBox()
		self.file_path_label = QtWidgets.QLineEdit()
		self.file_path_label.setReadOnly(True)
		self.file_preview = QtWidgets.QPlainTextEdit()
		self.file_preview.setReadOnly(True)
		self.file_preview.setFixedHeight(220)

		# Wire signals
		self.models_dir_edit.editingFinished.connect(self._on_models_dir_changed)
		self.model_combo.currentIndexChanged.connect(self._on_model_selected)
		self.project_name_edit.editingFinished.connect(self._update_file_map)
		self.file_combo.currentIndexChanged.connect(self._on_file_selected)

		# Assemble right pane
		right.addRow("Models dir", self.models_dir_edit)
		right.addRow("Model", self.model_combo)
		right.addRow("Temperature", self.temp_spin)
		right.addRow("Max tokens", self.max_tokens_spin)
		right.addRow("System prompt", self.system_prompt_edit)
		right.addRow(QtWidgets.QLabel(""))
		right.addRow("project_name", self.project_name_edit)
		right.addRow("Base template directory", self.base_template_edit)
		right.addRow(self.copy_btn)
		right.addRow("Target file", self.file_combo)
		right.addRow("Path", self.file_path_label)
		right.addRow("Preview", self.file_preview)

		layout.addLayout(left, 2)
		layout.addLayout(right, 1)
		self.setCentralWidget(central)

	def _refresh_models(self) -> None:
		self.client.models_dir = self.models_dir_edit.text().strip()
		models = self.client.list_local_models()
		self.model_combo.clear()
		self.model_combo.addItems(models)

	def _on_models_dir_changed(self) -> None:
		self._refresh_models()

	def _on_model_selected(self) -> None:
		# lazy load on send
		pass

	def _update_file_map(self) -> None:
		project_name = self.project_name_edit.text().strip()
		self.file_map = get_android_project_file_map(project_name)
		self.file_combo.blockSignals(True)
		self.file_combo.clear()
		self.file_combo.addItems(list(self.file_map.keys()))
		self.file_combo.blockSignals(False)
		self._on_file_selected()

	def _on_file_selected(self) -> None:
		filename = self.file_combo.currentText()
		path = self.file_map.get(filename, "")
		self.file_path_label.setText(path)
		self.file_preview.setPlainText(read_file_safely(path))

	@QtCore.Slot()
	def on_copy_clicked(self) -> None:
		project_name = self.project_name_edit.text().strip()
		base_dir = self.base_template_edit.text().strip()
		created, dest_dir, msg = scaffold_project_from_template(project_name, base_dir)
		QtWidgets.QMessageBox.information(self, "Scaffold", msg)
		self._update_file_map()

	@QtCore.Slot()
	def on_send_clicked(self) -> None:
		user_text = self.input_line.text().strip()
		if not user_text:
			return
		model_name = self.model_combo.currentText().strip()
		if not model_name:
			QtWidgets.QMessageBox.warning(self, "Model", "Please select a model.")
			return

		# Prepare prompt
		filename = self.file_combo.currentText()
		file_path = self.file_map.get(filename, "")
		file_content = read_file_safely(file_path)
		prompt = build_user_prompt(filename, file_content, user_text)

		# Reset UI
		self.chat_view.append("<b>User:</b> " + QtWidgets.QApplication.translate("", user_text))
		self.chat_view.append("<b>Assistant:</b> ")
		self.progress_label.setText("🔧 Preparing prompt...")
		self.input_line.clear()

		# Load model (blocking short)
		try:
			self.client.load_model(model_name, verbose=False)
		except Exception as exc:
			QtWidgets.QMessageBox.critical(self, "Model load failed", str(exc))
			return

		# Start worker thread
		self._thread = QtCore.QThread()
		self._worker = LLMWorker(
			client=self.client,
			system_prompt=self.system_prompt_edit.toPlainText(),
			prompt=prompt,
			max_tokens=int(self.max_tokens_spin.value()),
			temp=float(self.temp_spin.value()),
		)
		self._worker.moveToThread(self._thread)
		self._thread.started.connect(self._worker.run)
		self._worker.progress.connect(self.progress_label.setText)
		self._worker.chunk.connect(self._on_chunk)
		self._worker.finished.connect(self._on_finished)
		self._worker.error.connect(self._on_error)
		self._worker.finished.connect(self._thread.quit)
		self._worker.finished.connect(self._worker.deleteLater)
		self._thread.finished.connect(self._thread.deleteLater)
		self._thread.start()

	def _open_models_dir(self) -> None:
		path = self.models_dir_edit.text().strip()
		QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path))

	@QtCore.Slot(str)
	def _on_chunk(self, token: str) -> None:
		# Append token to the end of the assistant message
		self.chat_view.moveCursor(QTextCursor.End)
		self.chat_view.insertPlainText(token)
		self.chat_view.moveCursor(QTextCursor.End)
		self.chat_view.ensureCursorVisible()

	@QtCore.Slot()
	def _on_finished(self) -> None:
		self.progress_label.setText("✅ Done")

	@QtCore.Slot(str)
	def _on_error(self, message: str) -> None:
		self.progress_label.setText("")
		QtWidgets.QMessageBox.critical(self, "Generation error", message)


def main() -> None:
	app = QtWidgets.QApplication([])
	w = MainWindow()
	w.show()
	app.exec()


if __name__ == "__main__":
	main()