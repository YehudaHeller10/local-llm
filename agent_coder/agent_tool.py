from __future__ import annotations

import os
from typing import Dict, Tuple, Callable, Optional

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

	def run_autonomous(
		self,
		*,
		project_name: str,
		base_template_dir: str,
		system_prompt: str,
		user_goal: str,
		max_tokens: int,
		temp: float,
		on_status: Optional[Callable[[str], None]] = None,
		on_stage_done: Optional[Callable[[str], None]] = None,
	) -> None:
		"""End-to-end pipeline: scaffold -> plan -> generate 4 files with memory -> QA."""
		def report(msg: str):
			if on_status:
				on_status(msg)

		# Step 1: Scaffold
		report("Copying base template...")
		created, dest_dir, msg = scaffold_project_from_template(project_name, base_template_dir)
		report(msg)
		if on_stage_done:
			on_stage_done("scaffold")

		# Step 2: Plan (lightweight; ask for high-level app description and main features)
		plan_prompt = (
			"You will design a simple Android app in Kotlin using a single Activity and a basic layout. "
			"The user goal is: " + user_goal + ". "
			"Write a brief plan (3-5 bullet points) describing the main functionality and UI."
		)
		plan_text = ""
		for token in self.responder.stream_response(system_prompt, plan_prompt, max_tokens=min(256, max_tokens), temp=temp):
			plan_text += token
		report("Plan created.")
		if on_stage_done:
			on_stage_done("plan")

		# Step 3: Generate files with memory context
		file_map = get_android_project_file_map(project_name)
		memory: Dict[str, str] = {}
		order = [
			"build.gradle.kts",
			"AndroidManifest.xml",
			"activity_main.xml",
			"MainActivity.kt",
		]
		for filename in order:
			path = file_map[filename]
			current = read_file_safely(path)
			report(f"Generating {filename}...")
			context_hint = "\n\nContext so far (previous files):\n" + "\n".join(
				[f"{k}: {len(v)} chars" for k, v in memory.items()]
			)
			obj = self.responder.request_json_edit(
				system_prompt=system_prompt,
				filename=filename,
				content=current + context_hint + "\n\nPlan:\n" + plan_text,
				user_request=user_goal,
				max_tokens=max_tokens,
				temp=temp,
			)
			if obj and obj.get("filename") == filename:
				new_content = obj.get("content", "")
				# Write immediately and update memory
				if os.path.exists(path):
					with open(path + ".bak", "w", encoding="utf-8") as b:
						b.write(read_file_safely(path))
				with open(path, "w", encoding="utf-8") as f:
					f.write(new_content)
				memory[filename] = new_content
				report(f"✓ Wrote {filename}")
				if on_stage_done:
					on_stage_done(filename)
			else:
				report(f"(Skipped) No valid JSON for {filename}")

		# Step 4: QA checks (basic)
		report("Running QA checks...")
		qa_results = self._qa_checks(project_name)
		for k, v in qa_results.items():
			report(f"{k}: {v}")
		if on_stage_done:
			on_stage_done("qa")

	def _qa_checks(self, project_name: str) -> Dict[str, str]:
		file_map = get_android_project_file_map(project_name)
		results: Dict[str, str] = {}
		# Very light checks: file non-empty, manifest contains application/activity, layout contains root, MainActivity has onCreate
		manifest = read_file_safely(file_map["AndroidManifest.xml"]).lower()
		results["manifest_has_application"] = "yes" if "<application" in manifest else "no"
		results["manifest_has_activity"] = "yes" if "<activity" in manifest else "no"
		xml = read_file_safely(file_map["activity_main.xml"]).lower()
		results["layout_has_root"] = "yes" if xml.strip().startswith("<") else "no"
		kt = read_file_safely(file_map["MainActivity.kt"]).lower()
		results["main_has_oncreate"] = "yes" if "oncreate(" in kt else "no"
		gradle = read_file_safely(file_map["build.gradle.kts"]).lower()
		results["gradle_applies_android"] = "yes" if "com.android.application" in gradle else "no"
		return results