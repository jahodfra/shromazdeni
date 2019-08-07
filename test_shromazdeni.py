import fractions
import io
from datetime import datetime
from unittest import mock

import freezegun
import pytest

import shromazdeni
import utils


@pytest.fixture
def simple_building():
    third = fractions.Fraction(1) / 3
    model = shromazdeni.Model(
        [
            utils.Flat("1", third, [utils.Owner("Petr Novák")]),
            utils.Flat("2", third, [utils.Owner("Jana Nová")]),
            utils.Flat("3", third, [utils.Owner("Oldřich Starý")]),
        ]
    )
    model.add_person("Radoslava Květná")
    model.represent_flat("3", "Radoslava Květná")
    return model


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
        "Owners:\n 1. Oldřich Starý\n" "Represented by Radoslava Květná\n"
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
    model = shromazdeni.Model(
        [
            utils.Flat("777/1", third, []),
            utils.Flat("777/2", third, []),
            utils.Flat("778/3", third, []),
        ]
    )
    cmd = shromazdeni.AppCmd(model)

    possibilities = cmd.complete_flat("777", "flat 777/", 9, 9)

    assert possibilities == ["777/1", "777/2"]


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
    voter = utils.Person("Petr Novák", datetime.min)
    choice_from = mock.Mock(return_value=2)
    monkeypatch.setattr("shromazdeni.choice_from", choice_from)

    cmd.do_add("1 2 3")

    assert out.getvalue() == (
        "1 owners:\n 1. Petr Novák\n"
        "2 owners:\n 1. Jana Nová\n"
        "Ignoring 3. It is already represented by Radoslava Květná.\n"
    )
    assert simple_building.get_flat("1").represented.name == voter.name
    assert simple_building.get_flat("2").represented.name == voter.name
    choice_from.assert_called_once_with(
        "Select representation",
        ["New Person", "Jana Nová", "Petr Novák", "Radoslava Květná"],
        out,
    )


def test_add_new_person(simple_building, monkeypatch):
    out = io.StringIO()
    cmd = shromazdeni.AppCmd(simple_building, stdout=out)
    voter = utils.Person("Jakub Rychlý", datetime.min)
    monkeypatch.setattr("shromazdeni.choice_from", lambda *args, **kwargs: 0)
    monkeypatch.setattr("builtins.input", lambda q: "Jakub Rychlý")
    monkeypatch.setattr("shromazdeni.confirm", lambda q: True)

    cmd.do_add("1")

    assert out.getvalue() == "1 owners:\n 1. Petr Novák\n"
    assert simple_building.get_flat("1").represented.name == voter.name


def test_complete_remove():
    third = fractions.Fraction(1) / 3
    model = shromazdeni.Model(
        [
            utils.Flat(
                "777/1",
                third,
                [],
                represented=utils.Person("Radoslava Květná", datetime.min),
            )
        ]
    )
    cmd = shromazdeni.AppCmd(model)
    model.add_person("Peter Pan")

    possibilities = cmd.complete_remove("", "remove ", 9, 9)

    assert possibilities == ["777/1", "Peter Pan"]


def test_remove_with_empty_args(simple_building):
    out = io.StringIO()
    cmd = shromazdeni.AppCmd(simple_building, stdout=out)

    cmd.do_remove("")

    assert out.getvalue().startswith("No argument")


def test_remove_with_bad_args(simple_building):
    out = io.StringIO()
    cmd = shromazdeni.AppCmd(simple_building, stdout=out)

    cmd.do_remove("A")

    assert out.getvalue() == '"A" is neither flat or person.\n'


def test_remove_with_not_represented_flat(simple_building):
    out = io.StringIO()
    cmd = shromazdeni.AppCmd(simple_building, stdout=out)

    cmd.do_remove("1")

    assert out.getvalue() == '"1" is not represented.\n'


def test_remove_with_flat(simple_building):
    out = io.StringIO()
    cmd = shromazdeni.AppCmd(simple_building, stdout=out)

    cmd.do_remove("3")

    assert out.getvalue() == (
        "Radoslava Květná no longer represents 3.\n" "Radoslava Květná left.\n"
    )
    assert not simple_building.get_flat("3").represented
    assert not simple_building.get_person_names("Radoslava Květná")


def test_remove_with_flat_person_represents_more_flats(simple_building):
    out = io.StringIO()
    simple_building.represent_flat("1", "Radoslava Květná")
    cmd = shromazdeni.AppCmd(simple_building, stdout=out)

    cmd.do_remove("3")

    assert out.getvalue() == "Radoslava Květná no longer represents 3.\n"
    assert not simple_building.get_flat("3").represented
    assert simple_building.get_flat("1").represented
    assert simple_building.get_person_names("Radoslava Květná")


def test_remove_with_person(simple_building):
    out = io.StringIO()
    cmd = shromazdeni.AppCmd(simple_building, stdout=out)

    cmd.do_remove("Radoslava Květná")

    assert out.getvalue() == (
        "Radoslava Květná no longer represents 3.\n" "Radoslava Květná left.\n"
    )
    assert not simple_building.get_flat("3").represented
    assert not simple_building.get_person_names("Radoslava Květná")


@freezegun.freeze_time("2017-01-14")
def test_default_log_name():
    assert (
        shromazdeni.CommandLogger.default_logname("flats.json") == "flats.20170114.log"
    )


def test_parse_logfile():
    model = mock.Mock()
    fin = io.StringIO(
        """\
date,function,args
10:01,command1,1,2,3
10:02,command2,"string"
"""
    )

    shromazdeni.CommandLogger.parse_logfile(fin, model)

    model.command1.assert_called_once_with("1", "2", "3")
    model.command2.assert_called_once_with("string")


def test_create_logfile(tmp_path):
    filepath = tmp_path / "file.tmp"

    shromazdeni.CommandLogger.create_logfile(filepath)

    with open(filepath, "r") as fin:
        content = fin.read()
    assert content == "date,operation,*args\n"


@shromazdeni.log_command
def fake_operation(model, a, b):
    del model  # Unused
    del a  # Unused
    del b  # Unused
    return 1


def test_log_command_decorator():
    model = mock.Mock()

    result = fake_operation(model, "operand1", "operand2")

    assert result == 1
    model._logger.log.assert_called_once_with(
        "fake_operation", ("operand1", "operand2")
    )


@freezegun.freeze_time("2017-01-14T10:22")
def test_logger_log():
    fout = io.StringIO()
    logger = shromazdeni.CommandLogger(fout)

    logger.log("operation", ("a", "b"))

    assert fout.getvalue() == "10:22,operation,a,b\r\n"


if __name__ == "__main__":
    pytest.main()
