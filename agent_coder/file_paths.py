import os
from typing import Dict


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