"""Cálculo de totales del canario del jurado."""


def total(precios: list[float], descuento: float = 0.0) -> float:
    """Suma los precios y aplica un descuento entre 0 y 1."""
    if not 0 <= descuento <= 1:
        raise ValueError("el descuento va entre 0 y 1")
    subtotal = sum(precios)
    return round(subtotal * (1 - descuento), 2)


def promedio(precios: list[float]) -> float:
    """Promedio simple; una lista vacía es un error, no un cero."""
    if not precios:
        raise ValueError("no hay precios que promediar")
    return sum(precios) / len(precios)
