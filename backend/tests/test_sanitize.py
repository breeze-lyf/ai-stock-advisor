import math

def _sanitize_float(val):
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None

print(f"None -> {_sanitize_float(None)}")
print(f"nan (float) -> {_sanitize_float(float('nan'))}")
print(f"inf (float) -> {_sanitize_float(float('inf'))}")
print(f"123.45 -> {_sanitize_float(123.45)}")
print(f"'123.45' -> {_sanitize_float('123.45')}")
print(f"'abc' -> {_sanitize_float('abc')}")
