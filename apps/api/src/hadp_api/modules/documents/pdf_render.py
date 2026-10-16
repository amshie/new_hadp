"""One lock around every use of pdfplumber that renders (pypdfium2 underneath).

pypdfium2 is not thread-safe. A sync route runs in uvicorn's thread pool, and a confirmation
screen asks for the regions of all its values at once: six renders in six threads crashed the
API process outright ("double free or corruption") on the first browser test. Every render,
and every pdfplumber open that may render, takes this lock; page texts (pdfminer, pure Python)
go through it too, which costs little and keeps one rule.
"""

from __future__ import annotations

import io
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pdfplumber

_LOCK = threading.Lock()


@contextmanager
def open_pdf(data: bytes) -> Iterator[Any]:
    """`pdfplumber.open` under the process-wide render lock. Hold it for the whole block: the
    pages render lazily, after the open."""
    with _LOCK, pdfplumber.open(io.BytesIO(data)) as pdf:
        yield pdf
