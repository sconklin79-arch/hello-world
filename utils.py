def average(numbers):
    if not numbers:
        raise ValueError("average() requires a non-empty sequence")
    return sum(numbers) / len(numbers)


def get_first(items):
    if not items:
        raise ValueError("get_first() requires a non-empty sequence")
    return items[0]


def parse_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"cannot parse int from {value!r}")


def divide(a, b):
    if b == 0:
        raise ZeroDivisionError("divide() cannot divide by zero")
    return a / b
