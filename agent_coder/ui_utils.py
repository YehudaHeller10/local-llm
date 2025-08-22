from typing import Dict
import textwrap

CODE_FENCE = "```"


def make_file_snippet_block(filename: str, content: str) -> str:
    # Heuristic: choose code fence based on extension for better syntax highlight
    lang = ""
    if filename.endswith(".kt"):
        lang = "kotlin"
    elif filename.endswith(".xml"):
        lang = "xml"
    elif filename.endswith(".kts"):
        lang = "kotlin"

    return f"\n### File: {filename}\n\n{CODE_FENCE}{lang}\n{content}\n{CODE_FENCE}\n"


def build_user_prompt(selected_filename: str, file_content: str, user_query: str) -> str:
    snippet = make_file_snippet_block(selected_filename, file_content)
    return textwrap.dedent(
        f"""
        Please analyze and assist with the following Android project file. Provide clear, actionable edits and explanations. Keep the response concise and use fenced code blocks for code.

        {snippet}

        User request:\n{user_query}
        """
    ).strip()