from pathlib import Path
from typing import Any
import os
import re
import yaml

class Config:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()
        self.base_dir = self.path.parent.parent if self.path.parent.name == "config" else self.path.parent
        self._load_env_file(self.base_dir / ".env")
        self.data = self._load()

    def _load_env_file(self, path: Path) -> None:
        if not path.exists():
            return

        with path.open("r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()

                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                if not key:
                    continue

                if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                    value = value[1:-1]

                if key.startswith("export "):
                    key = key[len("export "):].strip()
                    if not key:
                        continue

                # Real environment wins over .env so deploys can override files.
                os.environ.setdefault(key, value)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            raise FileNotFoundError(f"Config file not found: {self.path}")
        with self.path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return self._resolve_env_values(data)

    def _resolve_env_values(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: self._resolve_env_values(item)
                for key, item in value.items()
            }

        if isinstance(value, list):
            return [self._resolve_env_values(item) for item in value]

        if isinstance(value, str):
            return self._expand_env_string(value)

        return value

    def _expand_env_string(self, value: str) -> str:
        pattern = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-(.*?))?\}")

        def replace(match: re.Match) -> str:
            name = match.group(1)
            default = match.group(2)
            return os.environ.get(name, default if default is not None else "")

        return pattern.sub(replace, value)

    def get(self, dotted_key: str, default: Any = None) -> Any:
        current: Any = self.data
        for part in dotted_key.split('.'):
            if not isinstance(current, dict):
                return default
            current = current.get(part)
            if current is None:
                return default
        return current

    def section(self, dotted_key: str) -> dict[str, Any]:
        value = self.get(dotted_key, {})
        return value if isinstance(value, dict) else {}
