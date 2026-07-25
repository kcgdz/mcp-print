"""Tests for real-file PDF preflight (requires pypdf)."""

import pytest

pypdf = pytest.importorskip("pypdf")

from pypdf import PdfWriter  # noqa: E402
from pypdf.generic import RectangleObject  # noqa: E402

from mcp_print.tools.pdfcheck import pdf_preflight  # noqa: E402

A4_PT = (595.28, 841.89)  # 210 x 297 mm
BLEED_PT = 8.5  # ~3 mm


def _make_pdf(path, with_bleed: bool = True) -> None:
    writer = PdfWriter()
    if with_bleed:
        w = A4_PT[0] + 2 * BLEED_PT
        h = A4_PT[1] + 2 * BLEED_PT
        page = writer.add_blank_page(width=w, height=h)
        page.trimbox = RectangleObject((BLEED_PT, BLEED_PT, BLEED_PT + A4_PT[0], BLEED_PT + A4_PT[1]))
        page.bleedbox = RectangleObject((0, 0, w, h))
    else:
        writer.add_blank_page(width=A4_PT[0], height=A4_PT[1])
    with open(path, "wb") as f:
        writer.write(f)


class TestPdfPreflight:
    def test_pdf_with_bleed_passes(self, tmp_path) -> None:
        pdf = tmp_path / "with_bleed.pdf"
        _make_pdf(pdf, with_bleed=True)
        result = pdf_preflight(str(pdf))
        assert result["page_count"] == 1
        bleed_check = next(c for c in result["checks"] if c["name"] == "bleed")
        assert bleed_check["status"] == "pass"
        assert abs(result["pages"][0]["trim_mm"]["width"] - 210) < 1

    def test_pdf_without_bleed_fails_bleed(self, tmp_path) -> None:
        pdf = tmp_path / "no_bleed.pdf"
        _make_pdf(pdf, with_bleed=False)
        result = pdf_preflight(str(pdf))
        bleed_check = next(c for c in result["checks"] if c["name"] == "bleed")
        assert bleed_check["status"] == "fail"
        assert result["status"] == "fail"

    def test_no_fonts_reports_pass(self, tmp_path) -> None:
        pdf = tmp_path / "blank.pdf"
        _make_pdf(pdf)
        result = pdf_preflight(str(pdf))
        font_check = next(c for c in result["checks"] if c["name"] == "fonts")
        assert font_check["status"] == "pass"

    def test_missing_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            pdf_preflight("does_not_exist.pdf")

    def test_unknown_method_raises(self, tmp_path) -> None:
        pdf = tmp_path / "x.pdf"
        _make_pdf(pdf)
        with pytest.raises(ValueError, match="target_method"):
            pdf_preflight(str(pdf), target_method="letterpress")
