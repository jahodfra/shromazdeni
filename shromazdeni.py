import argparse
import cmd
import collections
import csv
import json
import locale
import os
import pathlib
from datetime import datetime
from typing import (
    Any,
    Callable,
    cast,
    Dict,
    IO,
    List,
    Optional,
    Set,
    TextIO,
    Tuple,
    TypeVar,
    Union,
)

import utils


def setup_readline_if_available() -> None:
    # Slash is used as part of flat names.
    # We don't want to split the names so we can have simple auto completers.
    try:
        import readline

        delims = readline.get_completer_delims().replace("/", "")
        readline.set_completer_delims(delims)
    except ImportError:
        pass


def choice_from(title: str, choices: List[str], stdout: IO[str]) -> int:
    while True:
        stdout.write(title + "\n")
        for i, choice in enumerate(choices):
            stdout.write(f"{i:2d}) {choice}\n")
        line = input("Choice [empty to cancel]> ")

        if not line or line.isspace():
            return -1
        try:
            index = int(line)
            if 0 <= index < len(choices):
                return index
        except ValueError:
            pass
        stdout.write("invalid choice\n")


def confirm(question: str) -> bool:
    return input(f"\n{question} [yN]> ").lower() == "y"


FuncType = Callable[..., Any]
F = TypeVar("F", bound=FuncType)


def log_command(func: F) -> F:
    def wrapper(self: "Model", *args: str) -> Any:
        result = func(self, *args)
        # On success
        if self._logger:
            self._logger.log(func.__name__, args)
        return result

    return cast(F, wrapper)


class CommandLogger:
    def __init__(self, logfile: IO[str]):
        self._logfile = logfile
        self._writer = csv.writer(logfile)

    @staticmethod
    def default_logname(flats_filename: str) -> str:
        now = datetime.now().strftime("%Y%m%d")
        filename, _ext = os.path.splitext(flats_filename)
        filename += f".{now}.log"
        return filename

    @staticmethod
    def parse_logfile(logfile: IO[str], model: "Model") -> None:
        reader = csv.reader(logfile)
        next(reader)
        for row in reader:
            func = row[1]
            getattr(model, func)(*row[2:])

    @staticmethod
    def create_logfile(filename: Union[str, pathlib.Path]) -> TextIO:
        fout = open(filename, "w")
        writer = csv.writer(fout)
        writer.writerow(["date", "operation", "*args"])
        return fout

    def log(self, func_name: str, args: Tuple) -> None:
        assert all(isinstance(arg, str) for arg in args)
        now = datetime.now().strftime("%H:%M")
        row = [now, func_name]
        row += args
        self._writer.writerow(row)
        self._logfile.flush()


class Model:
    """Abstraction layer above json file from the parser."""

    def __init__(self, flats: List[utils.Flat]):
        self._flats = collections.OrderedDict((flat.name, flat) for flat in flats)
        self._present_persons: Dict[str, utils.Person] = {}
        self._logger: Optional[CommandLogger] = None

    def register_logger(self, logger: CommandLogger) -> None:
        self._logger = logger

    @property
    def flats(self) -> List[utils.Flat]:
        return list(self._flats.values())

    def get_flat(self, shortname: str) -> utils.Flat:
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
        self._present_persons[name] = utils.Person(name, datetime.now())

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


