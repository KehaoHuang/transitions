from __future__ import annotations

from typing import TYPE_CHECKING

from util import Callback

if TYPE_CHECKING:
    from event import EventData


class Condition:
    """ A helper class to call condition checks in the intended way.

    Attributes:
        _func (Callback): The function to call for the condition check.
        _target (bool): Indicates the target state. i.e., when True, the condition-checking callback should return
        True to pass the test, and wen False, the callback should return False to pass.

    Notes: This class should not be initialized or called from outside a Transition instance, and exists at module
    level (rather than nesting under the Transition class).
    """

    def __init__(self, func: Callback, target: bool = True):
        self._func = func
        self._target = target

    def check(self, event_data: EventData) -> bool:
        """ Check whether the condition passes.

        Args:
            event_data: An EventData instance to pass to the condition (if event sending is enabled) or to extract
            arguments from (if event sending is disabled). Also contains the data model attached to the current
            machine which is used to invoke the condition.

        Returns:
            Whether the condition test passes.
        """
        predicate = event_data.machine.resolve_callable(self._func, event_data)
        if event_data.machine.send_event:
            return predicate(event_data) == self._target
        return predicate(*event_data.args, **event_data.kwargs) == self._target

    def __repr__(self):
        return f"<{type(self).__name__}('{self._func}')@{id(self)}>"
