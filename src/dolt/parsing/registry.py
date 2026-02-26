"""Parser Registry — 확장자별 파서 자동 매핑."""

from __future__ import annotations

from dolt.errors import UnsupportedFormatError
from dolt.parsing.base import BaseParser
from dolt.utils.logging import get_logger

logger = get_logger("parsing")


class ParserRegistry:
    """확장자 → Parser 매핑을 관리한다."""

    def __init__(self) -> None:
        self._parsers: dict[str, BaseParser] = {}

    def register(self, parser: BaseParser) -> None:
        """파서를 등록한다. 동일 확장자는 덮어쓴다."""
        for ext in parser.supported_extensions():
            ext = ext.lower()
            self._parsers[ext] = parser
            logger.debug("파서 등록: %s → %s", ext, type(parser).__name__)

    def get_parser(self, file_ext: str) -> BaseParser:
        """확장자에 맞는 파서를 반환한다."""
        parser = self._parsers.get(file_ext.lower())
        if parser is None:
            raise UnsupportedFormatError(file_ext)
        return parser

    def list_supported(self) -> list[str]:
        """지원하는 모든 확장자 목록."""
        return sorted(self._parsers.keys())


def create_default_registry() -> ParserRegistry:
    """빌트인 파서를 모두 등록한 기본 레지스트리를 생성한다."""
    from dolt.parsing.docx_parser import DOCXParser
    from dolt.parsing.html_parser import HTMLParser
    from dolt.parsing.markdown_parser import MarkdownParser
    from dolt.parsing.pdf_parser import PDFParser
    from dolt.parsing.text_parser import PlainTextParser

    registry = ParserRegistry()
    registry.register(PDFParser())
    registry.register(DOCXParser())
    registry.register(HTMLParser())
    registry.register(MarkdownParser())
    registry.register(PlainTextParser())
    return registry