class AppCmd(cmd.Cmd):
    def __init__(
        self,
        model: Model,
        completekey: str = "tab",
        stdin: IO[str] = None,
        stdout: IO[str] = None,
    ):
        self.pm_index = 1
        self.model = model
        self.set_prompt()
        super().__init__(completekey=completekey, stdin=stdin, stdout=stdout)

    def set_prompt(self) -> None:
        percent = self.model.percent_represented
        can_start = "Y" if percent > 50 else "N"
        self.prompt = f"{can_start}{float(percent):.1f}> "

    def do_flat(self, args: str) -> None:
        """List all flats in the building or prints flat details."""
        args = args.strip()
        if args:
            try:
                flat = self.model.get_flat(args)
            except KeyError:
                self.stdout.write(f'Unit "{args}" not found.\n')
                return
            self.stdout.write("Owners:\n")
            for i, owner in enumerate(flat.owners, start=1):
                self.stdout.write(f"{i:2d}. {owner.name}\n")
            if flat.represented:
                self.stdout.write(f"Represented by {flat.represented.name}\n")
        else:
            self.columnize([flat.nice_name for flat in self.model.flats])

    def complete_flat(self, text: str, line: str, beginx: int, endx: int) -> List[str]:
        return [flat.name for flat in self.model.flats if flat.name.startswith(text)]

    def _write_flat_owners(self, flat: utils.Flat) -> None:
        self.stdout.write(f"{flat.name} owners:\n")
        for i, owner in enumerate(flat.owners, start=1):
            self.stdout.write(f"{i:2d}. {owner.name}\n")

    def do_add(self, args: str) -> None:
        """Adds the representation for flats."""
        # The command seems bit nonintuitive.
        # We first enter name of flat so we don't have to
        # enter the name of owner in the most common case.
        args = args.strip()
        if not args:
            self.stdout.write('No flats passed.\nuse "add [flat1] [flat2]"\n')
            return

        persons = set()
        flats = [arg.strip() for arg in args.split(" ")]
        new_flats = []
        try:
            for fname in flats:
                flat = self.model.get_flat(fname)
                if flat.represented:
                    # We can reference a represented flat just to populate
                    # a list of persons.
                    persons.add(flat.represented.name)
                    self.stdout.write(
                        f"Ignoring {fname}. It is already "
                        f"represented by {flat.represented.name}.\n"
                    )
                else:
                    persons.update(flat.persons)
                    new_flats.append(fname)
                    self._write_flat_owners(flat)
        except KeyError:
            self.stdout.write(f'Unit "{fname}" not found.\n')
            return
        flats = new_flats
        if not flats:
            return
        name = self._choose_person(persons)
        if not name:
            return
        represented_persons = set()
        # Assign a representative
        for fname in flats:
            self.model.represent_flat(fname, name)
            represented_persons.update(self.model.get_flat(fname).persons)
        # Check if the added person doesn't have other shares in the building.
        # e.g. another flat or a share on garage hall.
        other_flats = self.model.get_other_representatives(name)
        for other_flat in other_flats:
            self._write_flat_owners(self.model.get_flat(other_flat))
            if confirm(f"Should the person also represent flat {other_flat}?"):
                self.model.represent_flat(other_flat, name)
                represented_persons.update(self.model.get_flat(other_flat).persons)
        # Write what all represented persons also own.
        # that's important for garage hall.
        hints = []
        for flat in self.model.flats:
            if not flat.represented and represented_persons & flat.persons:
                hints.append(flat.name)
        if hints:
            hint_str = ", ".join(hints)
            self.stdout.write(f"Should {name} also represent: {hint_str}?\n")
        self.set_prompt()

    def _choose_person(self, persons: Set[str]) -> Optional[str]:
        options = ["New Person"] + sorted(persons)
        owner_index = choice_from("Select representation", options, self.stdout)
        if owner_index == -1:
            return None
        if owner_index == 0:
            name = input("Name: ")
            if not confirm("Create new person?"):
                return None
        else:
            name = options[owner_index]
        if not self.model.person_exists(name):
            # Prevent creating already existing person.
            self.model.add_person(name)
        return name

    complete_add = complete_flat

    def _remove_person(self, person_name: str) -> None:
        for flat in self.model.remove_person(person_name):
            self.stdout.write(f"{person_name} no longer represents {flat}.\n")
        self.stdout.write(f"{person_name} left.\n")

    def do_remove(self, args: str) -> None:
        """Removes person or flat representative."""
        args = args.strip()
        if not args:
            self.stdout.write('No argument. Use "remove [flat or person]"\n')
            return
        try:
            flat = self.model.get_flat(args)
        except KeyError:
            pass
        else:
            if not flat.represented:
                self.stdout.write(f'"{args}" is not represented.\n')
                return
            person = flat.represented
            flats = self.model.get_representative_flats(person.name)
            if len(flats) <= 1:
                self._remove_person(person.name)
            else:
                self.stdout.write(
                    f"{flat.represented.name} no longer represents {flat.name}.\n"
                )
                self.model.remove_flat_representative(flat.name)
            self.set_prompt()
            return
        try:
            self._remove_person(args)
            self.set_prompt()
        except KeyError:
            self.stdout.write(f'"{args}" is neither flat or person.\n')

    def complete_remove(
        self, text: str, line: str, beginx: int, endx: int
    ) -> List[str]:
        flats = [
            flat.name
            for flat in self.model.flats
            if flat.represented and flat.name.startswith(text)
        ]
        return flats + self.model.get_person_names(text)

    def do_presence(self, args: str) -> None:
        """Prints presence into file."""
        filename = args or "presence.html"
        rows = []
        sum_share = 0.0
        max_time = datetime.min
        max_pm = 0
        n_flats = 0
        representatives = set()
        for flat in self.model.flats:
            if flat.represented:
                repr_name = utils.convert_name(flat.represented.name)
                time = flat.represented.created_at.strftime("%H:%M")
                sum_share += float(flat.fraction)
                max_time = max(max_time, flat.represented.created_at)
                n_flats += 1
                representatives.add(flat.represented.name)
            else:
                repr_name = ""
                time = ""
            for i, owner in enumerate(flat.owners, start=1):
                share = float(flat.fraction * owner.fraction)
                name = utils.convert_name(owner.name)
                rows.append((name, flat.name, i, f"{share:.2%}", "", repr_name, time))
        rows.sort(key=lambda x: locale.strxfrm(x[0]))
        last_row = (
            "Celkem",
            n_flats,
            "",
            f"{sum_share:.2%}",
            max_pm,
            len(representatives),
            max_time.strftime("%H:%M"),
        )
        with open(filename, "w") as fout:
            fout.write(utils.CSS_STYLE)
            utils.write_table(
                fout, rows, "Presenční listina", PRESENCE_FIELDS, last_row=last_row
            )

    def do_quit(self, args: str) -> bool:
        """Quit the app."""
        return confirm("Really quit?")

    # Shortcuts
    do_q = do_quit
    do_f = do_flat
    complete_f = complete_flat
    do_EOF = do_quit


