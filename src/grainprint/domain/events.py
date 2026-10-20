from typing import Dict, List, Callable, Any
from dataclasses import dataclass
from enum import StrEnum, auto


class EventType(StrEnum):
    NAVIGATE_TO_ENTITY = auto()
    NAVIGATE_TO_MARKER = auto()
    ENTITY_CREATED = auto()
    ENTITY_UPDATED = auto()
    ENTITY_DELETED = auto()
    REFRESH_VIEWS = auto()


@dataclass
class Event:
    type: EventType
    data: Dict[str, Any]


class EventBus:
    _instance = None
    _listeners: Dict[EventType, List[Callable]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._listeners = {}
        return cls._instance

    def subscribe(self, event_type: EventType, handler: Callable[[Event],
                                                                 None]):
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable[[Event],
                                                                   None]):
        if event_type in self._listeners:
            self._listeners[event_type].remove(handler)

    def emit(self, event: Event):
        if event.type in self._listeners:
            for handler in self._listeners[event.type]:
                handler(event)

    def emit_navigate_to_entity(self, entity_type: str, entity_id: int):
        self.emit(
            Event(type=EventType.NAVIGATE_TO_ENTITY,
                  data={
                      'entity_type': entity_type,
                      'entity_id': entity_id
                  }))

    def emit_navigate_to_marker(self, marker_id: int):
        self.emit(
            Event(type=EventType.NAVIGATE_TO_MARKER,
                  data={'marker_id': marker_id}))

    def emit_entity_created(self, entity_type: str, entity_id: int):
        self.emit(
            Event(type=EventType.ENTITY_CREATED,
                  data={
                      'entity_type': entity_type,
                      'entity_id': entity_id
                  }))

    def emit_entity_updated(self, entity_type: str, entity_id: int):
        self.emit(
            Event(type=EventType.ENTITY_UPDATED,
                  data={
                      'entity_type': entity_type,
                      'entity_id': entity_id
                  }))

    def emit_entity_deleted(self, entity_type: str, entity_id: int):
        self.emit(
            Event(type=EventType.ENTITY_DELETED,
                  data={
                      'entity_type': entity_type,
                      'entity_id': entity_id
                  }))

    def emit_refresh_views(self):
        self.emit(Event(type=EventType.REFRESH_VIEWS, data={}))
