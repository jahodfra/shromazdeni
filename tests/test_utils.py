import fractions

import pytest

from shromazdeni import business
from shromazdeni import utils


def test_format_persons_single_person() -> None:
    address = "Novák Jan, Pařížská 32, Praha 1"
    assert utils.format_persons(address) == [address]


def test_format_persons_sjm() -> None:
    address = "SJM Novák Jan a Nováková Petra, Pařížská 32, Praha 1"
    assert utils.format_persons(address) == [
        "Novák Jan, Pařížská 32, Praha 1",
        "Nováková Petra, Pařížská 32, Praha 1",
    ]


def test_load_json() -> None:
    json_flats = [
        {"name": "1", "fraction": "1/3", "owners": [{"name": "P1", "fraction": "1"}]},
        {"name": "2", "fraction": "2/3", "owners": [{"name": "P2", "fraction": "1"}]},
    ]

    flats = utils.from_json_to_flats(json_flats)

    unit = fractions.Fraction(1)
    assert flats == [
        business.Flat(
            name="1",
            original_name="1",
            fraction=unit / 3,
            owners=[business.Owner("P1")],
            persons={"P1"},
        ),
        business.Flat(
            name="2",
            original_name="2",
            fraction=unit * 2 / 3,
            owners=[business.Owner("P2")],
            persons={"P2"},
        ),
    ]


def test_load_json_shorten_names() -> None:
    json_flats = [
        {"name": "100/1", "fraction": "1/3", "owners": []},
        {"name": "100/2", "fraction": "2/3", "owners": []},
    ]

    flats = utils.from_json_to_flats(json_flats)

    unit = fractions.Fraction(1)
    assert flats == [
        business.Flat(
            name="1", original_name="100/1", fraction=unit / 3, owners=[], persons=set()
        ),
        business.Flat(
            name="2",
            original_name="100/2",
            fraction=unit * 2 / 3,
            owners=[],
            persons=set(),
        ),
    ]


if __name__ == "__main__":
    pytest.main()
