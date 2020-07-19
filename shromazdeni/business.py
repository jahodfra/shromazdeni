"""
Main business model for the application

The module shouldn't depend on other parts of the package.
"""

import collections
import fractions
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Callable, cast, Dict, List, Optional, Set, Tuple, TypeVar
from typing_extensions import Protocol


@dataclass
class Person:
    """Represents a person present on the gathering."""

    name: str
    created_at: datetime
    # Eventually it will contain a code

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Person) and self.name == other.name


@dataclass
class Owner:
    name: str
    fraction: fractions.Fraction = fractions.Fraction(1)


@dataclass
class Flat:
    name: str
    fraction: fractions.Fraction
    owners: List[Owner]  # Owner can be SJM
    persons: Set[str]
    represented: Optional[Person] = None

    @property
    def sort_key(self) -> Tuple[int, ...]:
        return tuple(int(n) for n in self.name.split("/"))

    @property
    def nice_name(self) -> str:
        return ("*" if self.represented else " ") + self.name


class CommandLogger(Protocol):
    def log(self, func_name: str, args: Tuple) -> None:
        pass


FuncType = Callable[..., Any]
F = TypeVar("F", bound=FuncType)


def log_command(func: F) -> F:
    def wrapper(self: "Building", *args: str) -> Any:
        result = func(self, *args)
        # On success
        if self._logger:
            self._logger.log(func.__name__, args)
        return result

    return cast(F, wrapper)


class Building:
    """Abstraction layer above json file from the parser."""

    def __init__(self, flats: List[Flat]):
        self._flats = collections.OrderedDict((flat.name, flat) for flat in flats)
        self._present_persons: Dict[str, Person] = {}
        self._logger: Optional[CommandLogger] = None

    def register_logger(self, logger: CommandLogger) -> None:
        self._logger = logger

    @property
    def flats(self) -> List[Flat]:
        return list(self._flats.values())

    def get_flat(self, shortname: str) -> Flat:
        return self._flats[shortname]

    @property
    def percent_represented(self) -> float:
        return sum(flat.fraction for flat in self.flats if flat.represented) * 100

    @log_command
    def represent_flat(self, flat_name: str, person_name: str) -> None:
        person = self._present_persons[person_name]
        self._flats[flat_name].represented = person

    def person_exists(self, name: str) -> bool:
        return name in self._present_persons

    @log_command
    def add_person(self, name: str) -> None:
        assert not self.person_exists(name)
        self._present_persons[name] = Person(name, datetime.now())

    @log_command
    def remove_flat_representative(self, flat_name: str) -> None:
        flat = self._flats[flat_name]
        person = flat.represented
        if person:
            self._remove_flat_representative(flat_name)

    def _remove_flat_representative(self, flat_name: str) -> None:
        self._flats[flat_name].represented = None

    @log_command
    def remove_person(self, name: str) -> List[str]:
        person_flats = self.get_representative_flats(name)
        for flat_name in person_flats:
            self._remove_flat_representative(flat_name)
        del self._present_persons[name]
        return person_flats

    def get_representative_flats(self, person_name: str) -> List[str]:
        return [
            flat.name
            for flat in self.flats
            if flat.represented and flat.represented.name == person_name
        ]

    def get_person_names(self, prefix: str) -> List[str]:
        return [n for n in self._present_persons if n.startswith(prefix)]

    def get_other_representatives(self, person_name: str) -> List[str]:
        flats = []
        for flat in self._flats.values():
            if not flat.represented and person_name in flat.persons:
                flats.append(flat.name)
        flats.sort()
        return flats
