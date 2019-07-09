import fractions
import io
from unittest import mock

import pytest

import shromazdeni


def test_format_persons_single_person():
    address = "Novák Jan, Pařížská 32, Praha 1"
    assert shromazdeni.format_persons(address) == [address]


def test_format_persons_sjm():
    address = "SJM Novák Jan a Nováková Petra, Pařížská 32, Praha 1"
    assert shromazdeni.format_persons(address) == [
        "Novák Jan, Pařížská 32, Praha 1",
        "Nováková Petra, Pařížská 32, Praha 1",
    ]


@pytest.fixture
def simple_building():
    third = fractions.Fraction(1) / 3
    return shromazdeni.Building(
        [
            shromazdeni.Flat("1", third, ["Petr Novák"]),
            shromazdeni.Flat("2", third, ["Jana Nová"]),
            shromazdeni.Flat(
                "3",
                third,
                ["Oldřich Starý"],
                represented=shromazdeni.Person("Jana Nová"),
            ),
        ]
    )


def test_flat_with_param(simple_building):
    out = io.StringIO()
    cmd = shromazdeni.AppCmd(simple_building, stdout=out)

    cmd.do_flat("1")

    assert out.getvalue() == "Owners:\n 1. Petr Novák\n"


def test_flat_with_representation(simple_building):
    out = io.StringIO()
    cmd = shromazdeni.AppCmd(simple_building, stdout=out)

    cmd.do_flat("3")

    assert out.getvalue() == (
        "Owners:\n 1. Oldřich Starý\n" "Represented by Jana Nová\n"
    )


def test_flat_with_bad_param(simple_building):
    out = io.StringIO()
    cmd = shromazdeni.AppCmd(simple_building, stdout=out)

    cmd.do_flat("10")

    assert out.getvalue() == 'Unit "10" not found.\n'


def test_flat_without_params(simple_building):
    out = io.StringIO()
    cmd = shromazdeni.AppCmd(simple_building, stdout=out)

    cmd.do_flat("")

    assert out.getvalue() == " 1   2  *3\n"


def test_complete_flat():
    third = fractions.Fraction(1) / 3
    building = shromazdeni.Building(
        [
            shromazdeni.Flat("777/1", third, []),
            shromazdeni.Flat("777/2", third, []),
            shromazdeni.Flat("778/3", third, []),
        ]
    )
    cmd = shromazdeni.AppCmd(building)

    possibilities = cmd.complete_flat("777", "flat 777/", 9, 9)

    assert possibilities == ["777/1", "777/2"]


def test_load_json():
    json_flats = [
        {"name": "1", "fraction": "1/3", "owners": [{"name": "P1", "fraction": "1"}]},
        {"name": "2", "fraction": "2/3", "owners": [{"name": "P2", "fraction": "1"}]},
    ]

    building = shromazdeni.Building.load(json_flats)

    unit = fractions.Fraction(1)
    assert building.flats == [
        shromazdeni.Flat("1", unit / 3, ["P1"]),
        shromazdeni.Flat("2", unit * 2 / 3, ["P2"]),
    ]


def test_load_json_shorten_names():
    json_flats = [
        {"name": "100/1", "fraction": "1/3", "owners": []},
        {"name": "100/2", "fraction": "2/3", "owners": []},
    ]

    building = shromazdeni.Building.load(json_flats)

    unit = fractions.Fraction(1)
    assert building.flats == [
        shromazdeni.Flat("1", unit / 3, []),
        shromazdeni.Flat("2", unit * 2 / 3, []),
    ]


def test_add_without_param(simple_building):
    out = io.StringIO()
    cmd = shromazdeni.AppCmd(simple_building, stdout=out)

    cmd.do_add("")

    assert out.getvalue() == 'No flats passed.\nuse "add [flat1] [flat2]"\n'


def test_add_with_bad_param(simple_building):
    out = io.StringIO()
    cmd = shromazdeni.AppCmd(simple_building, stdout=out)

    cmd.do_add("100")

    assert out.getvalue() == 'Unit "100" not found.\n'


def test_confirm_yes(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda q: "y")
    assert shromazdeni.confirm("Question")


def test_confirm_no(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda q: "n")
    assert not shromazdeni.confirm("Question")


@pytest.mark.parametrize("choice", ["-1", "invalid", "2"])
def test_choice_from_invalid(monkeypatch, choice):
    out = io.StringIO()
    input_func = mock.Mock(side_effect=[choice, ""])
    monkeypatch.setattr("builtins.input", input_func)

    index = shromazdeni.choice_from("Select", ["A", "B"], stdout=out)

    assert index == -1
    assert out.getvalue() == (
        "Select\n 0) A\n 1) B\n" "invalid choice\n" "Select\n 0) A\n 1) B\n"
    )


def test_choice_from(monkeypatch):
    out = io.StringIO()
    input_func = mock.Mock(side_effect=["1"])
    monkeypatch.setattr("builtins.input", input_func)

    index = shromazdeni.choice_from("Select", ["A", "B"], stdout=out)

    assert index == 1
    assert out.getvalue() == "Select\n 0) A\n 1) B\n"


def test_add(simple_building, monkeypatch):
    out = io.StringIO()
    cmd = shromazdeni.AppCmd(simple_building, stdout=out)
    voter = shromazdeni.Person("Petr Novák")
    choice_from = mock.Mock(return_value=3)
    monkeypatch.setattr("shromazdeni.choice_from", choice_from)

    cmd.do_add("1 2 3")

    assert out.getvalue() == (
        "1 owners:\n 1. Petr Novák\n"
        "2 owners:\n 1. Jana Nová\n"
        "Ignoring 3. It is already represented by Jana Nová.\n"
    )
    assert simple_building.get_flat("1").represented == voter
    assert simple_building.get_flat("2").represented == voter
    assert choice_from.called_once_with("Select representation", [], out)


def test_add_new_person(simple_building, monkeypatch):
    out = io.StringIO()
    cmd = shromazdeni.AppCmd(simple_building, stdout=out)
    voter = shromazdeni.Person("Jakub Rychlý")
    monkeypatch.setattr("shromazdeni.choice_from", lambda *args, **kwargs: 0)
    monkeypatch.setattr("builtins.input", lambda q: "Jakub Rychlý")
    monkeypatch.setattr("shromazdeni.confirm", lambda q: True)

    cmd.do_add("1")

    assert out.getvalue() == ("1 owners:\n 1. Petr Novák\n")
    assert simple_building.get_flat("1").represented == voter


if __name__ == "__main__":
    pytest.main()
