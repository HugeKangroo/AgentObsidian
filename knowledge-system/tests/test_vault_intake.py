from __future__ import annotations

import json
from pathlib import Path
import subprocess

import fitz

from knowledge_system.cleanup_readiness import build_cleanup_readiness, emit_cleanup_candidates
from knowledge_system.linked_evidence import (
    build_linked_evidence_status,
    capture_linked_evidence_item,
    record_linked_evidence_decision,
    resolve_linked_evidence_reviews,
)
from knowledge_system.media_annotations import record_media_annotation
from knowledge_system.search_index import vault_hybrid_search
from knowledge_system.vault_compile import compile_vault
from knowledge_system.vault_pipeline import rebuild_sample_vault, vault_intake_media, vault_intake_pdf, vault_intake_repo, vault_intake_webpage


HTML = """<html>
<head><title>Modeling With Variables</title></head>
<body>
<p>Mathematical modeling starts with variables, assumptions, constraints, and objectives.</p>
</body>
</html>
"""


def _write_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Optimization Primer\nVariables, constraints, and objectives define a model.")
    doc.save(path)
    doc.close()


def _write_repo(path: Path) -> None:
    (path / "src").mkdir(parents=True)
    (path / "README.md").write_text(
        "# Modeling Toolkit\n\nThis toolkit documents variables, assumptions, constraints, and objectives.",
        encoding="utf-8",
    )
    (path / "pyproject.toml").write_text("[project]\nname = \"modeling-toolkit\"\n", encoding="utf-8")
    (path / "src" / "modeling.py").write_text("def objective(x):\n    return x * 2\n", encoding="utf-8")


def _write_git_remote(path: Path, bare_path: Path) -> None:
    _write_repo(path)
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-c", "user.email=test@example.com", "-c", "user.name=Test", "commit", "-m", "fixture"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(["git", "clone", "--bare", str(path), str(bare_path)], check=True, capture_output=True, text=True)


