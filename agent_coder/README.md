# Agent Coder (GPT4All + Streamlit)

Minimal, clean GUI to interact with GPT4All (GGUF models), stream responses, and send Android project file contents per selected `project_name`.

## Features
- Model selection from local `models` directory
- Live token streaming with markdown rendering and code blocks
- Clear progress indicators for each step
- Simple architecture: a few Python files only
- Targets specific Android files under `/workspace/output_projects/{project_name}`

## Prerequisites
- Python 3.10+
- GGUF models placed in `./models` (or configure a custom models path in the UI)

## Install
```bash
python -m pip install -r requirements.txt
```

## Run
```bash
streamlit run app.py
```

## Usage
1. Put your GGUF models under `./models`.
2. Open the app, select a model, enter `project_name`.
3. Choose one of the target files. The app will read its content from:
   - `/workspace/output_projects/{project_name}/app/src/main/java/com/example/empty_activity_android_studio_base_template/MainActivity.kt`
   - `/workspace/output_projects/{project_name}/app/src/main/res/layout/activity_main.xml`
   - `/workspace/output_projects/{project_name}/app/src/main/AndroidManifest.xml`
   - `/workspace/output_projects/{project_name}/app/build.gradle.kts`
4. Type your request in the chat input. The app sends the selected file content to the LLM and streams the response.

## Notes
- Responses are rendered as markdown. Code is shown in fenced code blocks.
- You can override the system prompt in the sidebar.
- This project is intentionally minimal and easy to copy to a new directory.