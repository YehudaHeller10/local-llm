from __future__ import annotations

import json
from typing import Dict, Optional, Iterable

from llm import GPT4AllClient


class LLMResponder:
	def __init__(self, client: GPT4AllClient) -> None:
		self.client = client

	def stream_response(self, system_prompt: str, prompt: str, *, max_tokens: int, temp: float):
		for token in self.client.generate_stream(
			prompt=self.client.build_prompt(system_prompt, [
				{"role": "user", "content": prompt}
			]),
			max_tokens=max_tokens,
			temp=temp,
		):
			yield token

	def request_json_edit(self, *, system_prompt: str, filename: str, content: str, user_request: str, max_tokens: int, temp: float) -> Optional[Dict[str, str]]:
		prompt = (
			"You will receive an Android project file. Respond ONLY with a single compact JSON object, no prose.\n"
			"Schema: {\"filename\": string, \"content\": string}. Put the full final file content in 'content'.\n"
			f"Target filename: {filename}\n\n"
			"Current file content:\n" + content + "\n\n"
			f"User request: {user_request}\n"
		)
		collected = ""
		for token in self.stream_response(system_prompt, prompt, max_tokens=max_tokens, temp=temp):
			collected += token
		try:
			start = collected.find("{")
			end = collected.rfind("}")
			if start == -1 or end == -1 or end <= start:
				return None
			obj = json.loads(collected[start : end + 1])
			if not isinstance(obj, dict):
				return None
			if "filename" in obj and "content" in obj:
				return {"filename": str(obj["filename"]), "content": str(obj["content"])}
			return None
		except Exception:
			return None