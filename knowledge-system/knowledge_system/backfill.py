from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

from .bookmarks import load_sample_sources
from .kernel import KuzuKernel
from .models import SourceRecord


@dataclass(frozen=True)
class SourceBackfillResult:
    run_id: str
    matched: int
    updated: int
    skipped: int
    artifact_path: Path
    updated_source_ids: list[str]


def backfill_source_metadata(project_root: Path, bookmarks_csv: Path) -> SourceBackfillResult:
    kernel = KuzuKernel(project_root)
    csv_sources = {source.id: source for source in load_sample_sources(bookmarks_csv)}
    matched = 0
    updated_source_ids: list[str] = []
    for source_id, csv_source in csv_sources.items():
        existing = kernel.get_source(source_id)
        if existing is None:
            continue
        matched += 1
        merged = _merge_source(existing, csv_source)
        if merged.model_dump() == existing.model_dump():
            continue
        kernel.update_source(merged)
        updated_source_ids.append(source_id)
    run_id = f"source-backfill-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    run_dir = project_root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = run_dir / "source_metadata_backfill.json"
    payload = {
        "run_id": run_id,
        "bookmarks_csv": str(bookmarks_csv),
        "matched": matched,
        "updated": len(updated_source_ids),
        "skipped": matched - len(updated_source_ids),
        "updated_source_ids": updated_source_ids,
    }
    artifact_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    kernel.close()
    return SourceBackfillResult(
        run_id=run_id,
        matched=matched,
        updated=len(updated_source_ids),
        skipped=matched - len(updated_source_ids),
        artifact_path=artifact_path,
        updated_source_ids=updated_source_ids,
    )


def _merge_source(existing: SourceRecord, csv_source: SourceRecord) -> SourceRecord:
    return SourceRecord(
        id=existing.id,
        source_type=_fill_scalar(existing.source_type, csv_source.source_type),
        uri=_fill_scalar(existing.uri, csv_source.uri),
        title=_fill_scalar(existing.title, csv_source.title),
        author=_fill_scalar(existing.author, csv_source.author),
        priority=_fill_scalar(existing.priority, csv_source.priority),
        domain=_fill_scalar(existing.domain, csv_source.domain),
        value_type=_fill_list(existing.value_type, csv_source.value_type),
        processor=_fill_scalar(existing.processor, csv_source.processor),
        raw_text=_fill_scalar(existing.raw_text, csv_source.raw_text),
        external_links=_fill_list(existing.external_links, csv_source.external_links),
        image_links=_fill_list(existing.image_links, csv_source.image_links),
        tags=_fill_list(existing.tags, csv_source.tags),
        source_date=_fill_scalar(existing.source_date, csv_source.source_date),
        archived_path=_fill_scalar(existing.archived_path, csv_source.archived_path),
    )


def _fill_scalar(existing: str, candidate: str) -> str:
    return existing if existing else candidate


def _fill_list(existing: list[str], candidate: list[str]) -> list[str]:
    return existing if existing else candidate
