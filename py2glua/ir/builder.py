import ast
from typing import Iterable

from .ir_base import (
    BinOp,
    Constant,
    File,
    Function,
    Import,
    ImportType,
    IRNode,
    Return,
    VarLoad,
    VarStore,
)


class IRBuilder:
    @classmethod
    def build_ir(cls, module: ast.Module) -> File:
        file = File(lineno=None, col_offset=None, parent=None)
        for stmt in module.body:
            ir_nodes = cls.build_node(stmt)
            if not ir_nodes:
                continue

            if isinstance(ir_nodes, list):
                cls._append_children(file, ir_nodes)

            else:
                cls._append_child(file, ir_nodes)

        return file

    @classmethod
    def build_node(cls, node: ast.AST | None):
        if node is None:
            return None

        handler = getattr(cls, f"build_{type(node).__name__}", None)
        if handler is None:
            raise NotImplementedError(f"Unsupported AST node: {type(node).__name__}")

        return handler(node)

    @staticmethod
    def _append_child(parent: File | Function, child: IRNode) -> None:
        child.parent = parent
        parent.body.append(child)  # type: ignore[attr-defined]

    @staticmethod
    def _append_children(parent: File | Function, children: Iterable[IRNode]) -> None:
        for ch in children:
            ch.parent = parent
            parent.body.append(ch)  # type: ignore[attr-defined]

    # imports
    @staticmethod
    def build_Import(node: ast.Import) -> Import:
        names = [alias.name for alias in node.names]
        aliases = [alias.asname for alias in node.names]
        return Import(
            module=None,
            names=names,
            aliases=aliases,
            import_type=ImportType.UNKNOWN,
            lineno=node.lineno,
            col_offset=node.col_offset,
            parent=None,
        )

    @staticmethod
    def build_ImportFrom(node: ast.ImportFrom) -> Import:
        names = [alias.name for alias in node.names]
        aliases = [alias.asname for alias in node.names]
        return Import(
            module=node.module,
            names=names,
            aliases=aliases,
            import_type=ImportType.UNKNOWN,
            lineno=node.lineno,
            col_offset=node.col_offset,
            parent=None,
        )

    # functions
    @classmethod
    def build_FunctionDef(cls, node: ast.FunctionDef) -> Function:
        args = [a.arg for a in node.args.args]
        decorators = [ast.unparse(d) for d in node.decorator_list]

        fn = Function(
            name=node.name,
            args=args,
            decorators=decorators,
            lineno=node.lineno,
            col_offset=node.col_offset,
            parent=None,
            body=[],
        )

        for stmt in node.body:
            ir = cls.build_node(stmt)
            if not ir:
                continue

            if isinstance(ir, list):
                for ch in ir:
                    ch.parent = fn

                fn.body.extend(ir)

            else:
                ir.parent = fn
                fn.body.append(ir)

        return fn

    @classmethod
    def build_Return(cls, node: ast.Return) -> Return:
        value_ir = cls.build_node(node.value) if node.value is not None else None
        ret = Return(
            value=value_ir,
            lineno=node.lineno,
            col_offset=node.col_offset,
            parent=None,
        )

        if value_ir is not None:
            value_ir.parent = ret

        return ret

    # assignments
    @classmethod
    def build_Assign(cls, node: ast.Assign) -> list[VarStore]:
        value_ir = cls.build_node(node.value)
        if not isinstance(value_ir, (VarLoad, Constant, BinOp)):
            raise NotImplementedError(
                f"Assign value of type {type(value_ir).__name__} is not supported yet"
            )

        stores: list[VarStore] = []
        for target in node.targets:
            if isinstance(target, ast.Name):
                store = VarStore(
                    name=target.id,
                    value=value_ir,
                    lineno=node.lineno,
                    col_offset=node.col_offset,
                    parent=None,
                )
                value_ir.parent = store
                stores.append(store)

            else:
                raise NotImplementedError(
                    f"Unsupported assignment target: {type(target).__name__}"
                )

        return stores

    @classmethod
    def build_AnnAssign(cls, node: ast.AnnAssign) -> VarStore:
        if not isinstance(node.target, ast.Name):
            raise NotImplementedError(
                f"Unsupported annotated target: {type(node.target).__name__}"
            )

        if node.value is None:
            raise NotImplementedError(
                "Annotated assignment without value is not supported yet"
            )

        value_ir = cls.build_node(node.value)
        if not isinstance(value_ir, (VarLoad, Constant, BinOp)):
            raise NotImplementedError(
                f"AnnAssign value of type {type(value_ir).__name__} is not supported yet"
            )

        store = VarStore(
            name=node.target.id,
            value=value_ir,
            lineno=node.lineno,
            col_offset=node.col_offset,
            parent=None,
        )
        value_ir.parent = store
        return store

    @classmethod
    def build_AugAssign(cls, node: ast.AugAssign) -> list[VarStore]:
        if not isinstance(node.target, ast.Name):
            raise NotImplementedError(
                f"Unsupported augmented target: {type(node.target).__name__}"
            )

        left = VarLoad(
            name=node.target.id,
            lineno=node.lineno,
            col_offset=node.col_offset,
            parent=None,
        )
        right = cls.build_node(node.value)
        if not isinstance(right, (VarLoad, Constant, BinOp)):
            raise NotImplementedError(
                f"AugAssign value of type {type(right).__name__} is not supported yet"
            )

        binop = BinOp(
            op=cls._op_to_str(node.op),
            left=left,
            right=right,
            lineno=node.lineno,
            col_offset=node.col_offset,
            parent=None,
        )
        left.parent = binop
        right.parent = binop

        store = VarStore(
            name=node.target.id,
            value=binop,
            lineno=node.lineno,
            col_offset=node.col_offset,
            parent=None,
        )
        binop.parent = store
        return [store]

    # expressions (leafs + binop)
    @staticmethod
    def build_Name(node: ast.Name) -> VarLoad:
        return VarLoad(
            name=node.id,
            lineno=node.lineno,
            col_offset=node.col_offset,
            parent=None,
        )

    @staticmethod
    def build_Constant(node: ast.Constant) -> Constant:
        return Constant(
            value=node.value,  # type: ignore
            lineno=node.lineno,
            col_offset=node.col_offset,
            parent=None,
        )

    @classmethod
    def build_BinOp(cls, node: ast.BinOp) -> BinOp:
        left = cls.build_node(node.left)
        right = cls.build_node(node.right)
        if not isinstance(left, (VarLoad, Constant, BinOp)) or not isinstance(
            right, (VarLoad, Constant, BinOp)
        ):
            raise NotImplementedError(
                f"BinOp operands not supported: {type(left).__name__}, {type(right).__name__}"
            )

        binop = BinOp(
            op=cls._op_to_str(node.op),
            left=left,
            right=right,
            lineno=node.lineno,
            col_offset=node.col_offset,
            parent=None,
        )
        left.parent = binop
        right.parent = binop
        return binop

    # helpers
    @staticmethod
    def _op_to_str(op: ast.AST) -> str:
        mapping = {
            ast.Add: "+",
            ast.Sub: "-",
            ast.Mult: "*",
            ast.Div: "/",
            ast.Mod: "%",
            ast.BitOr: "|",
            ast.BitAnd: "&",
            ast.BitXor: "^",
            ast.LShift: "<<",
            ast.RShift: ">>",
            ast.FloorDiv: "//",
            ast.Pow: "**",
        }
        for k, v in mapping.items():
            if isinstance(op, k):
                return v

        raise NotImplementedError(f"Unsupported binary operator: {type(op).__name__}")
