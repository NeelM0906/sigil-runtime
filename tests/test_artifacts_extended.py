"""Tests for extended artifact store and generators."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from bomba_sr.artifacts.store import (
    ArtifactRecord,
    ArtifactStore,
    ARTIFACT_TYPES,
    get_artifact_type_info,
    register_artifact_type,
)
from bomba_sr.artifacts.generators import generate_pdf, generate_docx
from bomba_sr.storage.db import RuntimeDB


@pytest.fixture()
def db():
    _db = RuntimeDB(":memory:")
    yield _db
    _db.close()


@pytest.fixture()
def store(db, tmp_path):
    return ArtifactStore(db, tmp_path / "artifacts")


# ── Type registry ────────────────────────────────────────────

class TestArtifactTypeRegistry:
    def test_builtin_types(self):
        assert "pdf" in ARTIFACT_TYPES
        assert "docx" in ARTIFACT_TYPES
        assert "image" in ARTIFACT_TYPES
        assert "markdown" in ARTIFACT_TYPES
        assert "code" in ARTIFACT_TYPES
        assert "html" in ARTIFACT_TYPES
        assert "csv" in ARTIFACT_TYPES
        assert "json" in ARTIFACT_TYPES
        assert "svg" in ARTIFACT_TYPES

    def test_get_type_info(self):
        ext, mime, is_bin = get_artifact_type_info("pdf")
        assert ext == ".pdf"
        assert mime == "application/pdf"
        assert is_bin is True

    def test_get_unknown_type(self):
        ext, mime, is_bin = get_artifact_type_info("unknown_format")
        assert ext == ".bin"
        assert is_bin is True

    def test_register_custom_type(self):
        register_artifact_type("xlsx", ".xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", True)
        ext, mime, is_bin = get_artifact_type_info("xlsx")
        assert ext == ".xlsx"
        assert is_bin is True
        # Cleanup
        ARTIFACT_TYPES.pop("xlsx", None)


# ── Text artifacts ───────────────────────────────────────────

class TestTextArtifacts:
    def test_create_markdown(self, store):
        rec = store.create_text_artifact(
            tenant_id="t1", session_id="s1", turn_id="turn1",
            project_id="p1", task_id="task1",
            artifact_type="markdown", title="Test Doc",
            content="# Hello\n\nWorld",
        )
        assert rec.artifact_type == "markdown"
        assert rec.mime_type == "text/markdown"
        assert rec.file_size > 0
        assert Path(rec.path).exists()

    def test_create_code(self, store):
        rec = store.create_text_artifact(
            tenant_id="t1", session_id="s1", turn_id="turn1",
            project_id=None, task_id=None,
            artifact_type="code", title="Script",
            content="print('hello')",
        )
        assert rec.artifact_type == "code"
        assert rec.file_size > 0

    def test_create_with_metadata(self, store):
        rec = store.create_text_artifact(
            tenant_id="t1", session_id="s1", turn_id="turn1",
            project_id="p1", task_id="task1",
            artifact_type="markdown", title="Doc",
            content="content",
            created_by="sai-memory",
            skill_id="docx-generator",
        )
        assert rec.created_by == "sai-memory"
        assert rec.skill_id == "docx-generator"


# ── Binary artifacts ─────────────────────────────────────────

class TestBinaryArtifacts:
    def test_create_binary(self, store):
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        rec = store.create_binary_artifact(
            tenant_id="t1", session_id="s1", turn_id="turn1",
            project_id="p1", task_id="task1",
            artifact_type="image", title="Screenshot",
            data=data,
        )
        assert rec.artifact_type == "image"
        assert rec.mime_type == "image/png"
        assert rec.file_size == len(data)
        assert Path(rec.path).exists()
        assert Path(rec.path).read_bytes() == data

    def test_create_binary_with_filename(self, store):
        data = b"%PDF-1.4 test content"
        rec = store.create_binary_artifact(
            tenant_id="t1", session_id="s1", turn_id="turn1",
            project_id=None, task_id=None,
            artifact_type="pdf", title="Report",
            data=data, filename="report.pdf",
        )
        assert rec.path.endswith("report.pdf")


# ── File artifacts ───────────────────────────────────────────

class TestFileArtifacts:
    def test_register_existing_file(self, store, tmp_path):
        src = tmp_path / "existing.html"
        src.write_text("<h1>Hello</h1>", encoding="utf-8")

        rec = store.create_file_artifact(
            tenant_id="t1", session_id="s1", turn_id="turn1",
            project_id="p1", task_id="task1",
            artifact_type="html", title="Page",
            source_path=str(src),
        )
        assert rec.artifact_type == "html"
        assert rec.file_size > 0
        assert "Hello" in rec.preview

    def test_register_missing_file(self, store):
        with pytest.raises(FileNotFoundError):
            store.create_file_artifact(
                tenant_id="t1", session_id="s1", turn_id="turn1",
                project_id=None, task_id=None,
                artifact_type="code", title="Missing",
                source_path="/nonexistent/file.py",
            )


# ── Query ────────────────────────────────────────────────────

class TestArtifactQuery:
    def test_list_task_artifacts(self, store):
        store.create_text_artifact(
            "t1", "s1", "turn1", "p1", "task-A",
            "markdown", "Doc 1", "content 1",
        )
        store.create_text_artifact(
            "t1", "s1", "turn2", "p1", "task-A",
            "code", "Script", "print(1)",
        )
        store.create_text_artifact(
            "t1", "s2", "turn1", "p1", "task-B",
            "markdown", "Other", "other",
        )

        results = store.list_task_artifacts("t1", "task-A")
        assert len(results) == 2
        assert all(r.task_id == "task-A" for r in results)

    def test_get_artifact(self, store):
        rec = store.create_text_artifact(
            "t1", "s1", "turn1", None, None,
            "markdown", "Lookup Test", "content",
        )
        fetched = store.get_artifact(rec.artifact_id)
        assert fetched is not None
        assert fetched.title == "Lookup Test"

    def test_get_nonexistent(self, store):
        assert store.get_artifact("not-a-real-id") is None

    def test_to_dict(self, store):
        rec = store.create_text_artifact(
            "t1", "s1", "turn1", "p1", "task1",
            "markdown", "Dict Test", "content",
            created_by="sai-forge", skill_id="docx-generator",
        )
        d = rec.to_dict()
        assert isinstance(d, dict)
        assert d["artifact_id"] == rec.artifact_id
        assert d["created_by"] == "sai-forge"
        assert d["skill_id"] == "docx-generator"


# ── Generators ───────────────────────────────────────────────

class TestPDFGenerator:
    def test_generate_pdf_basic(self):
        data = generate_pdf("Test Report", "This is a test document.\n\nSecond paragraph.")
        assert isinstance(data, (bytes, bytearray))
        assert len(data) > 100
        assert bytes(data)[:5] == b"%PDF-"

    def test_generate_pdf_with_headers(self):
        content = "# Section 1\nParagraph one.\n## Subsection\n- Item A\n- Item B"
        data = generate_pdf("Headed Doc", content, author="Test Author")
        assert bytes(data)[:5] == b"%PDF-"


class TestDOCXGenerator:
    def test_generate_docx_basic(self):
        data = generate_docx("Test Doc", "Hello world.\n\nSecond paragraph.")
        assert isinstance(data, (bytes, bytearray))
        assert len(data) > 100
        # DOCX is a ZIP file (PK header)
        assert bytes(data)[:2] == b"PK"

    def test_generate_docx_with_headers(self):
        content = "# Introduction\nSome text.\n## Details\n- Point one\n- Point two"
        data = generate_docx("Headed Doc", content, author="Tester")
        assert bytes(data)[:2] == b"PK"


# ── Being skill mapping ─────────────────────────────────────

class TestBeingSkillMapping:
    def test_default_skills(self):
        from bomba_sr.dashboard.service import get_being_skills
        skills = get_being_skills("sai-memory")
        assert "pdf-generator" in skills
        assert "docx-generator" in skills
        assert "code-generator" in skills

    def test_forge_has_screenshot(self):
        from bomba_sr.dashboard.service import get_being_skills
        skills = get_being_skills("sai-forge")
        assert "screenshot" in skills
        assert "pdf-generator" in skills

    def test_unknown_being_gets_defaults(self):
        from bomba_sr.dashboard.service import get_being_skills
        skills = get_being_skills("unknown-being")
        assert "pdf-generator" in skills
        assert "screenshot" not in skills