def _write_png(path: Path) -> None:
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
        b"\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x01\x01\x01\x00"
        b"\x18\xdd\x8d\xb0"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def test_vault_intake_webpage_preserves_raw_and_searches(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"

    result = vault_intake_webpage(
        project_root=project_root,
        url="https://example.com/modeling",
        html=HTML,
        title="Modeling With Variables",
        tags=["math", "modeling"],
    )
    compiled = compile_vault(project_root)
    hits = vault_hybrid_search(project_root, "mathematical modeling variables", limit=2, compiled=compiled)

    assert result.source_id.startswith("web-")
    assert result.source_score["decision"] in {"integrate", "review"}
    assert result.source_score["total"] > 0
    assert (project_root / "vault" / "raw" / "webpages" / result.source_id / "raw.html").exists()
    assert (project_root / "vault" / "wiki" / "sources" / f"source-{result.source_id}.md").exists()
    assert hits
    assert hits[0].page_id == result.primary_page_id


def test_vault_intake_pdf_and_repo_preserve_raw(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    pdf_path = tmp_path / "fixture.pdf"
    repo_path = tmp_path / "repo"
    _write_pdf(pdf_path)
    _write_repo(repo_path)

    pdf = vault_intake_pdf(project_root=project_root, path=pdf_path, title="Optimization Primer", tags=["math"])
    repo = vault_intake_repo(project_root=project_root, path=repo_path, title="", tags=["modeling"])
    compiled = compile_vault(project_root)
    pdf_manifest = json.loads(pdf.raw_manifest_path.read_text(encoding="utf-8"))
    repo_manifest = json.loads(repo.raw_manifest_path.read_text(encoding="utf-8"))

    assert (project_root / "vault" / "raw" / "pdfs" / pdf.source_id / "raw.pdf").exists()
    assert (project_root / "vault" / "raw" / "repos" / repo.source_id / "capture.json").exists()
    assert pdf_manifest["source_card_path"].endswith(f"source-{pdf.source_id}.md")
    assert repo_manifest["source_card_path"].endswith(f"source-{repo.source_id}.md")
    assert pdf.primary_page_id in compiled.pages_by_id
    assert repo.primary_page_id in compiled.pages_by_id


def test_vault_intake_media_preserves_raw_asset_and_review_blocker(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    media_path = tmp_path / "diagram.png"
    _write_png(media_path)

    result = vault_intake_media(
        project_root=project_root,
        path=media_path,
        title="Modeling Diagram",
        uri="https://example.com/diagram.png",
        tags=["math", "modeling"],
    )
    compiled = compile_vault(project_root)
    manifest = json.loads(result.raw_manifest_path.read_text(encoding="utf-8"))
    page = compiled.pages_by_id[result.primary_page_id]

    assert result.source_id.startswith("media-")
    assert (project_root / "vault" / "raw" / "media" / result.source_id / "asset.png").exists()
    assert manifest["raw_path"].endswith("/asset.png")
    assert manifest["source_card_path"].endswith(f"source-{result.source_id}.md")
    assert "![Raw media evidence]" in page.body
    assert any(review.source_id == result.source_id for review in compiled.reviews)
    assert not [issue for issue in compiled.lint_issues if issue.page_id == result.primary_page_id]


def test_media_annotation_records_caption_and_resolves_review_blocker(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    media_path = tmp_path / "diagram.png"
    _write_png(media_path)
    media = vault_intake_media(
        project_root=project_root,
        path=media_path,
        title="Modeling Diagram",
        uri="https://example.com/diagram.png",
        tags=["math", "modeling"],
    )

    annotation = record_media_annotation(
        project_root=project_root,
        source_id=media.source_id,
        caption="A small diagram showing variables feeding an objective under constraints.",
        observations="The visual is useful as modeling evidence, but it does not prove a numeric result.",
        method="agent_caption",
        reviewer="codex",
        confidence=0.72,
    )
    compiled = compile_vault(project_root)
    page = compiled.pages_by_id[annotation.annotation_page_id]
    source_reviews = [review for review in compiled.reviews if review.source_id == media.source_id]

    assert annotation.resolved_review_count == 1
    assert annotation.path.exists()
    assert "variables feeding an objective" in page.body
    assert "[[Modeling Diagram]]" in page.body
    assert all(review.status == "resolved" for review in source_reviews)
    assert all(not review.blocking for review in source_reviews)
    assert not [issue for issue in compiled.lint_issues if issue.page_id == annotation.annotation_page_id]


def test_capture_linked_webpage_evidence_preserves_raw_and_parent_context(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    queue = json.loads((project_root / "vault" / "generated" / "linked_evidence_queue.json").read_text(encoding="utf-8"))
    item = next(item for item in queue["items"] if item["kind"] == "external_link" and "langchain" in item["uri"])

    result = capture_linked_evidence_item(
        project_root=project_root,
        item_id=item["id"],
        html=(
            "<html><head><title>Agent Evaluation Readiness Checklist</title></head>"
            "<body>agent evaluation readiness regression evals traces "
            "agent evaluation readiness regression evals traces</body></html>"
        ),
    )
    payload = json.loads(result.path.read_text(encoding="utf-8"))
    compiled = compile_vault(project_root)
    hits = vault_hybrid_search(
        project_root=project_root,
        query="agent evaluation readiness regression evals traces",
        limit=3,
        compiled=compiled,
    )

    assert result.status == "captured"
    assert result.classification == "webpage"
    assert result.linked_source_id.startswith("web-")
    assert result.raw_manifest_path
    assert (project_root / result.raw_manifest_path).exists()
    assert payload["parent_source_id"] == "x-2037590936234959355"
    assert payload["queue_item_id"] == item["id"]
    assert "linked-evidence" in compiled.pages_by_id[f"source-{result.linked_source_id}"].tags
    assert hits[0].page_id == "learning-plan-agent-evaluation-readiness"


def test_capture_linked_media_evidence_records_unsupported_result(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    queue = json.loads((project_root / "vault" / "generated" / "linked_evidence_queue.json").read_text(encoding="utf-8"))
    item = next(item for item in queue["items"] if item["kind"] == "media_link")

    result = capture_linked_evidence_item(project_root=project_root, item_id=item["id"])
    payload = json.loads(result.path.read_text(encoding="utf-8"))

    assert result.status == "unsupported"
    assert result.classification == "media"
    assert result.raw_manifest_path == ""
    assert payload["reason"] == "Media capture requires an explicit local media file path or download_media=True before raw evidence can be preserved."


def test_capture_linked_repo_evidence_records_unsupported_result(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    queue = json.loads((project_root / "vault" / "generated" / "linked_evidence_queue.json").read_text(encoding="utf-8"))
    item = next(item for item in queue["items"] if item["kind"] == "external_link" and "github.com" in item["uri"])

    result = capture_linked_evidence_item(project_root=project_root, item_id=item["id"])
    payload = json.loads(result.path.read_text(encoding="utf-8"))

    assert result.status == "unsupported"
    assert result.classification == "repo"
    assert result.raw_manifest_path == ""
    assert payload["reason"] == "Remote repository capture requires an explicit local clone path or clone_repo=True before repo intake."


def test_capture_linked_repo_evidence_with_clone_preserves_raw_capture(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    repo_path = tmp_path / "repo"
    bare_path = tmp_path / "remote.git"
    _write_git_remote(repo_path, bare_path)
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    queue_path = project_root / "vault" / "generated" / "linked_evidence_queue.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    item = next(item for item in queue["items"] if item["kind"] == "external_link" and "github.com" in item["uri"])
    item["uri"] = bare_path.as_uri()
    queue_path.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")

    result = capture_linked_evidence_item(project_root=project_root, item_id=item["id"], clone_repo=True)
    payload = json.loads(result.path.read_text(encoding="utf-8"))
    manifest = json.loads((project_root / result.raw_manifest_path).read_text(encoding="utf-8"))
    compiled = compile_vault(project_root)

    assert result.status == "captured"
    assert result.classification == "repo"
    assert result.linked_source_id.startswith("repo-")
    assert payload["reason"].startswith("Linked repository evidence cloned")
    assert manifest["uri"] == bare_path.as_uri()
    assert (project_root / manifest["raw_path"]).exists()
    assert result.primary_page_id in compiled.pages_by_id


def test_capture_linked_media_evidence_with_local_file_preserves_raw_asset(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    media_path = tmp_path / "linked-diagram.png"
    _write_png(media_path)
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    queue = json.loads((project_root / "vault" / "generated" / "linked_evidence_queue.json").read_text(encoding="utf-8"))
    item = next(item for item in queue["items"] if item["kind"] == "media_link")

    result = capture_linked_evidence_item(project_root=project_root, item_id=item["id"], media_path=media_path)
    status = build_linked_evidence_status(project_root=project_root)
    status_payload = json.loads(status.path.read_text(encoding="utf-8"))
    status_item = next(entry for entry in status_payload["items"] if entry["id"] == item["id"])
    compiled = compile_vault(project_root)

    assert result.status == "captured"
    assert result.classification == "media"
    assert result.linked_source_id.startswith("media-")
    assert (project_root / result.raw_manifest_path).exists()
    assert status_item["status"] == "captured"
    assert status_item["raw_manifest_path"] == result.raw_manifest_path
    assert result.primary_page_id in compiled.pages_by_id
    assert any(review.source_id == result.linked_source_id for review in compiled.reviews)


def test_capture_linked_media_evidence_with_download_preserves_raw_asset(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    media_path = tmp_path / "remote-diagram.png"
    _write_png(media_path)
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    queue_path = project_root / "vault" / "generated" / "linked_evidence_queue.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    item = next(item for item in queue["items"] if item["kind"] == "media_link")
    item["uri"] = media_path.as_uri()
    queue_path.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")

    result = capture_linked_evidence_item(project_root=project_root, item_id=item["id"], download_media=True)
    payload = json.loads(result.path.read_text(encoding="utf-8"))
    manifest = json.loads((project_root / result.raw_manifest_path).read_text(encoding="utf-8"))

    assert result.status == "captured"
    assert result.classification == "media"
    assert result.linked_source_id.startswith("media-")
    assert payload["reason"].startswith("Linked media raw asset downloaded")
    assert manifest["uri"] == media_path.as_uri()
    assert (project_root / manifest["raw_path"]).exists()


def test_linked_evidence_status_merges_queue_and_capture_results(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    queue = json.loads((project_root / "vault" / "generated" / "linked_evidence_queue.json").read_text(encoding="utf-8"))
    webpage_item = next(item for item in queue["items"] if item["kind"] == "external_link" and "langchain" in item["uri"])
    media_item = next(item for item in queue["items"] if item["kind"] == "media_link")
    capture_linked_evidence_item(project_root=project_root, item_id=webpage_item["id"], html=HTML)
    capture_linked_evidence_item(project_root=project_root, item_id=media_item["id"])

    status = build_linked_evidence_status(project_root=project_root)
    payload = json.loads(status.path.read_text(encoding="utf-8"))
    items_by_id = {item["id"]: item for item in payload["items"]}

    assert status.total_count == 7
    assert status.captured_count == 1
    assert status.unsupported_count == 1
    assert status.pending_count == 5
    assert items_by_id[webpage_item["id"]]["status"] == "captured"
    assert items_by_id[webpage_item["id"]]["raw_manifest_path"]
    assert items_by_id[media_item["id"]]["status"] == "unsupported"
    assert items_by_id[media_item["id"]]["capture_result_path"]


def test_linked_evidence_decision_records_auditable_status(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    queue = json.loads((project_root / "vault" / "generated" / "linked_evidence_queue.json").read_text(encoding="utf-8"))
    item = next(item for item in queue["items"] if item["kind"] == "media_link")

    decision = record_linked_evidence_decision(
        project_root=project_root,
        item_id=item["id"],
        decision="nonessential",
        rationale="This fixture media item does not add reusable knowledge beyond the source text.",
        reviewer="codex",
    )
    status = build_linked_evidence_status(project_root=project_root)
    status_payload = json.loads(status.path.read_text(encoding="utf-8"))
    status_item = next(entry for entry in status_payload["items"] if entry["id"] == item["id"])
    compiled = compile_vault(project_root)

    assert decision.path.exists()
    assert decision.decision == "nonessential"
    assert status.decision_count == 1
    assert status_item["decision"] == "nonessential"
    assert status_item["decision_reviewer"] == "codex"
    assert status_item["decision_path"].endswith(".md")
    assert any(review.type == "linked_evidence_decision" for review in compiled.reviews)


def test_resolve_linked_evidence_reviews_closes_parent_blockers_after_decisions(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    media_path = tmp_path / "linked-diagram.png"
    _write_png(media_path)
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    queue = json.loads((project_root / "vault" / "generated" / "linked_evidence_queue.json").read_text(encoding="utf-8"))
    webpage_item = next(item for item in queue["items"] if item["source_id"] == "x-2037590936234959355" and item["kind"] == "external_link")
    media_item = next(item for item in queue["items"] if item["source_id"] == "x-2037590936234959355" and item["kind"] == "media_link")
    video_item = next(item for item in queue["items"] if item["source_id"] == "x-2051119679670976760")

    capture_linked_evidence_item(project_root=project_root, item_id=webpage_item["id"], html=HTML)
    capture_linked_evidence_item(project_root=project_root, item_id=media_item["id"], media_path=media_path)
    capture_linked_evidence_item(project_root=project_root, item_id=video_item["id"], html="<html><body>X video shell</body></html>")
    record_linked_evidence_decision(
        project_root=project_root,
        item_id=webpage_item["id"],
        decision="reviewed",
        rationale="Fixture webpage evidence was captured and reviewed.",
        reviewer="codex",
    )
    record_linked_evidence_decision(
        project_root=project_root,
        item_id=media_item["id"],
        decision="reviewed",
        rationale="Fixture media evidence was captured and reviewed.",
        reviewer="codex",
    )
    record_linked_evidence_decision(
        project_root=project_root,
        item_id=video_item["id"],
        decision="needs_followup",
        rationale="The fixture video shell does not preserve transcript evidence.",
        reviewer="codex",
    )

    result = resolve_linked_evidence_reviews(project_root=project_root, reviewer="codex")
    compiled = compile_vault(project_root)
    reviews = {review.id: review for review in compiled.reviews}

    assert result.resolved_count == 2
    assert reviews["review-x-2037590936234959355-1"].status == "resolved"
    assert reviews["review-x-2037590936234959355-1"].blocking is False
    assert reviews["review-x-2037590936234959355-2"].status == "resolved"
    assert reviews["review-x-2051119679670976760-1"].status == "pending"
    assert reviews["review-x-2051119679670976760-1"].blocking is True


def test_cleanup_readiness_blocks_sources_with_unresolved_evidence(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)

    result = build_cleanup_readiness(project_root=project_root)
    payload = json.loads(result.path.read_text(encoding="utf-8"))
    blocked_x_sources = [
        source for source in payload["sources"] if source["source_type"] == "x_bookmark" and not source["ready_for_cleanup_signal"]
    ]

    assert result.source_count >= 6
    assert result.ready_count + result.blocked_count == result.source_count
    assert result.blocked_count >= 1
    assert blocked_x_sources
    assert any("Linked evidence" in blocker or "Pending blocking review" in blocker for source in blocked_x_sources for blocker in source["blockers"])


def test_cleanup_candidates_emit_non_destructive_review_signals(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)

    result = emit_cleanup_candidates(project_root=project_root, reviewer="codex")
    payload = json.loads(result.path.read_text(encoding="utf-8"))
    compiled = compile_vault(project_root)

    assert result.candidate_count >= 1
    assert payload["candidate_count"] == result.candidate_count
    assert all((project_root / item["path"]).exists() for item in payload["candidates"])
    assert any(review.type == "deletion_candidate" and not review.blocking for review in compiled.reviews)
