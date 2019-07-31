import fractions
from dataclasses import dataclass
from typing import List, Optional, Set


@dataclass
class Person:
    """Represents a person present on the gathering."""

    name: str
    # Eventually it will contain a code


@dataclass
class Owner:
    name: str
    fraction: fractions.Fraction = fractions.Fraction(1)


@dataclass
class Flat:
    name: str
    fraction: fractions.Fraction
    owners: List[Owner]  # Owner can be SJM
    represented: Optional[Person] = None

    @property
    def sort_key(self):
        return tuple(int(n) for n in self.name.split("/"))

    @property
    def nice_name(self):
        return ("*" if self.represented else " ") + self.name

    @property
    def persons(self) -> Set[str]:
        return set(
            person for owner in self.owners for person in format_persons(owner.name)
        )


def _convert_flat(flat, shorten_name):
    if shorten_name:
        shortname = flat["name"].split("/", 1)[1]
    else:
        shortname = flat["name"]

    owners = []
    for json_owner in flat["owners"]:
        owners.append(
            Owner(
                name=json_owner["name"],
                fraction=fractions.Fraction(json_owner["fraction"]),
            )
        )
    return Flat(
        name=shortname, owners=owners, fraction=fractions.Fraction(flat["fraction"])
    )


def from_json_to_flats(json_flats):
    prefixes = set(flat["name"].split("/")[0] for flat in json_flats)
    shorten_name = len(prefixes) == 1
    flats = [_convert_flat(flat, shorten_name) for flat in json_flats]
    flats.sort(key=lambda flat: flat.sort_key)
    return flats


def format_persons(name: str) -> List[str]:
    if name.startswith("SJM"):
        name = name[3:].strip()
        names, address = name.split(",", 1)
        address = address.strip()
        name1, name2 = names.split(" a ")
        return [", ".join((name1, address)), ", ".join((name2, address))]
    else:
        return [name]
