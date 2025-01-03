from functools import total_ordering
from abc import ABC, abstractmethod
from .connection import Connection, OpenConnection


@total_ordering
class Visitor(ABC):
    """
    An abstract class, generalizing for both StopVisitor and TripVisitor.

    Derived classes need to implement the ordering methods _equal() and __lt__(),
    which should compare by the datetime of the next event (departure or stop).
    They should also implement the next() method.
    """

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Visitor):
            return self._equal(other)
        return NotImplemented
    
    @abstractmethod
    def _equal(self, other: "Visitor") -> bool:
        """Defined separately from __eq__() for typing reasons."""
        pass

    @abstractmethod
    def __lt__(self, other: "Visitor") -> bool:
        pass

    @abstractmethod
    def next(self, visited_stops: dict[str, Connection], visited_trips: dict[str, OpenConnection]) -> list["Visitor"]:
        """
        Handle the next event (departure or stop).

        :param visited_stops: A dictionary with the current best Connections to all stops that have already been reached. \
        The function can mutate this dictionary.
        :param visited_trips: A dictionary with the current best OpenConnections to all trips that have already been reached. \
        The function can mutate this dictionary.
        :returns: A list of Visitors that should be enqueued.
        """
