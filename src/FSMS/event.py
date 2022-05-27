from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, TYPE_CHECKING

from itertools import chain
from functools import partial

from exception import MachineError
from state import State
from transition import Transition

if TYPE_CHECKING:
    from machine import Machine


class Event:
    """ A collection of transitions assigned to the same trigger. """

    def __init__(self, name: str, machine: Machine):
        self._name = name
        self._machine = machine
        self.transitions: Dict[str, List[Transition]] = defaultdict(list)

    def _trigger(self, model: Any, *args, **kwargs):
        """ Internal trigger function called by the Machine instance.

        Args:
            model: The currently processed model.
            args and kwargs: Optional positional or named arguments that will be passed onto the EventData object,
            enabling arbitrary state information to be passed on to downstream triggered functions.

        Returns:
            Indicates whether a transition was successfully executed (True if successful, False if not).
        """

        state = self._machine.get_model_state(model)
        if state.name not in self.transitions:
            ignore = state.ignore_invalid_triggers \
                if state.ignore_invalid_triggers is not None \
                else self._machine.ignore_invalid_triggers
            if ignore:
                return False
            else:
                raise MachineError(f"{self._machine.name} Cannot trigger event {self._name} from state {state.name}")
        event_data = EventData(state, self, self._machine, model, args, kwargs)
        return self._process(event_data)

    def _process(self, event_data: EventData):
        self._machine.callbacks(self._machine.prepare_event, event_data)
        try:
            for trans in self.transitions[event_data.state.name]:
                event_data.transition = trans
                if trans.execute(event_data):
                    event_data.result = True
                    break
        except Exception as e:
            event_data.error = e
            if self._machine.on_exception:
                self._machine.callbacks(self._machine.on_exception, event_data)
            else:
                raise
        finally:
            try:
                self._machine.callbacks(self._machine.finalize_event, event_data)
            except Exception as e:
                pass
        return event_data.result

    def add_transition(self, transition: Transition):
        self.transitions[transition.source].append(transition)

    def add_callback(self, trigger: str, func: str):
        for transition in chain(*self.transitions.values()):
            transition.add_callback(trigger, func)

    def trigger(self, model: Any, *args, **kwargs):
        func = partial(self._trigger, model, *args, **kwargs)
        return self._machine.process(func)


class EventData:
    """ Collection of relevant data related to the ongoing transition attempt.

    Attributes:
        state (State): The State from which the Event was triggered.
        event (Event): The triggering Event.
        machine (Machine): The current Machine instance.
        model (Any): The model/object the machine is bound to.
        args (list): Optional positional arguments from trigger method to store internally for possible later use.
        kwargs (dict): Optional keyword arguments from trigger method to store internally for possible later use.
        transition (Transition): Currently active transition. Will be assigned during triggering.
        error (Exception): In case a triggered event causes an Error, it is assigned here and passed on.
        result (bool): True in case a transition has been successful, False otherwise.
    """

    def __init__(self, state: State, event: Event, machine: Machine, model: Any, args: tuple, kwargs: dict):
        """
        Args:
        """
        self.state = state
        self.event = event
        self.machine = machine
        self.model = model
        self.args = args
        self.kwargs = kwargs
        self.transition = None
        self.error = None
        self.result = False

    def update(self, state):
        """ Updates the EventData object with the passed state.

        Attributes:
            state (State, str or Enum): The state object, enum member or string to assign to EventData.
        """

        if not isinstance(state, State):
            self.state = self.machine.get_state(state)

    def __repr__(self):
        return f"<{type(self).__name__}('{self.state}', {getattr(self, 'transition')})@{id(self)}>"
