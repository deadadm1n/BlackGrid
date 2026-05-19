from pathlib import Path
import shutil

import yaml


def load_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Patch file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def patch_properties(file_path: Path, values: dict, logger=None):
    lines = []
    seen = set()

    if file_path.exists():
        original_lines = file_path.read_text(encoding="utf-8").splitlines()
    else:
        original_lines = []

    for line in original_lines:
        stripped = line.strip()

        if not stripped or stripped.startswith("#") or "=" not in line:
            lines.append(line)
            continue

        key, _value = line.split("=", 1)
        key = key.strip()

        if key in values:
            lines.append(f"{key}={values[key]}")
            seen.add(key)
        else:
            lines.append(line)

    for key, value in values.items():
        if key not in seen:
            lines.append(f"{key}={value}")

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if logger:
        logger.info("[Patcher] Patched properties: %s", file_path)


def replace_file(server_dir: Path, patch_dir: Path, target_file: str, source_file: str, logger=None):
    src = patch_dir / source_file
    dst = server_dir / target_file

    if not src.exists():
        raise FileNotFoundError(f"Replacement source not found: {src}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

    if logger:
        logger.info("[Patcher] Replaced file: %s <- %s", dst, src)


def replace_text_file(file_path: Path, content: str, logger=None):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content.rstrip() + "\n", encoding="utf-8")

    if logger:
        logger.info("[Patcher] Replaced text file: %s", file_path)


def text_replace(file_path: Path, replacements: list[dict], logger=None):
    if not file_path.exists():
        raise FileNotFoundError(f"Cannot text_replace missing file: {file_path}")

    text = file_path.read_text(encoding="utf-8")

    for replacement in replacements:
        find = replacement["find"]
        new = replacement["with"]

        if find not in text:
            raise RuntimeError(f"Text not found in {file_path}: {find}")

        text = text.replace(find, new)

    file_path.write_text(text, encoding="utf-8")

    if logger:
        logger.info("[Patcher] Applied text replacements: %s", file_path)


def apply_patches(server_dir: Path, patch_yaml: Path, logger=None):
    data = load_yaml(patch_yaml)
    patch_dir = patch_yaml.parent
    patches = data.get("patches", [])

    if logger:
        logger.info("[Patcher] Applying %s patches from %s", len(patches), patch_yaml)

    for patch in patches:
        patch_type = patch["type"]
        target = server_dir / patch["file"]

        if patch_type == "properties":
            patch_properties(target, patch.get("set", {}), logger=logger)

        elif patch_type == "replace_file":
            replace_file(server_dir, patch_dir, patch["file"], patch["source"], logger=logger)

        elif patch_type == "replace_text_file":
            replace_text_file(target, patch["content"], logger=logger)

        elif patch_type == "text_replace":
            text_replace(target, patch.get("replace", []), logger=logger)

        else:
            raise ValueError(f"Unknown patch type: {patch_type}")
