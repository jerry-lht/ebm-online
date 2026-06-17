"""Infrastructure method package contracts.

Concrete method modules are loaded by registry/loader modules through a
module-level ``build_method()`` function. The returned object must satisfy the
corresponding application port or internal coordinator subtask interface.
"""

from __future__ import annotations

from typing import Protocol


class MethodFactoryModule(Protocol):
    def build_method(self) -> object:
        ...
