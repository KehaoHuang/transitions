from collections.abc import Callable
from enum import Enum, EnumMeta
from typing import TypeVar

T = TypeVar('T')

Callback = str | Callable[..., None]
Callbacks = list[Callback]
StateParam = str | Enum
StatesParam = list[str] | EnumMeta


def listify(obj: T | list[T]) -> list[T]:
    """Wraps a passed object into a list in case it has not been a list, tuple before.

    Args:
        obj: object to be converted into a list.
    Returns:
        A list, empty in case "obj" is None. May also return a tuple in case "obj" has been a tuple before.
    """
    if obj is None:
        return []
    try:
        return obj if isinstance(obj, (list, tuple, EnumMeta)) else [obj]
    except ReferenceError:
        return [obj]
