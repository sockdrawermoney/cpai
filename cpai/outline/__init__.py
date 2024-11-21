"""Code outline extraction functionality for cpai."""

from .base import OutlineExtractor
from .javascript import JavaScriptOutlineExtractor
from .python import PythonOutlineExtractor
from .solidity import SolidityOutlineExtractor
from .rust import RustOutlineExtractor
from typing import List

__all__ = ['OutlineExtractor', 'JavaScriptOutlineExtractor', 'PythonOutlineExtractor',
           'SolidityOutlineExtractor', 'RustOutlineExtractor']

EXTRACTORS: List[OutlineExtractor] = [
    JavaScriptOutlineExtractor(),
    PythonOutlineExtractor(),
    SolidityOutlineExtractor(),
    RustOutlineExtractor()
]
