import fractions
import io
import pathlib
from datetime import datetime
from unittest import mock

import freezegun
import pytest
from _pytest.monkeypatch import MonkeyPatch

from shromazdeni import __main__
from shromazdeni import business


@pytest.fixture
def simple_building() -> business.Building:
    third = fractions.Fraction(1) / 3
    model = business.Building(
        [
            business.Flat("1", third, [business.Owner("Petr Novák")], {"Petr Novák"}),
            business.Flat("2", third, [business.Owner("Jana Nová")], {"Jana Nová"}),
            business.Flat(
                "3", third, [business.Owner("Oldřich Starý")], {"Oldřich Starý"}
            ),
        ]
    )
    model.add_person("Radoslava Květná")
    model.represent_flat("3", "Radoslava Květná")
    return model


@pytest.fixture
def building_with_one_owner() -> business.Building:
    share = fractions.Fraction(1) / 2
    return business.Building(
        [
            business.Flat("1", share, [business.Owner("Petr Novák")], {"Petr Novák"}),
            business.Flat(
                "2",
                share,
                [business.Owner("Petr Novák"), business.Owner("Jana Nová")],
                {"Petr Novák", "Jana Nová"},
            ),
        ]
    )


def test_flat_with_param(simple_building: business.Building) -> None:
    out = io.StringIO()
    cmd = __main__.AppCmd(simple_building, stdout=out)

    cmd.do_flat("1")

    assert out.getvalue() == "Owners:\n 1. Petr Novák\n"


def test_flat_with_representation(simple_building: business.Building) -> None:
    out = io.StringIO()
    cmd = __main__.AppCmd(simple_building, stdout=out)

    cmd.do_flat("3")

    assert out.getvalue() == (
        "Owners:\n 1. Oldřich Starý\n" "Represented by Radoslava Květná\n"
    )


def test_flat_with_bad_param(simple_building: business.Building) -> None:
    out = io.StringIO()
    cmd = __main__.AppCmd(simple_building, stdout=out)

    cmd.do_flat("10")

    assert out.getvalue() == 'Unit "10" not found.\n'


def test_flat_without_params(simple_building: business.Building) -> None:
    out = io.StringIO()
    cmd = __main__.AppCmd(simple_building, stdout=out)

    cmd.do_flat("")

    assert out.getvalue() == " 1   2  *3\n"


def test_complete_flat() -> None:
    third = fractions.Fraction(1) / 3
    model = business.Building(
        [
            business.Flat("777/1", third, [], set()),
            business.Flat("777/2", third, [], set()),
            business.Flat("778/3", third, [], set()),
        ]
    )
    cmd = __main__.AppCmd(model)

    possibilities = cmd.complete_flat("777", "flat 777/", 9, 9)

    assert possibilities == ["777/1", "777/2"]


def test_add_without_param(simple_building: business.Building) -> None:
    out = io.StringIO()
    cmd = __main__.AppCmd(simple_building, stdout=out)

    cmd.do_add("")

    assert out.getvalue() == 'No flats passed.\nuse "add [flat1] [flat2]"\n'


def test_add_with_bad_param(simple_building: business.Building) -> None:
    out = io.StringIO()
    cmd = __main__.AppCmd(simple_building, stdout=out)

    cmd.do_add("100")

    assert out.getvalue() == 'Unit "100" not found.\n'


def test_confirm_yes(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda q: "y")
    assert __main__.confirm("Question")


def test_confirm_no(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda q: "n")
    assert not __main__.confirm("Question")


@pytest.mark.parametrize("choice", ["-1", "invalid", "2"])
def test_choice_from_invalid(monkeypatch: MonkeyPatch, choice: str) -> None:
    out = io.StringIO()
    input_func = mock.Mock(side_effect=[choice, ""])
    monkeypatch.setattr("builtins.input", input_func)

    index = __main__.choice_from("Select", ["A", "B"], stdout=out)

    assert index == -1
    assert out.getvalue() == (
        "Select\n 0) A\n 1) B\n" "invalid choice\n" "Select\n 0) A\n 1) B\n"
    )


