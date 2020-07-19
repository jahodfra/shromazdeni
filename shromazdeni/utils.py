import fractions
from shromazdeni import business
from typing import Dict, List


def _convert_flat(flat: Dict, shorten_name: bool) -> business.Flat:
    if shorten_name:
        shortname = flat["name"].split("/", 1)[1]
    else:
        shortname = flat["name"]

    owners = []
    for json_owner in flat["owners"]:
        owners.append(
            business.Owner(
                name=json_owner["name"],
                fraction=fractions.Fraction(json_owner["fraction"]),
            )
        )
    persons = set(person for owner in owners for person in format_persons(owner.name))
    return business.Flat(
        name=shortname,
        owners=owners,
        fraction=fractions.Fraction(flat["fraction"]),
        persons=persons,
    )


def from_json_to_flats(json_flats: List) -> List[business.Flat]:
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
