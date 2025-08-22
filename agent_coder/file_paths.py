import os
import shutil
from typing import Dict, Tuple


def get_android_project_file_map(project_name: str, root: str = "/workspace/output_projects") -> Dict[str, str]:
	project_root = os.path.join(root, project_name)

	return {
		"MainActivity.kt": os.path.join(
			project_root,
			"app",
			"src",
			"main",
			"java",
			"com",
			"example",
			"empty_activity_android_studio_base_template",
			"MainActivity.kt",
		),
		"activity_main.xml": os.path.join(
			project_root,
			"app",
			"src",
			"main",
			"res",
			"layout",
			"activity_main.xml",
		),
		"AndroidManifest.xml": os.path.join(
			project_root,
			"app",
			"src",
			"main",
			"AndroidManifest.xml",
		),
		"build.gradle.kts": os.path.join(
			project_root,
			"app",
			"build.gradle.kts",
		),
	}


def read_file_safely(file_path: str) -> str:
	try:
		with open(file_path, "r", encoding="utf-8") as f:
			return f.read()
	except FileNotFoundError:
		return f"[File not found: {file_path}]"
	except Exception as exc:
		return f"[Error reading {file_path}: {exc}]"


def scaffold_project_from_template(
	project_name: str,
	base_template_dir: str,
	output_root: str = "/workspace/output_projects",
) -> Tuple[bool, str, str]:
	"""
	Create a new project directory by copying from base_template_dir to
	/workspace/output_projects/{project_name} if it does not already exist.
	Never modify the base template. Returns (created, dest_dir, message).
	"""
	if not os.path.isdir(base_template_dir):
		return False, "", f"Base template not found: {base_template_dir}"

	dest_dir = os.path.join(output_root, project_name)
	# Guard: never allow selecting the template dir itself as destination
	if os.path.abspath(dest_dir) == os.path.abspath(base_template_dir):
		return False, dest_dir, "Refusing to write into the base template directory. Choose a different project_name."

	if os.path.exists(dest_dir):
		return False, dest_dir, f"Project already exists at {dest_dir}. No changes made."

	parent = os.path.dirname(dest_dir)
	os.makedirs(parent, exist_ok=True)
	shutil.copytree(base_template_dir, dest_dir, dirs_exist_ok=False)
	return True, dest_dir, f"Project scaffolded at {dest_dir} from base template."