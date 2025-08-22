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
		Please analyze and assist with the following Android project file. Provide clear, actionable edits.
		Respond with fenced code blocks for any updated code. If you propose a full replacement, output exactly the final content.

		{snippet}

		User request:\n{user_query}
		"""
	).strip()


def build_multi_file_prompt(filename_to_content: Dict[str, str], user_query: str) -> str:
	sections = [make_file_snippet_block(name, content) for name, content in filename_to_content.items()]
	joined = "\n".join(sections)
	return textwrap.dedent(
		f"""
		You are an Android coding assistant. The user is non-technical. Based on the following 4 project files, propose concrete edits that will make the app meet the request. Minimize changes and keep the app buildable.

		CRITICAL FORMAT FOR EDITS:
		For each file you change, output:
		File: <exact filename>
		```<language>
		<full, final content of that file>
		```
		Only include files you actually change. Do not include commentary inside code fences.

		Project files:
		{joined}

		User request:\n{user_query}
		"""
	).strip()