def is_number(num: str) -> bool:
    try:
        float(num)
    except ValueError:
        return False
    return True
