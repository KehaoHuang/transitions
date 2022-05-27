from collections import deque, OrderedDict
from collections.abc import Callable
from functools import partial
from typing import Any
from enum import Enum

from event import Event, EventData
from state import State
from transition import Transition
from util import listify, Callback, Callbacks, StateParam, StatesParam


class Machine:
    """ Machine manages states, transitions and models.

    In case it is initialized without a specific model (or specifically no model), it will also act as a model
    itself. Machine takes also care of decorating models with convenience functions related to added transitions and
    states during runtime.

    Attributes:
        model: Model/list of models attached to the machine.

        states: Collection of all registered states.

        state_attribute: Attribute that would be attached to models. Accessing this attribute would return the
        current state of the model.

        initial: Name of the initial state for new models.

        transitions: Collection of transitions. Each element is a list or dictionary of named arguments to be passed
        onto the Transition initializer.

        send_event: When True, any arguments passed to trigger methods will be wrapped in an EventData object,
        allowing indirect and encapsulated access to data. When False, all positional and keyword arguments will be
        passed directly to all callback methods.

        auto_transitions: When True (default), every state will automatically have an associated to_{state}()
        convenience trigger in the model.

        name: Name of the Machine

        ignore_invalid_triggers: When True, any calls to trigger methods that are not valid for the present state (
        i.e., calling on a_to_b() trigger when the current state is c) will be silently ignored rather than raising
        an invalid transition exception.

        before_state_change: Callable(s) called every change state before the transition happened. It receives the
        very same args as normal callbacks.

        after_state_change: Callable(s) called every change state after the transition happened. It receives the
        very same args as normal callbacks.

        prepare_event: Callable(s) called on for before possible transitions will be processed. It receives the very
        same args as normal callbacks.

        finalize_event: Callable(s) called on for each triggered event after transitions have been processed. This is
        also called when a transition raises an exception.

        on_exception: Callable(s) called when an event raises an exception. If not set, the exception will be raised
        instead.

        **kwargs: additional arguments passed to next class in MRO. This can be ignored in most cases.
    """
    SEPARATOR = '_'
    WILDCARD_ALL = '*'
    WILDCARD_SAME = '='
    SELF_LITERAL = 'self'

    def __init__(self,
                 model: Any | list[Any] = SELF_LITERAL,
                 states: StatesParam | None = None,
                 state_attribute: str = 'state',
                 initial: StateParam = 'initial',
                 transitions: list[list[str]] | list[dict[str, str]] | None = None,
                 send_event: bool = False,
                 auto_transitions: bool = True,
                 name: str | None = None,
                 ignore_invalid_triggers: bool | None = None,
                 before_state_change: Callback | Callbacks | None = None,
                 after_state_change: Callback | Callbacks | None = None,
                 prepare_event: Callback | Callbacks | None = None,  # and so on
                 finalize_event: Callback | Callbacks | None = None,
                 on_exception: Callback | Callbacks | None = None,
                 **kwargs):
        # self._queued = queued
        self._transition_queue = deque()
        self._before_state_change = []
        self._after_state_change = []
        self._prepare_event = []
        self._finalize_event = []
        self._on_exception = []
        self._initial = None
        self.state_attribute = state_attribute
        self.send_event = send_event

        self.states: OrderedDict[str, State] = OrderedDict()
        self.events: dict[str, Event] = {}
        self.auto_transitions = auto_transitions
        self.ignore_invalid_triggers = ignore_invalid_triggers
        self.prepare_event = prepare_event
        self.before_state_change = before_state_change
        self.after_state_change = after_state_change
        self.finalize_event = finalize_event
        self.on_exception = on_exception
        self.name = name + ": " if name is not None else ""

        self._models = []

        if states is not None:
            self.add_states(states)

        if initial is not None:
            self.initial = initial

        if transitions is not None:
            self.add_transitions(transitions)

        if model:
            self.add_models(model)

    @property
    def initial(self):
        return self._initial

    @initial.setter
    def initial(self, value):
        if isinstance(value, State):
            if value.name not in self.states:
                self.add_states(value)
            self._initial = value.name
        else:
            state = value.name if isinstance(value, Enum) else value
            if state not in self.states:
                self.add_states(state)
            self._initial = state

    @property
    def models(self):
        return self._models

    @property
    def before_state_change(self):
        return self._before_state_change

    @before_state_change.setter
    def before_state_change(self, value):
        self._before_state_change = listify(value)

    @property
    def after_state_change(self):
        return self._after_state_change

    @after_state_change.setter
    def after_state_change(self, value):
        self._after_state_change = listify(value)

    @property
    def prepare_event(self):
        return self._prepare_event

    @prepare_event.setter
    def prepare_event(self, value):
        self._prepare_event = listify(value)

    @property
    def finalize_event(self):
        return self._finalize_event

    @finalize_event.setter
    def finalize_event(self, value):
        self._finalize_event = listify(value)

    @property
    def on_exception(self):
        return self._on_exception

    @on_exception.setter
    def on_exception(self, value):
        self._on_exception = listify(value)

    def get_model_state(self, model: Any):
        return self.get_state(getattr(model, self.state_attribute))

    def get_state(self, state: StateParam):
        if isinstance(state, Enum):
            state = state.name
        if state not in self.states:
            raise ValueError(f"State {repr(state)} is not a registered state.")
        return self.states[state]

    def set_state(self, model: Any, state: StateParam):
        if not isinstance(state, State):
            state = self.get_state(state)
        for model in listify(model):
            setattr(model, self.state_attribute, state.value)

    def _add_state2model(self, model: Any, state: StateParam) -> None:
        func = partial(self.is_state, model, state.value)
        attr_name = f'is_{state.name}' if self.state_attribute == 'state' \
            else f'is_{self.state_attribute}_{state.name}'
        bind2obj(model, attr_name, func)

        for dynamic_method in State.dynamic_methods:
            method = f'{dynamic_method}_{state.name}'
            # if the model has on_enter/exit_xxx attribute, and it is not registered in the according list of
            # callbacks within this state, register this callback
            if hasattr(model, method) and method not in getattr(state, dynamic_method):
                state.add_callback(dynamic_method[3:], method)

    def _add_trigger2model(self, model: Any, trigger: str) -> None:
        bind2obj(model, trigger, partial(self.events[trigger].trigger, model))

    def add_models(self, models: Any | list[Any], initial=None) -> None:
        models = listify(models)

        if initial is None:
            if self.initial is None:
                raise ValueError("No initial state configured for machine, must specify when adding models.")
            else:
                initial = self.initial

        for model in models:
            model = self if model is self.SELF_LITERAL else model
            if model not in self.models:
                def trigger_func(trigger_name: str, *args, **kwargs):
                    try:
                        event_local = self.events[trigger_name]
                    except KeyError:
                        state_local = self.get_model_state(model)
                        ignore = state_local.ignore_invalid_triggers \
                            if state_local.ignore_invalid_triggers is not None \
                            else self.ignore_invalid_triggers
                        if not ignore:
                            raise AttributeError(f"Do not know event named {trigger_name}")
                        return False
                    return event_local.trigger(model, *args, **kwargs)
                bind2obj(model, 'trigger', trigger_func)  # trigger signature changed

                for name in self.events:
                    self._add_trigger2model(model, name)
                for state in self.states.values():
                    self._add_state2model(model, state)

                self.set_state(model, initial)
                self.models.append(model)

    def remove_models(self, models: Any | list[Any]) -> None:
        models = listify(models)
        for model in models:
            self.models.remove(model)
        # if len(self._transition_queue) > 0:
        #     # possibly filter?
        #     self._transition_queue = deque(self._transition_queue[0]
        #                                    + [e for e in self._transition_queue if e.args[0] not in models])

    def is_state(self, model: Any, state: StateParam) -> bool:
        return getattr(model, self.state_attribute) == state

    def add_states(self,
                   states: StateParam | StatesParam | dict,
                   on_enter: Callback | Callbacks | None = None,
                   on_exit: Callback | Callbacks | None = None,
                   ignore_invalid_triggers: bool | None = None) -> None:
        ignore = ignore_invalid_triggers if ignore_invalid_triggers is not None else self.ignore_invalid_triggers
        for state in listify(states):
            if isinstance(state, (str, Enum)):
                state: State = State(state, on_enter, on_exit, ignore_invalid_triggers)
            elif isinstance(state, dict):
                if 'ignore_invalid_triggers' not in state:
                    state['ignore_invalid_triggers'] = ignore
                state: State = State(**state)
            self.states[state.name] = state

            for model in self.models:
                self._add_state2model(model, state)

            if self.auto_transitions:
                for other in self.states.keys():
                    if self.state_attribute == 'state':
                        method = f"to_{other}"
                    else:
                        method = f"to_{self.state_attribute}_{other}"
                    if other == state.name:
                        self.add_transition(method, self.WILDCARD_ALL, other)
                    else:
                        self.add_transition(method, state.name, other)

    """ Alias for add_states """
    add_state = add_states

    def add_transition(self,
                       trigger: str,
                       source: StateParam | StatesParam,
                       dest: StateParam,
                       conditions: Callback | Callbacks | None = None,
                       unless: Callback | Callbacks | None = None,
                       before: Callback | Callbacks | None = None,
                       after: Callback | Callbacks | None = None,
                       prepare: Callback | Callbacks | None = None,
                       **kwargs):
        if trigger == self.state_attribute:
            raise ValueError("Trigger name cannot be same as state attribute name for this machine.")
        if trigger not in self.events:
            self.events[trigger] = Event(trigger, self)
            for model in self.models:
                self._add_trigger2model(trigger, model)

        if source == Machine.WILDCARD_ALL:
            source: list[str] = list(self.states.keys())
        else:
            source: list[str] = listify(source)

        for state in source:
            if dest == self.WILDCARD_SAME:
                dest = state
            elif dest is not None:
                dest = dest.name if isinstance(dest, Enum) else dest
            else:
                dest = None
            trans = Transition(state, dest, conditions, unless, before, after, prepare, **kwargs)
            self.events[trigger].add_transition(trans)

    def add_transitions(self, transitions: list[list | dict]):
        for trans in listify(transitions):  # trans: list | dict
            if isinstance(trans, list):
                self.add_transition(*trans)
            else:
                self.add_transition(**trans)

    def triggers_from(self, *states: StateParam) -> list[str]:
        """ Collects all triggers from the given state(s).

        Args:
            *states: tuple of source state(s)

        Returns:
            list of transition/trigger name(s)
        """
        names = set(state.name if isinstance(state, Enum) else state for state in states)
        return [trigger for trigger in self.events if any(name in self.events[trigger].transitions for name in names)]

    def dispatch(self, trigger: str, *args, **kwargs) -> bool:
        return all([getattr(model, trigger)(*args, **kwargs) for model in self.models])

    def callbacks(self, funcs: Callbacks, event_data: EventData) -> None:
        for func in funcs:
            self.callback(func, event_data)

    def callback(self, func: Callback, event_data: EventData) -> None:
        func = self.resolve_callable(func, event_data)
        if self.send_event:
            func(event_data)
        else:
            func(*event_data.args, **event_data.kwargs)

    def process(self, trigger: Callable):
        return trigger()

    @staticmethod
    def resolve_callable(func: Callback, event_data: EventData) -> Callable[..., None]:
        if isinstance(func, str):
            try:
                func = getattr(event_data.model, func)
                if not callable(func):
                    def wrapper(*_, **__):
                        return func
                    return wrapper
            except AttributeError:
                try:
                    model, name = func.rsplit('.', 1)
                    m = __import__(model)
                    for n in model.split('.')[1:]:
                        m = getattr(m, n)
                    func = getattr(m, name)
                except (ImportError, AttributeError, ValueError):
                    raise AttributeError(f"Callable with name {func} could neither be retrieved from the passed model "
                                         f"nor imported from a module.")
        return func


def bind2obj(model: Any, name: str, func: Callback) -> None:
    if hasattr(model, name):
        pass  # log if needed
        return
    setattr(model, name, func)


