from __future__ import annotations

import os
from typing import Dict, Tuple

from file_paths import (
	get_android_project_file_map,
	read_file_safely,
	scaffold_project_from_template,
	_project_root,
)
from llm_responder import LLMResponder
from llm import GPT4AllClient


class AndroidAgent:
	def __init__(self, models_dir: str) -> None:
		self.client = GPT4AllClient(models_dir=models_dir)
		self.responder = LLMResponder(self.client)

	def preload_model(self, model_name: str) -> None:
		self.client.load_model(model_name, verbose=False)

	def scaffold(self, project_name: str, base_template_dir: str) -> Tuple[bool, str, str]:
		return scaffold_project_from_template(project_name, base_template_dir)

	def run_generation(self, *, project_name: str, system_prompt: str, user_request: str, max_tokens: int, temp: float, on_status=None) -> Dict[str, str]:
		file_map = get_android_project_file_map(project_name)
		outputs: Dict[str, str] = {}

		def report(msg: str):
			if on_status:
				on_status(msg)

		for filename, path in file_map.items():
			report(f"Searching for {filename}...")
			current = read_file_safely(path)
			report(f"Generating {filename}...")
			obj = self.responder.request_json_edit(
				system_prompt=system_prompt,
				filename=filename,
				content=current,
				user_request=user_request,
				max_tokens=max_tokens,
				temp=temp,
			)
			if obj and obj.get("filename") == filename:
				outputs[filename] = obj.get("content", "")
				report(f"✓ File generation completed: {filename}")
			else:
				report(f"(Skipped) No valid JSON for {filename}")

		return outputs

	def write_outputs(self, project_name: str, outputs: Dict[str, str]) -> None:
		file_map = get_android_project_file_map(project_name)
		for filename, content in outputs.items():
			if filename not in file_map:
				continue
			path = file_map[filename]
			# backup
			if os.path.exists(path):
				with open(path + ".bak", "w", encoding="utf-8") as b:
					b.write(read_file_safely(path))
			with open(path, "w", encoding="utf-8") as f:
				f.write(content)