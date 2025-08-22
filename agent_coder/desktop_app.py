import os
from typing import List, Dict

from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import QAction, QDesktopServices, QTextCursor

from llm import GPT4AllClient
from file_paths import get_android_project_file_map, read_file_safely, scaffold_project_from_template, _project_root
from ui_utils import build_user_prompt, build_multi_file_prompt
from agent_tool import AndroidAgent


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

		# Simple mode controls for non-technical users
		self.simple_mode_checkbox = QtWidgets.QCheckBox("Simple Mode (No-Code)")
		self.simple_prompt = QtWidgets.QPlainTextEdit()
		self.simple_prompt.setPlaceholderText("Describe the app you want (e.g., a notes app with add/list/delete)...")
		self.simple_prompt.setFixedHeight(100)
		self.simple_start_btn = QtWidgets.QPushButton("Build Android App")
		self.simple_start_btn.setStyleSheet("font-weight: bold; padding: 8px 12px;")
		self.simple_start_btn.clicked.connect(self.on_agent_auto)

		left.addWidget(QtWidgets.QLabel("Chat"))
		left.addWidget(self.chat_view, 1)
		left.addWidget(self.progress_label)
		left_io = QtWidgets.QHBoxLayout()
		left_io.addWidget(self.input_line, 1)
		left_io.addWidget(send_btn)
		left.addLayout(left_io)
		left.addWidget(QtWidgets.QLabel(""))
		left.addWidget(self.simple_mode_checkbox)
		left.addWidget(self.simple_prompt)
		left.addWidget(self.simple_start_btn)

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

		self.include_all_checkbox = QtWidgets.QCheckBox("Include all 4 files in prompt")
		self.lite_mode_checkbox = QtWidgets.QCheckBox("Lite mode (single-file prompt, faster)")
		self.apply_button = QtWidgets.QPushButton("Apply Edits from last response")
		self.apply_button.clicked.connect(self.on_apply_clicked)

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
		right.addRow(self.include_all_checkbox)
		right.addRow(self.lite_mode_checkbox)
		right.addRow(self.apply_button)

		layout.addLayout(left, 2)
		layout.addLayout(right, 1)
		self.setCentralWidget(central)

		# Agent panel at bottom
		agent_panel = QtWidgets.QGroupBox("Android Agent Developer")
		agent_layout = QtWidgets.QVBoxLayout(agent_panel)
		self.agent_status = QtWidgets.QTextBrowser()
		self.agent_status.setFixedHeight(180)
		self.agent_spinner = QtWidgets.QLabel("⏳ Idle")
		self.agent_progress = QtWidgets.QProgressBar()
		self.agent_progress.setRange(0, 6)
		self.agent_progress.setValue(0)
		self.agent_run_button = QtWidgets.QPushButton("Run Agent (JSON-based)")
		self.agent_run_button.clicked.connect(self.on_agent_run)
		self.agent_auto_button = QtWidgets.QPushButton("Auto-Run (Scaffold → Plan → Generate → QA)")
		self.agent_auto_button.clicked.connect(self.on_agent_auto)
		agent_layout.addWidget(self.agent_status)
		agent_layout.addWidget(self.agent_spinner)
		agent_layout.addWidget(self.agent_progress)
		agent_layout.addWidget(self.agent_run_button)
		agent_layout.addWidget(self.agent_auto_button)
		layout.addWidget(agent_panel, 0)

	def _refresh_models(self) -> None:
		self.client.models_dir = self.models_dir_edit.text().strip()
		models = self.client.list_local_models()
		self.model_combo.clear()
		self.model_combo.addItems(models)
		# Preselect first
		if models:
			self.model_combo.setCurrentIndex(0)
			self._preload_model_if_available()

	def _on_models_dir_changed(self) -> None:
		self._refresh_models()

	def _on_model_selected(self) -> None:
		self._preload_model_if_available()

	def _preload_model_if_available(self) -> None:
		model_name = self.model_combo.currentText().strip()
		if not model_name:
			return
		try:
			self.progress_label.setText(f"🧠 Preloading model: {model_name}...")
			self.client.load_model(model_name, verbose=False)
			self.progress_label.setText("Model ready ✅")
		except Exception as exc:
			self.progress_label.setText("")
			QtWidgets.QMessageBox.warning(self, "Model preload", f"Failed to preload {model_name}: {exc}")

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
		if (self.include_all_checkbox.isChecked() and not self.lite_mode_checkbox.isChecked()):
			# Build multi-file map with current project files
			fname_to_content: Dict[str, str] = {}
			for fname, fpath in self.file_map.items():
				fname_to_content[fname] = read_file_safely(fpath)
			prompt = build_multi_file_prompt(fname_to_content, user_text)
		else:
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

	def on_apply_clicked(self) -> None:
		# Parse the last assistant message and apply edits to files (backup originals)
		if not hasattr(self, "file_map"):
			return
		# find last assistant message from the chat_view
		text = self.chat_view.toPlainText()
		if not text:
			QtWidgets.QMessageBox.information(self, "Apply", "No assistant response to parse.")
			return
		applied_count = self._apply_edits_from_text(text)
		QtWidgets.QMessageBox.information(self, "Apply", f"Applied edits to {applied_count} file(s).")
		self._on_file_selected()

	def _apply_edits_from_text(self, text: str) -> int:
		# Very simple parser expecting sections like:
		# File: AndroidManifest.xml\n```xml\n...\n```  OR File: MainActivity.kt\n```kotlin\n...\n```
		count = 0
		lines = text.splitlines()
		current_file = None
		collecting = False
		buffer: List[str] = []
		for line in lines:
			if line.strip().startswith("File:"):
				# flush previous
				if current_file and buffer:
					if self._write_file_if_target(current_file, "\n".join(buffer)):
						count += 1
				buffer = []
				current_file = line.split(":", 1)[1].strip()
				collecting = False
			elif line.strip().startswith("```"):
				if not collecting:
					collecting = True
					buffer = []
				else:
					collecting = False
			elif collecting:
				buffer.append(line)
		# flush last
		if current_file and buffer:
			if self._write_file_if_target(current_file, "\n".join(buffer)):
				count += 1
		return count

	def _write_file_if_target(self, filename: str, content: str) -> bool:
		# Only write if filename matches our 4 targets
		if filename not in self.file_map:
			return False
		path = self.file_map[filename]
		# backup
		try:
			if os.path.exists(path):
				backup_path = path + ".bak"
				with open(backup_path, "w", encoding="utf-8") as b:
					b.write(read_file_safely(path))
			with open(path, "w", encoding="utf-8") as f:
				f.write(content)
			return True
		except Exception as exc:
			QtWidgets.QMessageBox.critical(self, "Write error", f"{filename}: {exc}")
			return False

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

	def on_agent_run(self) -> None:
		project_name = self.project_name_edit.text().strip()
		if not project_name:
			QtWidgets.QMessageBox.warning(self, "Agent", "Please specify project_name")
			return
		model_name = self.model_combo.currentText().strip()
		if not model_name:
			QtWidgets.QMessageBox.warning(self, "Agent", "Please select a model")
			return
		# preload
		try:
			self.client.load_model(model_name, verbose=False)
		except Exception as exc:
			QtWidgets.QMessageBox.critical(self, "Agent", f"Model load failed: {exc}")
			return
		self.agent_spinner.setText("🔄 Running...")
		self.agent_status.clear()
		user_request = self.input_line.text().strip() or "Create a simple Android app with a button and a toast."
		agent = AndroidAgent(models_dir=self.client.models_dir)

		def on_status(msg: str) -> None:
			self.agent_status.append(msg)
			self.agent_status.moveCursor(QTextCursor.End)

		outputs = agent.run_generation(
			project_name=project_name,
			system_prompt=self.system_prompt_edit.toPlainText(),
			user_request=user_request,
			max_tokens=int(self.max_tokens_spin.value()),
			temp=float(self.temp_spin.value()),
			on_status=on_status,
		)
		agent.write_outputs(project_name, outputs)
		self.agent_spinner.setText("✅ Done")
		self._on_file_selected()

	def on_agent_auto(self) -> None:
		project_name = self.project_name_edit.text().strip() or "my_project"
		base_dir = self.base_template_edit.text().strip()
		model_name = self.model_combo.currentText().strip()
		if not model_name:
			QtWidgets.QMessageBox.warning(self, "Agent", "Please select a model")
			return
		goal = (self.simple_prompt.toPlainText().strip() if self.simple_mode_checkbox.isChecked() else self.input_line.text().strip()) or "Create a simple Android app with a button and a toast."
		# preload
		try:
			self.client.load_model(model_name, verbose=False)
		except Exception as exc:
			QtWidgets.QMessageBox.critical(self, "Agent", f"Model load failed: {exc}")
			return
		self.agent_spinner.setText("🔄 Running auto pipeline...")
		self.agent_status.clear()
		self.agent_progress.setValue(0)
		agent = AndroidAgent(models_dir=self.client.models_dir)
		agent.preload_model(model_name)

		def on_status(msg: str) -> None:
			self.agent_status.append(msg)
			self.agent_status.moveCursor(QTextCursor.End)

		def on_stage_done(stage: str) -> None:
			labels = {
				"scaffold": "Copying base template",
				"plan": "Creating app plan",
				"build.gradle.kts": "Creating build settings",
				"AndroidManifest.xml": "Creating manifest",
				"activity_main.xml": "Creating app layout",
				"MainActivity.kt": "Creating main functionality",
				"qa": "Running QA checks",
			}
			text = labels.get(stage, stage)
			self.agent_status.append(f"✓ {text}")
			self.agent_status.moveCursor(QTextCursor.End)
			self._on_file_selected()
			# advance progress
			val = min(self.agent_progress.value() + 1, self.agent_progress.maximum())
			self.agent_progress.setValue(val)

		agent.run_autonomous(
			project_name=project_name,
			base_template_dir=base_dir,
			system_prompt=self.system_prompt_edit.toPlainText(),
			user_goal=goal,
			max_tokens=int(self.max_tokens_spin.value()),
			temp=float(self.temp_spin.value()),
			on_status=on_status,
			on_stage_done=on_stage_done,
		)
		self.agent_spinner.setText("✅ Done")


def main() -> None:
	# Prefer CPU-only to avoid CUDA DLL warnings on Windows
	os.environ.setdefault("GGML_NO_CUDA", "1")
	os.environ.setdefault("GGML_CUDA", "0")
	try:
		import multiprocessing
		os.environ.setdefault("GGML_NUM_THREADS", str(max(1, multiprocessing.cpu_count() - 0)))
	except Exception:
		pass
	app = QtWidgets.QApplication([])
	w = MainWindow()
	w.show()
	app.exec()


if __name__ == "__main__":
	main()