PRESENCE_FIELDS = [
    utils.Field("Vlastník", "owner"),
    utils.Field("Jednotka", "unit"),
    utils.Field("Část", "sub"),
    utils.Field("Podíl", "size"),
    utils.Field("PM", "ref"),
    utils.Field("Hlasuje", "owner"),
    utils.Field("Čas registrace", "time"),
]


def open_or_create_logfile(
    logfile: TextIO, model: Model, default_filename: str
) -> TextIO:
    if not logfile:
        try:
            logfile = open(default_filename, "r+")
        except IOError:
            logfile = CommandLogger.create_logfile(default_filename)
        else:
            CommandLogger.parse_logfile(logfile, model)
    else:
        CommandLogger.parse_logfile(logfile, model)
    return logfile


def main() -> None:
    locale.setlocale(locale.LC_ALL, "cs_CZ.UTF-8")
    parser = argparse.ArgumentParser(
        description="Records presence and votes on a gathering."
    )
    parser.add_argument(
        "flats",
        type=argparse.FileType("rb"),
        help="the json file with flats definition",
    )
    parser.add_argument(
        "--log",
        metavar="logfile",
        type=argparse.FileType("r+"),
        help="the csv file with actions definition",
    )
    args = parser.parse_args()
    setup_readline_if_available()
    json_flats = json.load(args.flats)
    model = Model(utils.from_json_to_flats(json_flats))
    default_filename = CommandLogger.default_logname(args.flats.name)
    logfile = open_or_create_logfile(args.log, model, default_filename)
    model.register_logger(CommandLogger(logfile))
    AppCmd(model).cmdloop()


if __name__ == "__main__":
    main()
