"""Code outline extraction functionality for cpai."""

from .base import OutlineExtractor
from .javascript import JavaScriptOutlineExtractor
from .python import PythonOutlineExtractor
from typing import List

__all__ = ['OutlineExtractor', 'JavaScriptOutlineExtractor', 'PythonOutlineExtractor']

EXTRACTORS: List[OutlineExtractor] = [
    JavaScriptOutlineExtractor(),
    PythonOutlineExtractor()
]
