"""Validate persisted circuit JSON before it reaches the SVG renderer."""
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field


Finite = Annotated[float, Field(allow_inf_nan=False)]


class Corner(BaseModel):
    number: int = Field(ge=1)
    letter: str = ""
    x: Finite
    y: Finite
    label_x: Finite
    label_y: Finite


class Start(BaseModel):
    x: Finite
    y: Finite
    ahead_x: Finite
    ahead_y: Finite


class CircuitData(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    circuit_name: Optional[str] = None
    rotation: Finite = 0
    year: Optional[int] = None
    width: Finite = Field(gt=0)
    height: Finite = Field(gt=0)
    outline: list[tuple[Finite, Finite]] = Field(min_length=50, max_length=10001)
    corners: list[Corner] = Field(max_length=100)
    start: Optional[Start] = None
