from __future__ import annotations


def pdf_with_text(lines: list[str]) -> bytes:
    ops = ["BT /F1 10 Tf 50 760 Td"]
    for i, line in enumerate(lines):
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")[:110]
        if i == 0:
            ops.append(f"({safe}) Tj")
        else:
            ops.append(f"0 -12 Td ({safe}) Tj")
    ops.append("ET")
    stream = "\n".join(ops)
    objects = []

    def obj(n: int, body: str) -> str:
        return f"{n} 0 obj\n{body}\nendobj\n"

    objects.append(obj(1, "<< /Type /Catalog /Pages 2 0 R >>"))
    objects.append(obj(2, "<< /Type /Pages /Kids [3 0 R] /Count 1 >>"))
    objects.append(
        obj(
            3,
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        )
    )
    objects.append(obj(4, f"<< /Length {len(stream.encode('latin-1', errors='replace'))} >>\nstream\n{stream}\nendstream"))
    objects.append(obj(5, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"))
    body = "".join(objects)
    xref_positions = []
    cursor = len("%PDF-1.4\n")
    chunks = []
    for raw in objects:
        xref_positions.append(cursor)
        chunks.append(raw)
        cursor += len(raw.encode("latin-1", errors="replace"))
    xref = ["xref", f"0 {len(objects)+1}", "0000000000 65535 f "]
    for pos in xref_positions:
        xref.append(f"{pos:010d} 00000 n ")
    xref_str = "\n".join(xref) + "\n"
    startxref = cursor + len("%PDF-1.4\n") - len("%PDF-1.4\n")
    # rebuild with accurate offsets
    header = "%PDF-1.4\n"
    content = header
    xref_positions = []
    for raw in objects:
        xref_positions.append(len(content))
        content += raw
    xref = ["xref", f"0 {len(objects)+1}", "0000000000 65535 f "]
    for pos in xref_positions:
        xref.append(f"{pos:010d} 00000 n ")
    xref_block = "\n".join(xref) + "\n"
    trailer = (
        f"trailer\n<< /Root 1 0 R /Size {len(objects)+1} >>\nstartxref\n{len(content)}\n%%EOF\n"
    )
    return (content + xref_block + trailer).encode("latin-1", errors="replace")
