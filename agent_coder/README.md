# Agent Coder (GPT4All + Desktop)

Minimal, clean Desktop GUI (PySide6) to interact with GPT4All (GGUF models), stream responses, and send Android project file contents per selected `project_name`.

## Features
- Model selection from local `models` directory
- Model preload on startup/selection to reduce first-token latency
- Lite mode (single-file prompt) for faster responses
- Live token streaming with clear progress indicators
- Simple architecture: a few Python files only
- Targets specific Android files under `<project_root>/output_projects/{project_name}`
- Safe scaffolding: always works on a copy of the base template

## Prerequisites
- Python 3.10+
- GGUF models placed in `./models`
- Base template directory at `<project_root>/Empty_Activity_android_studio_base_template`

## Install
```bash
python -m pip install -r requirements.txt
```

## Run - Desktop (PySide6)
```bash
python desktop_app.py
```
If using the provided Linux venv:
```bash
/workspace/agent_coder/.venv/bin/python /workspace/agent_coder/desktop_app.py
```

## Usage
1. Put your GGUF models under `./models`.
2. Enter `project_name`. Ensure the `Base template directory` points to `<project_root>/Empty_Activity_android_studio_base_template`.
3. Click "Create project from base (copy)". This creates `<project_root>/output_projects/{project_name}` without touching the base template.
4. Choose one of the target files. The app will read its content from:
   - `<project_root>/output_projects/{project_name}/app/src/main/java/com/example/empty_activity_android_studio_base_template/MainActivity.kt`
   - `<project_root>/output_projects/{project_name}/app/src/main/res/layout/activity_main.xml`
   - `<project_root>/output_projects/{project_name}/app/src/main/AndroidManifest.xml`
   - `<project_root>/output_projects/{project_name}/app/build.gradle.kts`
5. For faster first token: leave "Lite mode" checked (single-file prompt) and rely on "Include all 4 files" only when necessary.
6. Type your request and click Send. The app streams the response into the chat area.
7. Click "Apply Edits from last response" to write updates (with `.bak` backups) to the project files.

## Tips for performance
- Use smaller GGUF (e.g., q4_k_m). Keep models on a fast local drive.
- Environment (Windows PowerShell):
  - `$env:GGML_NUM_THREADS = [Environment]::ProcessorCount`
  - `$env:GGML_NO_CUDA = 1; $env:GGML_CUDA = 0`
- Keep `models` and `output_projects` on the same fast disk.