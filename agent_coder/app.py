import os
import time
from typing import List, Dict

import streamlit as st

from llm import GPT4AllClient
from file_paths import get_android_project_file_map, read_file_safely
from ui_utils import build_user_prompt


APP_TITLE = "Agent Coder (GPT4All)"
DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful Android coding assistant. Be concise. Provide edits in fenced code blocks."
)


@st.cache_resource
def get_client(models_dir: str) -> GPT4AllClient:
    return GPT4AllClient(models_dir=models_dir)


def render_sidebar(client: GPT4AllClient) -> Dict:
    st.sidebar.header("Settings")
    models_dir = st.sidebar.text_input("Models directory", value="./models")

    if client.models_dir != models_dir:
        client.models_dir = models_dir

    with st.sidebar.status("Scanning models directory...", expanded=False) as status:
        models = client.list_local_models()
        if models:
            status.update(label=f"Found {len(models)} model(s)", state="complete")
        else:
            status.update(label="No models found", state="error")

    model = st.sidebar.selectbox("Model (GGUF)", options=models, index=0 if models else None)

    temp = st.sidebar.slider("Temperature", min_value=0.0, max_value=1.2, value=0.2, step=0.05)
    max_tokens = st.sidebar.slider("Max tokens", min_value=128, max_value=4096, value=1024, step=64)

    system_prompt = st.sidebar.text_area("System prompt", value=DEFAULT_SYSTEM_PROMPT, height=100)

    st.sidebar.markdown("---")
    st.sidebar.caption("Files are read under /workspace/output_projects/{project_name}")

    return {
        "models_dir": models_dir,
        "model": model,
        "temp": float(temp),
        "max_tokens": int(max_tokens),
        "system_prompt": system_prompt,
    }


def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="🤖", layout="wide")
    st.title(APP_TITLE)
    st.caption("Minimal, clear UI. Streams responses. Sends selected Android file to LLM.")

    cfg = render_sidebar(get_client("./models"))
    client = get_client(cfg["models_dir"])

    col_left, col_right = st.columns([2, 1], gap="large")

    with col_right:
        st.subheader("Project")
        project_name = st.text_input("project_name", value="my_project")
        file_map = get_android_project_file_map(project_name)
        filenames: List[str] = list(file_map.keys())
        selected_filename = st.selectbox("Target file", options=filenames, index=0 if filenames else 0)

        st.write("")
        st.subheader("Preview")
        file_path = file_map.get(selected_filename, "")
        st.code(file_path, language="")
        preview_content = read_file_safely(file_path)
        st.text_area("File content (read-only)", value=preview_content, height=240, disabled=True)

    with col_left:
        st.subheader("Chat")
        if "messages" not in st.session_state:
            st.session_state.messages = []  # list of dict role/content

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_input = st.chat_input("Ask about this file or request an edit...")
        if user_input and cfg["model"]:
            # Append user message
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            # Progress indicators
            progress = st.empty()
            progress.write("🔧 Preparing prompt...")
            prompt = build_user_prompt(selected_filename, preview_content, user_input)

            progress.write("🧠 Loading model...")
            try:
                client.load_model(cfg["model"], verbose=False)
            except Exception as exc:
                with st.chat_message("assistant"):
                    st.error(f"Failed to load model: {exc}")
                return

            progress.write("🚀 Generating (streaming)...")
            assistant_placeholder = st.empty()
            streamed = ""
            with st.chat_message("assistant"):
                assistant_placeholder.markdown("⏳")
                try:
                    for token in client.generate_stream(
                        prompt=client.build_prompt(cfg["system_prompt"], [
                            {"role": "user", "content": prompt}
                        ]),
                        max_tokens=cfg["max_tokens"],
                        temp=cfg["temp"],
                    ):
                        streamed += token
                        assistant_placeholder.markdown(streamed)
                except Exception as exc:
                    assistant_placeholder.markdown(streamed)
                    st.error(f"Generation error: {exc}")

            st.session_state.messages.append({"role": "assistant", "content": streamed})
            progress.write("✅ Done")

    st.markdown("---")
    st.caption("Place your GGUF models under the selected models directory. Code blocks are fenced for clarity.")


if __name__ == "__main__":
    main()