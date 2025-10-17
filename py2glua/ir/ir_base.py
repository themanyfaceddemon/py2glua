from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

from ..runtime import Realm


@dataclass
class IRNode:
    lineno: int | None
    col_offset: int | None
    parent: "IRNode | None"

    def walk(self) -> Iterator["IRNode"]:
        raise NotImplementedError


@dataclass
class File(IRNode):
    path: Path | None = None
    realm: Realm | None = None
    meta_tags: list[str] = field(default_factory=list)
    body: list[IRNode] = field(default_factory=list)

    def walk(self) -> Iterator[IRNode]:
        yield self
        for ch in self.body:
            yield from ch.walk()


# region Import
class ImportType(Enum):
    UNKNOWN = auto()
    PYTHON_STD = auto()
    EXTERNAL = auto()
    LOCAL = auto()
    INTERNAL = auto()


@dataclass
class Import(IRNode):
    module: str | None = None
    names: list[str] = field(default_factory=list)
    aliases: list[str | None] = field(default_factory=list)
    import_type: ImportType = ImportType.UNKNOWN

    def walk(self) -> Iterator[IRNode]:
        yield self


# endregion


# region Constants / Vars
@dataclass
class Constant(IRNode):
    value: int | float | str | bool | None

    def walk(self) -> Iterator[IRNode]:
        yield self


@dataclass
class VarStore(IRNode):
    name: str
    value: IRNode

    def walk(self) -> Iterator[IRNode]:
        yield self
        yield from self.value.walk()


@dataclass
class VarLoad(IRNode):
    name: str

    def walk(self) -> Iterator[IRNode]:
        yield self


# endregion


# region Binary operations
@dataclass
class BinOp(IRNode):
    op: str  # "+", "-", "*", "/", "%", "|", "&", "^", "<<", ">>", "//", "**"
    left: IRNode
    right: IRNode

    def walk(self) -> Iterator[IRNode]:
        yield self
        yield from self.left.walk()
        yield from self.right.walk()


# endregion


# region Functions
@dataclass
class Function(IRNode):
    name: str
    args: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    body: list[IRNode] = field(default_factory=list)

    def walk(self) -> Iterator[IRNode]:
        yield self
        for ch in self.body:
            yield from ch.walk()


@dataclass
class Return(IRNode):
    value: IRNode | None = None

    def walk(self) -> Iterator[IRNode]:
        yield self
        if self.value is not None:
            yield from self.value.walk()


# endregion