def test_choice_from(monkeypatch: MonkeyPatch) -> None:
    out = io.StringIO()
    input_func = mock.Mock(side_effect=["1"])
    monkeypatch.setattr("builtins.input", input_func)

    index = __main__.choice_from("Select", ["A", "B"], stdout=out)

    assert index == 1
    assert out.getvalue() == "Select\n 0) A\n 1) B\n"


def test_add(simple_building: business.Building, monkeypatch: MonkeyPatch) -> None:
    out = io.StringIO()
    cmd = __main__.AppCmd(simple_building, stdout=out)
    voter = business.Person("Petr Novák", datetime.min)
    choice_from = mock.Mock(return_value=2)
    monkeypatch.setattr("shromazdeni.__main__.choice_from", choice_from)

    cmd.do_add("1 2 3")

    assert out.getvalue() == (
        "1 owners:\n 1. Petr Novák\n"
        "2 owners:\n 1. Jana Nová\n"
        "Ignoring 3. It is already represented by Radoslava Květná.\n"
    )
    assert simple_building.get_flat("1").represented == voter
    assert simple_building.get_flat("2").represented == voter
    choice_from.assert_called_once_with(
        "Select representation",
        ["New Person", "Jana Nová", "Petr Novák", "Radoslava Květná"],
        out,
    )


def test_add_new_person(
    simple_building: business.Building, monkeypatch: MonkeyPatch
) -> None:
    out = io.StringIO()
    cmd = __main__.AppCmd(simple_building, stdout=out)
    voter = business.Person("Jakub Rychlý", datetime.min)
    monkeypatch.setattr("shromazdeni.__main__.choice_from", lambda *args, **kwargs: 0)
    monkeypatch.setattr("builtins.input", lambda q: "Jakub Rychlý")
    monkeypatch.setattr("shromazdeni.__main__.confirm", lambda q: True)

    cmd.do_add("1")

    assert out.getvalue() == "1 owners:\n 1. Petr Novák\n"
    assert simple_building.get_flat("1").represented == voter


def test_add_ask_for_other_unit(
    building_with_one_owner: business.Building, monkeypatch: MonkeyPatch
) -> None:
    out = io.StringIO()
    cmd = __main__.AppCmd(building_with_one_owner, stdout=out)
    voter = business.Person("Petr Novák", datetime.min)
    monkeypatch.setattr("shromazdeni.__main__.choice_from", lambda *args, **kwargs: 1)
    monkeypatch.setattr("shromazdeni.__main__.confirm", lambda q: True)

    cmd.do_add("1")

    assert out.getvalue() == (
        "1 owners:\n 1. Petr Novák\n2 owners:\n 1. Petr Novák\n 2. Jana Nová\n"
    )
    assert building_with_one_owner.get_flat("1").represented == voter
    assert building_with_one_owner.get_flat("2").represented == voter


def test_add_inform_about_extra_unit(
    building_with_one_owner: business.Building, monkeypatch: MonkeyPatch
) -> None:
    out = io.StringIO()
    cmd = __main__.AppCmd(building_with_one_owner, stdout=out)
    monkeypatch.setattr("shromazdeni.__main__.choice_from", lambda *args, **kwargs: 1)
    monkeypatch.setattr("shromazdeni.__main__.confirm", lambda q: True)

    cmd.do_add("2")

    assert out.getvalue() == (
        "2 owners:\n 1. Petr Novák\n 2. Jana Nová\n"
        "Should Jana Nová also represent: 1?\n"
    )


def test_complete_remove() -> None:
    third = fractions.Fraction(1) / 3
    model = business.Building(
        [
            business.Flat(
                "777/1",
                third,
                [],
                set(),
                represented=business.Person("Radoslava Květná", datetime.min),
            )
        ]
    )
    cmd = __main__.AppCmd(model)
    model.add_person("Peter Pan")

    possibilities = cmd.complete_remove("", "remove ", 9, 9)

    assert possibilities == ["777/1", "Peter Pan"]


