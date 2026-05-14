from __future__ import annotations

from textwrap import dedent

from tcvn_copilot.rag.chunker import chunk_standard


def test_splits_on_numbered_clauses() -> None:
    text = dedent(
        """\
        1. Phạm vi áp dụng
        Quy chuẩn này áp dụng cho công trình dân dụng và công nghiệp.

        2. Tài liệu viện dẫn
        TCVN 2737:2023, QCVN 06:2022.

        2.1. Phân loại
        Các loại tải trọng được phân thành tĩnh tải và hoạt tải.

        3. Yêu cầu chung
        Tải trọng phải được tính toán theo trạng thái giới hạn.
        """
    )
    chunks = chunk_standard(text)
    numbers = [c.clause_number for c in chunks]
    assert "1" in numbers
    assert "2" in numbers
    assert "2.1" in numbers
    assert "3" in numbers


def test_handles_dieu_prefix() -> None:
    text = dedent(
        """\
        Điều 5. Cấp công trình
        Cấp I áp dụng cho công trình cao tầng.

        Điều 6. Tải trọng tính toán
        Bao gồm tĩnh tải và hoạt tải.
        """
    )
    chunks = chunk_standard(text)
    assert any(c.clause_number == "5" for c in chunks)
    assert any(c.clause_number == "6" for c in chunks)


def test_falls_back_to_size_chunking_when_no_clauses() -> None:
    text = "Một đoạn văn dài không có số điều khoản. " * 200
    chunks = chunk_standard(text)
    assert chunks
    assert all(c.clause_number.startswith("chunk-") for c in chunks)
