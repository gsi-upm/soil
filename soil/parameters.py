from __future__ import annotations

from typing_extensions import Annotated
import annotated_types
from typing import *

from dataclasses import dataclass

class Parameter:
    pass


def floatrange(
    *,
    gt: Optional[float] = None,
    ge: Optional[float] = None,
    lt: Optional[float] = None,
    le: Optional[float] = None,
    multiple_of: Optional[float] = None,
) -> type[float]:
    return Annotated[ 
        float,
        annotated_types.Interval(gt=gt, ge=ge, lt=lt, le=le),
        annotated_types.MultipleOf(multiple_of) if multiple_of is not None else None,
    ]

function = Annotated[Callable, Parameter]
Integer = Annotated[int, Parameter]
Float = Annotated[float, Parameter]


probability = floatrange(ge=0, le=1)