import fractions
from shromazdeni import business
from typing import Dict, List, Any


def _convert_flat(flat: Dict, shorten_name: bool) -> business.Flat:
    name = flat["name"]
    if shorten_name:
        shortname = name.split("/", 1)[1]
    else:
        shortname = name

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
        original_name=name,
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


def from_owners_to_json(owners: List[business.Owner]) -> List[Dict[str, Any]]:
    return [{"name": owner.name, "fraction": str(owner.fraction)} for owner in owners]


def from_flats_to_json(flats: List[business.Flat]) -> List[Dict[str, Any]]:
    return [
        {
            "name": flat.original_name,
            "fraction": str(flat.fraction),
            "owners": from_owners_to_json(flat.owners),
        }
        for flat in flats
    ]


def format_persons(name: str) -> List[str]:
    if name.startswith("SJM"):
        name = name[3:].strip()
        names, address = name.split(",", 1)
        address = address.strip()
        name1, name2 = names.split(" a ")
        return [", ".join((name1, address)), ", ".join((name2, address))]
    else:
        return [name]
