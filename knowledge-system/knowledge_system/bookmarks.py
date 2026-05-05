from __future__ import annotations

import csv
import re
from pathlib import Path

from .models import SourceRecord

SAMPLE_STATUS_IDS = [
    "2051388640740401425",
    "2049534755729707205",
    "2051353318447108548",
    "2037590936234959355",
    "2051248243871498700",
    "2051119679670976760",
]


def status_id_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def split_semicolon(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def parse_notes(notes: str) -> tuple[str, list[str], list[str]]:
    raw_match = re.search(r"raw_text=(.*?); external_links=", notes, flags=re.DOTALL)
    ext_match = re.search(r"; external_links=(.*?); image_links=", notes, flags=re.DOTALL)
    img_match = re.search(r"; image_links=(.*)$", notes, flags=re.DOTALL)
    raw_text = raw_match.group(1).strip() if raw_match else ""
    external_links = split_semicolon(ext_match.group(1)) if ext_match else []
    image_links = split_semicolon(img_match.group(1)) if img_match else []
    return raw_text, external_links, image_links


def processor_for(row: dict[str, str]) -> str:
    action = row.get("next_action", "")
    domain = row.get("domain", "")
    tags = row.get("tags", "")
    if action == "expand-github-readme":
        return "repo_expander"
    if action == "extract-tool-card":
        return "tool_card_extractor"
    if action == "extract-learning-plan":
        return "learning_plan_extractor"
    if action == "save-media-context":
        return "media_context_saver"
    if action == "save-prompt-template" or "prompt" in tags or "prompt" in domain:
        return "prompt_template_extractor"
    if action == "split-resource-list":
        return "resource_list_splitter"
    return "playbook_extractor"


def load_sample_sources(bookmarks_csv: Path) -> list[SourceRecord]:
    wanted = set(SAMPLE_STATUS_IDS)
    sources: list[SourceRecord] = []
    with bookmarks_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            row_id = status_id_from_url(row["url"])
            if row_id not in wanted:
                continue
            raw_text, external_links, image_links = parse_notes(row.get("notes", ""))
            sources.append(
                SourceRecord(
                    id=f"x-{row_id}",
                    uri=row["url"],
                    title=row.get("title", "").strip() or row_id,
                    author=row.get("author", ""),
                    priority=row.get("priority", "medium"),
                    domain=row.get("domain", ""),
                    value_type=split_semicolon(row.get("value_type", "")),
                    processor=processor_for(row),
                    raw_text=raw_text,
                    external_links=external_links,
                    image_links=image_links,
                    tags=split_semicolon(row.get("tags", "")),
                    source_date=row.get("source_date", ""),
                    archived_path=row.get("archived_path", ""),
                )
            )
    order = {f"x-{sample_id}": idx for idx, sample_id in enumerate(SAMPLE_STATUS_IDS)}
    return sorted(sources, key=lambda item: order[item.id])

