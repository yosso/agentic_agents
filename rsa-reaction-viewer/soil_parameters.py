"""Typed soil-layer values in the confirmed workbook units."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class SoilParameters:
    """The 12 parsed parameters for one layer, in worksheet column order.

    START/END are depths in feet, positive downward from the hole's top.
    None denotes a missing or invalid numeric input, never an assumed zero.
    An empty model denotes a missing soil-model label. Validation findings,
    raw workbook values and source cells are retained by the preparation layer.
    Construction does not imply engineering validity or solver readiness.
    """

    start: float | None  # ft
    end: float | None  # ft
    model: str  # e.g. SOFT CLAY, SAND, ROCK
    density: float | None  # lb/ft^3
    cohesion_ultimate: float | None  # kip/ft^2
    cohesion_factored: float | None  # kip/ft^2
    friction_angle: float | None  # degrees
    k_static: float | None  # lb/in^3
    k_cyclic: float | None  # lb/in^3
    k_static_factored: float | None  # lb/in^3; workbook fKh
    e50: float | None  # unitless strain at 50% maximum principal stress difference
    e50_factored: float | None  # unitless
