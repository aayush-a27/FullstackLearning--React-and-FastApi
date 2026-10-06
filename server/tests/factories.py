"""Test data builders."""


def sample_pdf(pages: int = 1, text: str = "Hello from the test document.") -> bytes:
    """
    Build a small valid PDF with selectable text on every page.

    Written byte by byte rather than with a library so the fixture stays
    deterministic and doesn't depend on pypdf's internal API.
    """
    escaped = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")

    objects: list[bytes] = []

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)  # object numbers are 1-based

    catalog_num = add(b"")  # placeholders, filled in once the pages exist
    pages_num = add(b"")
    font_num = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    page_nums: list[int] = []
    for index in range(pages):
        content = f"BT /F1 12 Tf 20 150 Td ({escaped} page {index + 1}) Tj ET".encode()
        stream_num = add(
            b"<< /Length "
            + str(len(content)).encode()
            + b" >>\nstream\n"
            + content
            + b"\nendstream"
        )
        page_nums.append(
            add(
                b"<< /Type /Page /Parent "
                + str(pages_num).encode()
                + b" 0 R /MediaBox [0 0 300 300] /Contents "
                + str(stream_num).encode()
                + b" 0 R /Resources << /Font << /F1 "
                + str(font_num).encode()
                + b" 0 R >> >> >>"
            )
        )

    kids = b" ".join(str(n).encode() + b" 0 R" for n in page_nums)
    objects[pages_num - 1] = (
        b"<< /Type /Pages /Kids [" + kids + b"] /Count " + str(pages).encode() + b" >>"
    )
    objects[catalog_num - 1] = (
        b"<< /Type /Catalog /Pages " + str(pages_num).encode() + b" 0 R >>"
    )

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += str(number).encode() + b" 0 obj\n" + body + b"\nendobj\n"

    xref_at = len(out)
    out += b"xref\n0 " + str(len(objects) + 1).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        b"trailer\n<< /Size "
        + str(len(objects) + 1).encode()
        + b" /Root "
        + str(catalog_num).encode()
        + b" 0 R >>\nstartxref\n"
        + str(xref_at).encode()
        + b"\n%%EOF\n"
    )
    return bytes(out)