def test_remove_with_empty_args(simple_building: business.Building) -> None:
    out = io.StringIO()
    cmd = __main__.AppCmd(simple_building, stdout=out)

    cmd.do_remove("")

    assert out.getvalue().startswith("No argument")


def test_remove_with_bad_args(simple_building: business.Building) -> None:
    out = io.StringIO()
    cmd = __main__.AppCmd(simple_building, stdout=out)

    cmd.do_remove("A")

    assert out.getvalue() == '"A" is neither flat or person.\n'


def test_remove_with_not_represented_flat(simple_building: business.Building) -> None:
    out = io.StringIO()
    cmd = __main__.AppCmd(simple_building, stdout=out)

    cmd.do_remove("1")

    assert out.getvalue() == '"1" is not represented.\n'


def test_remove_with_flat(simple_building: business.Building) -> None:
    out = io.StringIO()
    cmd = __main__.AppCmd(simple_building, stdout=out)

    cmd.do_remove("3")

    assert out.getvalue() == (
        "Radoslava Květná no longer represents 3.\n" "Radoslava Květná left.\n"
    )
    assert not simple_building.get_flat("3").represented
    assert not simple_building.get_person_names("Radoslava Květná")


def test_remove_with_flat_person_represents_more_flats(
    simple_building: business.Building,
) -> None:
    out = io.StringIO()
    simple_building.represent_flat("1", "Radoslava Květná")
    cmd = __main__.AppCmd(simple_building, stdout=out)

    cmd.do_remove("3")

    assert out.getvalue() == "Radoslava Květná no longer represents 3.\n"
    assert not simple_building.get_flat("3").represented
    assert simple_building.get_flat("1").represented
    assert simple_building.get_person_names("Radoslava Květná")


def test_remove_with_person(simple_building: business.Building) -> None:
    out = io.StringIO()
    cmd = __main__.AppCmd(simple_building, stdout=out)

    cmd.do_remove("Radoslava Květná")

    assert out.getvalue() == (
        "Radoslava Květná no longer represents 3.\n" "Radoslava Květná left.\n"
    )
    assert not simple_building.get_flat("3").represented
    assert not simple_building.get_person_names("Radoslava Květná")


@freezegun.freeze_time("2017-01-14")
def test_default_log_name() -> None:
    assert __main__.CommandLogger.default_logname("flats.json") == "flats.20170114.log"


def test_parse_logfile() -> None:
    model = mock.Mock()
    fin = io.StringIO(
        """\
date,function,args
10:01,command1,1,2,3
10:02,command2,"string"
"""
    )

    __main__.CommandLogger.parse_logfile(fin, model)

    model.command1.assert_called_once_with("1", "2", "3")
    model.command2.assert_called_once_with("string")


def test_create_logfile(tmp_path: pathlib.Path) -> None:
    filepath = tmp_path / "file.tmp"

    __main__.CommandLogger.create_logfile(filepath)

    with open(filepath, "r") as fin:
        content = fin.read()
    assert content == "date,operation,*args\n"


@business.log_command
def fake_operation(model: business.Building, a: str, b: str) -> int:
    del model  # Unused
    del a  # Unused
    del b  # Unused
    return 1


def test_log_command_decorator() -> None:
    model = mock.Mock()

    result = fake_operation(model, "operand1", "operand2")

    assert result == 1
    model._logger.log.assert_called_once_with(
        "fake_operation", ("operand1", "operand2")
    )


@freezegun.freeze_time("2017-01-14T10:22")
def test_logger_log() -> None:
    fout = io.StringIO()
    logger = __main__.CommandLogger(fout)

    logger.log("operation", ("a", "b"))

    assert fout.getvalue() == "10:22,operation,a,b\r\n"


if __name__ == "__main__":
    pytest.main()
