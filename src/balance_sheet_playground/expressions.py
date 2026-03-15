from __future__ import annotations

import ast
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Mapping


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True)
class RateExpression:
    constant: Decimal = Decimal("0")
    coefficients: dict[str, Decimal] = field(default_factory=dict)

    def __add__(self, other: "RateExpression") -> "RateExpression":
        coefficients = dict(self.coefficients)
        for symbol, value in other.coefficients.items():
            coefficients[symbol] = coefficients.get(symbol, Decimal("0")) + value
            if coefficients[symbol] == 0:
                del coefficients[symbol]
        return RateExpression(self.constant + other.constant, coefficients)

    def __sub__(self, other: "RateExpression") -> "RateExpression":
        return self + (-other)

    def __neg__(self) -> "RateExpression":
        return self * Decimal("-1")

    def __mul__(self, other: object) -> "RateExpression":
        factor = _to_decimal(other)
        return RateExpression(
            self.constant * factor,
            {symbol: value * factor for symbol, value in self.coefficients.items()},
        )

    __rmul__ = __mul__

    def __truediv__(self, other: object) -> "RateExpression":
        divisor = _to_decimal(other)
        return RateExpression(
            self.constant / divisor,
            {symbol: value / divisor for symbol, value in self.coefficients.items()},
        )

    def evaluate(self, values: Mapping[str, object]) -> Decimal:
        result = self.constant
        for symbol, coefficient in self.coefficients.items():
            result += coefficient * _to_decimal(values[symbol])
        return result

    def format(self, percent: bool = True, precision: int = 4) -> str:
        parts: list[str] = []
        if self.constant:
            parts.append(_format_number(self.constant, percent=percent, precision=precision))
        for symbol in sorted(self.coefficients):
            coefficient = self.coefficients[symbol]
            if coefficient == 1:
                parts.append(symbol)
            elif coefficient == -1:
                parts.append(f"-{symbol}")
            else:
                parts.append(
                    f"{_format_number(coefficient, percent=percent, precision=precision)}*{symbol}"
                )
        if not parts:
            return _format_number(Decimal("0"), percent=percent, precision=precision)
        result = parts[0]
        for part in parts[1:]:
            if part.startswith("-"):
                result += f" - {part[1:]}"
            else:
                result += f" + {part}"
        return result

    @classmethod
    def fixed(cls, value: object) -> "RateExpression":
        return cls(constant=_to_decimal(value))

    @classmethod
    def symbol(cls, name: str, coefficient: object = 1) -> "RateExpression":
        return cls(coefficients={name: _to_decimal(coefficient)})

    @classmethod
    def parse(cls, raw: str | None) -> "RateExpression":
        if raw is None or str(raw).strip() == "":
            return cls()
        parser = _RateParser(str(raw))
        return parser.parse()


def _format_number(value: Decimal, percent: bool, precision: int) -> str:
    scale = Decimal("100") if percent else Decimal("1")
    suffix = "%" if percent else ""
    scaled = value * scale
    quant = Decimal(1).scaleb(-precision)
    text = f"{scaled.quantize(quant):f}".rstrip("0").rstrip(".")
    if text == "-0":
        text = "0"
    return f"{text}{suffix}"


class _RateParser:
    def __init__(self, source: str) -> None:
        self.source = source

    def parse(self) -> RateExpression:
        source = self.source.replace("%", "*0.01")
        tree = ast.parse(source, mode="eval")
        return self._visit(tree.body)

    def _visit(self, node: ast.AST) -> RateExpression:
        if isinstance(node, ast.Name):
            return RateExpression.symbol(node.id)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return RateExpression.fixed(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -self._visit(node.operand)
        if isinstance(node, ast.BinOp):
            left = self._visit(node.left)
            right = self._visit(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return self._multiply(left, right)
            if isinstance(node.op, ast.Div):
                return self._divide(left, right)
        raise ValueError(f"Unsupported rate expression: {self.source}")

    def _multiply(self, left: RateExpression, right: RateExpression) -> RateExpression:
        if left.coefficients and right.coefficients:
            raise ValueError("Non-linear rate expressions are not supported")
        if right.coefficients:
            return right * left.constant
        return left * right.constant

    def _divide(self, left: RateExpression, right: RateExpression) -> RateExpression:
        if right.coefficients:
            raise ValueError("Division by symbolic terms is not supported")
        return left / right.constant
