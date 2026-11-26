from dataclasses import dataclass
from io import BytesIO
import re
from zipfile import BadZipFile, ZipFile

from docx import Document as load_docx
from docx.opc.exceptions import PackageNotFoundError
from docx.table import Table
from docx.text.paragraph import Paragraph
from lxml.etree import XMLSyntaxError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

PDF_CONTENT_TYPE = "application/pdf"
DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MAX_DOCX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_DOCX_ARCHIVE_ENTRIES = 10_000


class UnsupportedDocumentError(ValueError):
    """The filename extension or declared media type is not supported."""


class InvalidDocumentError(ValueError):
    """The file is malformed, encrypted, or contains no extractable text."""


@dataclass(frozen=True)
class TextBlock:
    text: str
    page_number: int | None
    section_title: str | None


@dataclass(frozen=True)
class ExtractedDocument:
    blocks: list[TextBlock]
    page_count: int | None


def _looks_like_pdf_heading(line: str) -> bool:
    if len(line) > 120:
        return False
    if re.match(r"^\d+(?:\.\d+)*[.)]?\s+\S", line):
        return True
    return line.isupper() and sum(character.isalpha() for character in line) >= 3


def _extract_pdf(data: bytes) -> ExtractedDocument:
    if b"%PDF-" not in data[:1024]:
        raise InvalidDocumentError("The uploaded file is not a valid PDF.")

    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise InvalidDocumentError("Encrypted PDF files are not supported.")
        pages = reader.pages
        blocks: list[TextBlock] = []
        current_section: str | None = None
        for page_number, page in enumerate(pages, start=1):
            text = page.extract_text() or ""
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                if _looks_like_pdf_heading(line):
                    current_section = line
                blocks.append(
                    TextBlock(
                        text=line,
                        page_number=page_number,
                        section_title=current_section,
                    )
                )
    except InvalidDocumentError:
        raise
    except (PdfReadError, ValueError, OSError, KeyError) as error:
        raise InvalidDocumentError("The uploaded PDF could not be read.") from error

    if not blocks:
        raise InvalidDocumentError("The PDF contains no extractable text.")
    return ExtractedDocument(blocks=blocks, page_count=len(pages))


def _extract_docx(data: bytes) -> ExtractedDocument:
    try:
        with ZipFile(BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_DOCX_ARCHIVE_ENTRIES:
                raise InvalidDocumentError("The DOCX archive contains too many entries.")
            if sum(entry.file_size for entry in entries) > MAX_DOCX_UNCOMPRESSED_BYTES:
                raise InvalidDocumentError("The DOCX archive expands beyond the allowed size.")
            entry_names = {entry.filename for entry in entries}
            if "[Content_Types].xml" not in entry_names or "word/document.xml" not in entry_names:
                raise InvalidDocumentError("The uploaded file is not a valid DOCX document.")
        document = load_docx(BytesIO(data))
    except InvalidDocumentError:
        raise
    except (BadZipFile, PackageNotFoundError, XMLSyntaxError, ValueError, OSError, KeyError) as error:
        raise InvalidDocumentError("The uploaded DOCX could not be read.") from error

    blocks: list[TextBlock] = []
    current_section: str | None = None
    for item in document.iter_inner_content():
        if isinstance(item, Paragraph):
            text = item.text.strip()
            if not text:
                continue
            if item.style and item.style.name.lower().startswith("heading"):
                current_section = text
            blocks.append(TextBlock(text=text, page_number=None, section_title=current_section))
        elif isinstance(item, Table):
            for row in item.rows:
                text = " | ".join(cell.text.strip() for cell in row.cells).strip(" |")
                if text:
                    blocks.append(TextBlock(text=text, page_number=None, section_title=current_section))

    if not blocks:
        raise InvalidDocumentError("The DOCX contains no extractable text.")
    return ExtractedDocument(blocks=blocks, page_count=None)


def extract_document(filename: str, content_type: str, data: bytes) -> ExtractedDocument:
    extension = filename.rpartition(".")[2].lower()
    expected_content_type = {
        "pdf": PDF_CONTENT_TYPE,
        "docx": DOCX_CONTENT_TYPE,
    }.get(extension)
    if expected_content_type is None or content_type.split(";", 1)[0].strip().lower() != expected_content_type:
        raise UnsupportedDocumentError("Only PDF and DOCX documents are supported.")

    if extension == "pdf":
        return _extract_pdf(data)
    return _extract_docx(data)
