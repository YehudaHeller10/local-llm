from __future__ import annotations

import os
from typing import Generator, Iterable, List, Optional

from gpt4all import GPT4All


class GPT4AllClient:
    def __init__(self, models_dir: str = "./models") -> None:
        self.models_dir = models_dir
        self._model: Optional[GPT4All] = None
        self._model_name: Optional[str] = None

    def list_local_models(self) -> List[str]:
        if not os.path.isdir(self.models_dir):
            return []
        return [
            f
            for f in os.listdir(self.models_dir)
            if f.lower().endswith(".gguf") and os.path.isfile(os.path.join(self.models_dir, f))
        ]

    def load_model(self, model_filename: str, verbose: bool = False) -> None:
        model_path = os.path.join(self.models_dir, model_filename)
        if not os.path.isfile(model_path):
            raise FileNotFoundError(f"Model not found at: {model_path}")
        if self._model is not None and self._model_name == model_filename:
            return
        if self._model is not None:
            try:
                self._model.close()
            except Exception:
                pass
        self._model = GPT4All(model_name=model_path, allow_download=False, verbose=verbose)
        self._model_name = model_filename

    def build_prompt(self, system_prompt: str, messages: Iterable[dict]) -> str:
        sys = f"[SYSTEM]\n{system_prompt.strip()}\n" if system_prompt else ""
        parts: List[str] = [sys]
        for msg in messages:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            parts.append(f"[{role}]\n{content}\n")
        parts.append("[ASSISTANT]\n")
        return "\n".join(parts)

    def generate_stream(self, prompt: str, max_tokens: int = 1024, temp: float = 0.2) -> Generator[str, None, None]:
        if self._model is None:
            raise RuntimeError("Model is not loaded. Call load_model first.")
        # gpt4all supports streaming token generator when streaming=True
        for token in self._model.generate(prompt, max_tokens=max_tokens, temp=temp, streaming=True):
            yield token

    def chat_stream(self, system_prompt: str, messages: Iterable[dict], max_tokens: int = 1024, temp: float = 0.2) -> Generator[str, None, None]:
        prompt = self.build_prompt(system_prompt=system_prompt, messages=messages)
        yield from self.generate_stream(prompt=prompt, max_tokens=max_tokens, temp=temp)