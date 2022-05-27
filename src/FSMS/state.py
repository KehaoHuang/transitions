from __future__ import annotations

from typing import TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from event import EventData

from util import listify, Callback, Callbacks


class State:
    """ A persistent representation of a state managed by a Machine.

    Attributes:
        _name (str | Enum): State name which is also assigned to the model(s).
        _on_enter (list): Callbacks executed when a state is entered.
        _on_exit (list): Callbacks executed when a state is exit.
        ignore_invalid_triggers (bool): Indicates if unhandled/invalid triggers should raise an exception.
    """

    dynamic_methods: list[str] = ['on_enter', 'on_exit']
    """ A list of dynamic methods which can be resolved by a Machine instance for convenience functions. """

    def __init__(self,
                 name: str | Enum,
                 on_enter: Callback | Callbacks | None = None,
                 on_exit: Callback | Callbacks | None = None,
                 ignore_invalid_triggers: bool | None = None):
        self._name = name
        self._on_enter: Callbacks = listify(on_enter)
        self._on_exit: Callbacks = listify(on_exit)

        self.ignore_invalid_triggers = ignore_invalid_triggers

    @property
    def name(self):
        if isinstance(self._name, Enum):
            return self._name.name
        else:
            return self._name

    @property
    def value(self):
        return self._name

    def enter(self, event_data: EventData) -> None:
        """ Triggered when a state is entered. """
        event_data.machine.callbacks(self._on_enter, event_data)

    def exit(self, event_data) -> None:
        """ Triggered when a state is exited. """
        event_data.machine.callbacks(self._on_exit, event_data)

    def add_callback(self, trigger: str, func: str) -> None:
        """ Add a new enter or exit callback.
        Args:
            trigger: The type of triggering event. Must be one of 'enter' or 'exit'.
            func: The callback function.
        """
        callbacks: list = getattr(self, 'on_' + trigger)
        callbacks.append(func)

    def __repr__(self):
        return f"<{type(self).__name__}('{self._name}')@{id(self)}>"
