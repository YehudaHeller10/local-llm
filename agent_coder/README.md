# Agent Coder (GPT4All + Streamlit + Desktop)

Minimal, clean GUI to interact with GPT4All (GGUF models), stream responses, and send Android project file contents per selected `project_name`.

## Features
- Model selection from local `models` directory
- Live token streaming with markdown rendering and code blocks
- Clear progress indicators for each step
- Simple architecture: a few Python files only
- Targets specific Android files under `/workspace/output_projects/{project_name}`
- Safe scaffolding: always works on a copy of the base template
- Desktop GUI (PySide6) and Web (Streamlit)

## Prerequisites
- Python 3.10+
- GGUF models placed in `./models` (or configure a custom models path in the UI)
- Base template directory at `/workspace/agent_coder/Empty_Activity_android_studio_base_template`

## Install
```bash
python -m pip install -r requirements.txt
```

## Run - Web (Streamlit)
```bash
streamlit run app.py
```

## Run - Desktop (PySide6)
```bash
python desktop_app.py
```
If you are using the provided virtual environment:
```bash
/workspace/agent_coder/.venv/bin/python /workspace/agent_coder/desktop_app.py
```

## Usage
1. Put your GGUF models under `./models`.
2. Enter `project_name` and keep `Base template directory` as `/workspace/agent_coder/Empty_Activity_android_studio_base_template` (or change if needed).
3. Click "Create project from base (copy)". This creates `/workspace/output_projects/{project_name}` without touching the base template.
4. Choose one of the target files. The app will read its content from:
   - `/workspace/output_projects/{project_name}/app/src/main/java/com/example/empty_activity_android_studio_base_template/MainActivity.kt`
   - `/workspace/output_projects/{project_name}/app/src/main/res/layout/activity_main.xml`
   - `/workspace/output_projects/{project_name}/app/src/main/AndroidManifest.xml`
   - `/workspace/output_projects/{project_name}/app/build.gradle.kts`
5. Type your request in the chat input. The app sends the selected file content to the LLM and streams the response.

## Notes
- The base template is never modified. New projects are copied into `/workspace/output_projects`.
- Responses are rendered as markdown (web). Desktop app displays streaming text; for formatted code blocks, copy output as needed.
- You can override the system prompt.
- This project is intentionally minimal and easy to copy to a new directory.