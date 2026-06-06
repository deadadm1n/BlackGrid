#!/usr/bin/env python3
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html import unescape
from pathlib import Path


ATM11_FILES_URL = "https://www.curseforge.com/minecraft/modpacks/all-the-mods-11/files/all"
ATM11_PROJECT_ID = 1148445
DEFAULT_MANIFEST = Path("configs/atm11-serverfiles.json")


class ManifestUpdateError(RuntimeError):
    pass


def reader_url(url):
    return "https://r.jina.ai/http://" + url


def candidate_source_urls(url, use_reader=True):
    if use_reader:
        yield reader_url(url)

    yield url


def fetch_text(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0 Safari/537.36 BlackGridManifestUpdater/1.0"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise ManifestUpdateError(f"CurseForge returned HTTP {e.code}") from e
    except urllib.error.URLError as e:
        raise ManifestUpdateError(f"Could not reach CurseForge: {e.reason}") from e


def strip_html(text):
    text = re.sub(r"<script\b.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def safe_zip_name(title):
    cleaned = re.sub(r"[^A-Za-z0-9.\-_]+", "-", title).strip("-")

    if not cleaned:
        cleaned = "ServerFiles"

    if not cleaned.lower().endswith(".zip"):
        cleaned += ".zip"

    return cleaned


def extract_serverfiles_title(text, file_id):
    text = text.replace("*", "")
    patterns = [
        r"(ServerFiles[-_ ]?[0-9][A-Za-z0-9.\-_]*(?:\.zip)?(?:\s+Latest\s+release\s+R\s+[A-Za-z0-9., _-]+)?)",
        r"(Server Files[-_ ]?[0-9][A-Za-z0-9.\-_]*(?:\.zip)?(?:\s+Latest\s+release\s+R\s+[A-Za-z0-9., _-]+)?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            title = match.group(1).strip(" -|")
            return re.sub(r"\s+", " ", title)

    return f"ServerFiles-{file_id}"


def extract_pack_version(title):
    match = re.search(
        r"(?:ServerFiles|Server Files)[-_ ]?([0-9]+(?:\.[0-9]+)+)",
        title,
        re.IGNORECASE,
    )

    if match:
        return match.group(1)

    return None


def parse_latest_serverfiles(html):
    candidates = []
    seen = set()

    link_pattern = re.compile(
        r'href="(?P<href>/minecraft/modpacks/all-the-mods-11/files/(?P<file_id>\d+))"[^>]*>(?P<title>.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )

    for match in link_pattern.finditer(html):
        file_id = int(match.group("file_id"))

        if file_id in seen:
            continue

        title = strip_html(match.group("title"))

        if "serverfiles" not in title.lower() and "server files" not in title.lower():
            continue

        seen.add(file_id)
        candidates.append(build_candidate(file_id, title))

    loose_pattern = re.compile(
        r"/minecraft/modpacks/all-the-mods-11/files/(?P<file_id>\d+)",
        re.IGNORECASE,
    )

    for match in loose_pattern.finditer(html):
        file_id = int(match.group("file_id"))

        if file_id in seen:
            continue

        start = max(match.start() - 700, 0)
        end = min(match.end() + 1400, len(html))
        chunk_text = strip_html(html[start:end])

        if "serverfiles" not in chunk_text.lower() and "server files" not in chunk_text.lower():
            continue

        seen.add(file_id)
        candidates.append(build_candidate(file_id, extract_serverfiles_title(chunk_text, file_id)))

    if not candidates:
        raise ManifestUpdateError("Could not find an ATM11 ServerFiles entry on the CurseForge files page")

    candidates.sort(key=lambda item: item["file_id"], reverse=True)
    latest = candidates[0]
    attach_matching_pack_file(html, latest)
    return latest


def build_candidate(file_id, display_name):
    page_url = f"https://www.curseforge.com/minecraft/modpacks/all-the-mods-11/files/{file_id}"
    return {
        "file_id": file_id,
        "display_name": display_name,
        "file_name": safe_zip_name(display_name),
        "page_url": page_url,
        "download_url": f"https://www.curseforge.com/api/v1/mods/{ATM11_PROJECT_ID}/files/{file_id}/download",
    }


def attach_matching_pack_file(html, latest):
    pack_version = extract_pack_version(latest["display_name"])

    if not pack_version:
        return

    pattern = re.compile(
        r"\[All the Mods 11-" + re.escape(pack_version) + r"(?P<title>[^\]]*)\]"
        r"\(https://www\.curseforge\.com/minecraft/modpacks/all-the-mods-11/files/(?P<file_id>\d+)\)",
        re.IGNORECASE,
    )

    for match in pattern.finditer(html):
        file_id = int(match.group("file_id"))

        if file_id == int(latest["file_id"]):
            continue

        latest["changelog_file_id"] = file_id
        latest["changelog_url"] = (
            f"https://www.curseforge.com/minecraft/modpacks/all-the-mods-11/files/{file_id}/changelog"
        )
        return


def extract_changelog(markdown):
    marker = re.search(
        r"\*\s+\[Related Projects\]\([^)]+\)\s*(?P<body>.*?)"
        r"(?:\n\[!\[Image|\nCurseForge -|\nWe use cookies|\Z)",
        markdown,
        re.IGNORECASE | re.DOTALL,
    )

    if not marker:
        if "File has no changelog" in markdown:
            return ""

        return ""

    body = marker.group("body").strip()

    if "File has no changelog" in body:
        return ""

    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def attach_changelog(latest, use_reader=True):
    changelog_url = latest.get("changelog_url")

    if not changelog_url:
        return

    for source_url in candidate_source_urls(changelog_url, use_reader=use_reader):
        try:
            changelog = extract_changelog(fetch_text(source_url))
        except ManifestUpdateError:
            continue

        latest["changelog_source_url"] = source_url

        if changelog:
            latest["changelog"] = changelog

        return


def read_manifest(path):
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, dict):
        raise ManifestUpdateError(f"Manifest must be a JSON object: {path}")

    return data


def current_file_id(manifest):
    data = manifest.get("atm11_serverfiles", manifest)

    if not isinstance(data, dict):
        return 0

    value = data.get("file_id")

    if value in (None, ""):
        return 0

    try:
        return int(value)
    except (TypeError, ValueError):
        raise ManifestUpdateError("Manifest file_id must be numeric")


def write_manifest(path, latest, previous_id):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "atm11_serverfiles": {
            "file_id": latest["file_id"],
            "display_name": latest["display_name"],
            "page_url": latest["page_url"],
            "download_url": latest["download_url"],
            "discovered_at": datetime.now(timezone.utc).isoformat(),
            "previous_file_id": previous_id or None,
            "source": "curseforge_files_page",
            "metadata_source_url": latest.get("metadata_source_url"),
            "changelog_file_id": latest.get("changelog_file_id"),
            "changelog_url": latest.get("changelog_url"),
            "changelog_source_url": latest.get("changelog_source_url"),
            "changelog": latest.get("changelog"),
        }
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Update the ATM11 ServerFiles manifest from CurseForge.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Manifest JSON path to update.")
    parser.add_argument("--url", default=ATM11_FILES_URL, help="CurseForge files page to read.")
    parser.add_argument("--no-reader", action="store_true", help="Skip the public text-reader source and fetch CurseForge directly.")
    parser.add_argument("--force", action="store_true", help="Rewrite the manifest even if the file id is unchanged.")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    manifest = read_manifest(manifest_path)
    previous_id = current_file_id(manifest)
    latest = None
    errors = []

    for source_url in candidate_source_urls(args.url, use_reader=not args.no_reader):
        try:
            latest = parse_latest_serverfiles(fetch_text(source_url))
            latest["metadata_source_url"] = source_url
            break
        except ManifestUpdateError as e:
            errors.append(f"{source_url}: {e}")

    if latest is None:
        raise ManifestUpdateError("Could not discover ATM11 ServerFiles. " + " | ".join(errors))

    attach_changelog(latest, use_reader=not args.no_reader)

    if latest["file_id"] < previous_id:
        raise ManifestUpdateError(
            f"Detected file id {latest['file_id']} is older than manifest file id {previous_id}"
        )

    if latest["file_id"] == previous_id and not args.force:
        print(f"ATM11 ServerFiles manifest is current: {latest['display_name']} ({latest['file_id']})")
        return 0

    write_manifest(manifest_path, latest, previous_id)
    print(f"Updated ATM11 ServerFiles manifest: {previous_id or 'none'} -> {latest['file_id']}")
    print(latest["display_name"])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ManifestUpdateError as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(1)
