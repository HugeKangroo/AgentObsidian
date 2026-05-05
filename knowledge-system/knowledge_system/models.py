from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


SourceType = Literal["x_bookmark", "webpage", "pdf", "repo", "local_file", "manual_topic", "research_query"]


class SourceRecord(BaseModel):
    id: str
    source_type: SourceType = "x_bookmark"
    uri: str
    title: str
    author: str = ""
    priority: str = "medium"
    domain: str = ""
    value_type: list[str] = Field(default_factory=list)
    processor: str
    raw_text: str = ""
    external_links: list[str] = Field(default_factory=list)
    image_links: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source_date: str = ""
    archived_path: str = ""


class PageDraft(BaseModel):
    id: str
    title: str
    type: str
    body: str
    sources: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    status: str = "draft"
    path: str = ""


class Distillation(BaseModel):
    id: str
    source_id: str
    processor: str
    summary: str
    pages: list[PageDraft]
    claims: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)


class ReviewItem(BaseModel):
    id: str
    type: str
    source_id: str = ""
    page_id: str = ""
    message: str
    blocking: bool = True
    status: str = "pending"


class SearchHit(BaseModel):
    page_id: str
    title: str
    text: str
    score: float = 0.0


@dataclass
class FiledPage:
    page_id: str
    path: Path


@dataclass
class PipelineResult:
    project_root: Path
    source_count: int
    page_count: int
    review_count: int
    graph_edge_count: int
    reviews: list[ReviewItem]
    lint: dict[str, Any]
    graph_insights: dict[str, Any]
    search: Any
    answer_and_file_query: Any
    pending_mcp_tools: Any

