import ast

from py2glua.ir.builder import IRBuilder
from py2glua.ir.ir_base import (
    BinOp,
    Constant,
    File,
    Function,
    Return,
    VarLoad,
    VarStore,
)


def build_ir(src: str) -> File:
    tree = ast.parse(src)
    return IRBuilder.build_ir(tree)


# Простое присваивание
def test_simple_assign():
    src = "x = 1"
    ir = build_ir(src)

    assert isinstance(ir, File)
    assert len(ir.body) == 1

    node = ir.body[0]
    assert isinstance(node, VarStore)
    assert node.name == "x"
    assert isinstance(node.value, Constant)
    assert node.value.value == 1
    assert node.value.parent is node


# Бинарную операции
def test_binary_operation():
    src = "y = 2 * 3"
    ir = build_ir(src)

    store = ir.body[0]
    assert isinstance(store, VarStore)
    assert store.name == "y"

    binop = store.value
    assert isinstance(binop, BinOp)
    assert binop.op == "*"

    assert isinstance(binop.left, Constant)
    assert binop.left.value == 2
    assert isinstance(binop.right, Constant)
    assert binop.right.value == 3

    # Род связи
    assert binop.left.parent is binop
    assert binop.right.parent is binop
    assert binop.parent is store


# AugAssign x += y
def test_augassign():
    src = "x += y"
    ir = build_ir(src)

    store = ir.body[0]
    assert isinstance(store, VarStore)
    assert store.name == "x"

    binop = store.value
    assert isinstance(binop, BinOp)
    assert binop.op == "+"
    assert isinstance(binop.left, VarLoad)
    assert binop.left.name == "x"
    assert isinstance(binop.right, VarLoad)
    assert binop.right.name == "y"


# Функцию с телом и return
def test_function_def():
    src = """
def foo(a, b):
    x = a + b
    return x
"""
    ir = build_ir(src)

    fn = ir.body[0]
    assert isinstance(fn, Function)
    assert fn.name == "foo"
    assert fn.args == ["a", "b"]

    assert len(fn.body) == 2
    store, ret = fn.body

    # VarStore внутри функции
    assert isinstance(store, VarStore)
    assert store.name == "x"
    binop = store.value
    assert isinstance(binop, BinOp)
    assert binop.op == "+"

    # Return
    assert isinstance(ret, Return)
    assert isinstance(ret.value, VarLoad)
    assert ret.value.name == "x"


# BinOp (a + b * c)
def test_nested_binop():
    src = "z = a + b * c"
    ir = build_ir(src)

    store = ir.body[0]
    assert isinstance(store, VarStore)

    outer = store.value
    assert isinstance(outer, BinOp)
    assert outer.op == "+"

    right = outer.right
    assert isinstance(right, BinOp)
    assert right.op == "*"
    assert isinstance(right.left, VarLoad)
    assert isinstance(right.right, VarLoad)

    # Род связи
    assert right.parent is outer
    assert outer.parent is store
    assert store.parent is ir


# return без значения
def test_return_none():
    src = """
def f():
    return
"""
    ir = build_ir(src)

    fn = ir.body[0]
    assert isinstance(fn, Function)
    assert len(fn.body) == 1
    ret = fn.body[0]
    assert isinstance(ret, Return)
    assert ret.value is None
