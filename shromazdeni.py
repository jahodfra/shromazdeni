import argparse
import cmd
import collections
import csv
import datetime
import json
import os
from typing import Dict, List, TextIO

import utils


def setup_readline_if_available():
    # Slash is used as part of flat names.
    # We don't want to split the names so we can have simple auto completers.
    try:
        import readline

        delims = readline.get_completer_delims().replace("/", "")
        readline.set_completer_delims(delims)
    except ImportError:
        pass


def choice_from(title, choices, stdout):
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


def confirm(question):
    return input(f"\n{question} [yN]> ").lower() == "y"


def log_command(func):
    def wrapper(self, *args):
        result = func(self, *args)
        # On success
        if self._logger:
            self._logger.log(func.__name__, args)
        return result

    return wrapper


class CommandLogger:
    def __init__(self, logfile):
        self._logfile = logfile
        self._writer = csv.writer(logfile)

    @staticmethod
    def default_logname(flats_filename: str) -> str:
        now = datetime.datetime.now().strftime("%Y%m%d")
        filename, _ext = os.path.splitext(flats_filename)
        filename += f".{now}.log"
        return filename

    @staticmethod
    def parse_logfile(logfile, model):
        reader = csv.reader(logfile)
        next(reader)
        for row in reader:
            func = row[1]
            getattr(model, func)(*row[2:])

    @staticmethod
    def create_logfile(filename: str):
        fout = open(filename, "w")
        writer = csv.writer(fout)
        writer.writerow(["date", "operation", "*args"])
        return fout

    def log(self, func_name, args):
        assert all(isinstance(arg, str) for arg in args)
        now = datetime.datetime.now().strftime("%H:%M")
        row = [now, func_name]
        row += args
        self._writer.writerow(row)
        self._logfile.flush()


class Model:
    """Abstraction layer above json file from the parser."""

    def __init__(self, flats: List[utils.Flat]):
        self._flats = collections.OrderedDict((flat.name, flat) for flat in flats)
        self._present_persons: Dict[str, utils.Person] = {}
        self._logger = None

    def register_logger(self, logger):
        self._logger = logger

    @property
    def flats(self):
        return list(self._flats.values())

    def get_flat(self, shortname):
        return self._flats[shortname]

    @property
    def percent_represented(self):
        return sum(flat.fraction for flat in self.flats if flat.represented) * 100

    @log_command
    def represent_flat(self, flat_name, person_name):
        person = self._present_persons[person_name]
        self._flats[flat_name].represented = person

    def person_exists(self, name):
        return name in self._present_persons

    @log_command
    def add_person(self, name):
        assert not self.person_exists(name)
        self._present_persons[name] = utils.Person(name)

    @log_command
    def remove_flat_representative(self, flat_name):
        flat = self._flats[flat_name]
        person = flat.represented
        if person:
            self._remove_flat_representative(flat_name)

    def _remove_flat_representative(self, flat_name):
        self._flats[flat_name].represented = None

    @log_command
    def remove_person(self, name):
        person_flats = self.get_representative_flats(name)
        for flat_name in person_flats:
            self._remove_flat_representative(flat_name)
        del self._present_persons[name]
        return person_flats

    def get_representative_flats(self, person_name):
        return [
            flat.name
            for flat in self.flats
            if flat.represented and flat.represented.name == person_name
        ]

    def get_person_names(self, prefix):
        return [n for n in self._present_persons if n.startswith(prefix)]


class AppCmd(cmd.Cmd):
    def __init__(self, model, completekey="tab", stdin=None, stdout=None):
        self.model = model
        self.set_prompt()
        super().__init__(completekey=completekey, stdin=stdin, stdout=stdout)

    def set_prompt(self):
        percent = self.model.percent_represented
        can_start = "Y" if percent > 50 else "N"
        self.prompt = f"{can_start}{float(percent):.1f}> "

    def do_flat(self, args):
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

    def complete_flat(self, text, line, beginx, endx):
        return [flat.name for flat in self.model.flats if flat.name.startswith(text)]

    def do_add(self, args):
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
                    persons.add(flat.represented.name)
                    self.stdout.write(
                        f"Ignoring {fname}. It is already "
                        f"represented by {flat.represented.name}.\n"
                    )
                else:
                    persons.update(flat.persons)
                    new_flats.append(fname)
                    self.stdout.write(f"{fname} owners:\n")
                    for i, owner in enumerate(flat.owners, start=1):
                        self.stdout.write(f"{i:2d}. {owner.name}\n")
        except KeyError:
            self.stdout.write(f'Unit "{fname}" not found.\n')
            return
        flats = new_flats
        if not flats:
            return
        persons = ["New Person"] + sorted(persons)
        owner_index = choice_from("Select representation", persons, self.stdout)
        if owner_index == -1:
            return
        if owner_index == 0:
            name = input("Name: ")
            if not confirm("Create new person?"):
                return
        else:
            name = persons[owner_index]
        if not self.model.person_exists(name):
            # Prevent creating already existing person.
            self.model.add_person(name)
        for fname in flats:
            self.model.represent_flat(fname, name)
        self.set_prompt()

    complete_add = complete_flat

    def _remove_person(self, person_name):
        for flat in self.model.remove_person(person_name):
            self.stdout.write(f"{person_name} no longer represents {flat}.\n")
        self.stdout.write(f"{person_name} left.\n")

    def do_remove(self, args):
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
            person = flat.represented
            if not person:
                self.stdout.write(f'"{args}" is not represented.\n')
                return
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

    def complete_remove(self, text, line, beginx, endx):
        flats = [
            flat.name
            for flat in self.model.flats
            if flat.represented and flat.name.startswith(text)
        ]
        return flats + self.model.get_person_names(text)

    def do_presence(self, args):
        """Print presence."""
        if args and not args.isspace():
            pass

        # Without parameter, writes who is present
        # With the name it writes the flats the person represents
        # TODO: finish
        pass

    def do_quit(self, args):
        """Quit the app."""
        return confirm("Really quit?")

    # Shortcuts
    do_q = do_quit
    do_f = do_flat
    complete_f = complete_flat
    do_EOF = do_quit


def open_or_create_logfile(logfile: TextIO, model: Model, default_filename: str):
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


def main():
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
