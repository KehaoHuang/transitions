from __future__ import annotations

from typing import TYPE_CHECKING

from condition import Condition
from util import listify, Callback, Callbacks

if TYPE_CHECKING:
    from event import EventData


class Transition:
    """ Representation of a transition managed by a Machine instance.

    Attributes:
        source (str): Source state of the Transition.
        _dest (str): Destination state of the Transition.
        _before (Callbacks): Callbacks executed before the Transition is executed but only of condition checks have
        been successful.
        _after (Callbacks): Callbacks executed after the Transition is executed but only of condition checks have
        been successful.
        _prepare (Callbacks): Callbacks executed before conditions checks.
        _conditions (list[Condition]): Callbacks evaluated to determine if the transition should be executed.
    """

    dynamic_methods: list[str] = ['before', 'after', 'prepare']
    """ A list of dynamic methods which can be resolved by a Machine instance for convenience functions. """

    def __init__(self,
                 source: str,
                 dest: str,
                 conditions: Callback | Callbacks | None,
                 unless: Callback | Callbacks | None,
                 before: Callback | Callbacks | None,
                 after: Callback | Callbacks | None,
                 prepare: Callback | Callbacks | None,
                 **kwargs):
        self.source = source
        self._dest = dest
        self._before: Callbacks = listify(before)
        self._after: Callbacks = listify(after)
        self._prepare: Callbacks = listify(prepare)
        self._conditions: list[Condition] = (list(Condition(func, target=True) for func in listify(conditions))
                                             + list(Condition(func, target=False) for func in listify(unless)))

    def _eval_conditions(self, event_data: EventData) -> bool:
        return all([cond.check(event_data) for cond in self._conditions])

    def _change2dest(self, event_data: EventData) -> None:
        event_data.machine.get_state(self.source).exit(event_data)
        event_data.machine.set_state(event_data.model, self._dest)
        event_data.update(getattr(event_data.model, event_data.machine.state_attribute))
        event_data.machine.get_state(self._dest).enter(event_data)

    def add_callback(self, trigger: str, func: Callback) -> None:
        """ Add a new before, after, or prepare callback.

        Args:
            trigger: The type of triggering event. Must be one of 'before', 'after' or 'prepare'.
            func: The callback function.
        """
        callbacks: Callbacks = getattr(self, trigger)
        callbacks.append(func)

    def execute(self, event_data: EventData) -> bool:
        """ Execute the transition.

        Args:
            event_data: An EventData instance.

        Returns:
            Indicates whether the transition was successfully executed (True if successful, False if not).
        """
        event_data.machine.callbacks(self._prepare, event_data)
        if not self._eval_conditions(event_data):
            return False
        event_data.machine.callbacks(event_data.machine.before_state_change + self._before, event_data)

        if self._dest:
            self._change2dest(event_data)
        event_data.machine.callbacks(event_data.machine.after_state_change + self._after, event_data)
        return True

    def __repr__(self):
        return f"<{type(self).__name__}('{self.source}', '{self._dest}')@{id(self)}>"
