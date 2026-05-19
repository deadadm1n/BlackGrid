from pathlib import Path
from zipfile import ZipFile

def safe_extract_zip(zip_path: Path, target_dir: Path):
    target_dir = target_dir.resolve()
    with ZipFile(zip_path, 'r') as zip_ref:
        for member in zip_ref.infolist():
            member_path = (target_dir / member.filename).resolve()
            try:
                member_path.relative_to(target_dir)
            except ValueError:
                raise RuntimeError(f'Unsafe zip path blocked: {member.filename}')
        zip_ref.extractall(target_dir)
