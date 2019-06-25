#!env/bin/python

import cmd
import collections
import fractions
import json
import sys
from dataclasses import dataclass
from typing import List, Optional, Set


@dataclass
class Person:
    """Represents a person present on the gathering."""

    name: str
    # Eventually it will contain a code


@dataclass
class Flat:
    name: str
    fraction: fractions.Fraction
    owners: List[str]  # Owner can be SJM
    persons: Set[str]
    represented: Optional[Person] = None

    @property
    def sort_key(self):
        return tuple(int(n) for n in self.name.split("/"))

    @property
    def nice_name(self):
        return ("*" if self.represented else " ") + self.name


# TODO: preserve presence when the program crashes
# TODO: log the program output to an extra file


def setup_readline_if_available():
    # Slash is used as part of flat names.
    # We don't want to split the names so we can have simple auto completers.
    try:
        import readline

        delims = readline.get_completer_delims().replace("/", "")
        readline.set_completer_delims(delims)
    except ImportError:
        pass


def format_persons(name):
    if name.startswith("SJM"):
        name = name[3:].strip()
        names, address = name.split(",", 1)
        address = address.strip()
        name1, name2 = names.split(" a ")
        return [", ".join((name1, address)), ", ".join((name2, address))]
    else:
        return [name]


def choice_from(title, choices):
    while True:
        print(title)
        for i, choice in enumerate(choices):
            print(f"{i:2d}) {choice}")
        line = input("Choice [empty to cancel]> ")

        if not line or line.isspace():
            return -1
        try:
            index = int(line)
            if 0 <= index < len(choices):
                return index
        except ValueError:
            pass
        print("invalid choice")


def prompt(question):
    return input(f"\n{question} [yN]> ").lower() == "y"


class Building:
    """Abstraction layer above json file from the parser."""

    def __init__(self, flats):
        prefixes = set(flat["name"].split("/")[0] for flat in flats)
        shorten_name = len(prefixes) > 1
        self._flats = collections.OrderedDict()
        converted = [self._convert_flat(flat, shorten_name) for flat in flats]
        converted.sort(key=lambda flat: flat.sort_key)
        self._flats = collections.OrderedDict((flat.name, flat) for flat in converted)

    @staticmethod
    def _convert_flat(flat, shorten_name):
        if shorten_name:
            shortname = flat["name"]
        else:
            shortname = flat["name"].split("/", 1)[1]

        persons = set(
            person
            for owner in flat["owners"]
            for person in format_persons(owner["name"])
        )
        return Flat(
            name=shortname,
            owners=[owner["name"] for owner in flat["owners"]],
            persons=persons,
            fraction=fractions.Fraction(flat["fraction"]),
        )

    @classmethod
    def load(cls, filepath):
        with open(filepath, "r") as fin:
            flats = json.load(fin)
        return cls(flats)

    @property
    def flat_names(self):
        return [flat.nice_name for flat in self._flats.values()]

    def get_flat(self, shortname):
        return self._flats[shortname]

    @property
    def percent_represented(self):
        return (
            sum(flat.fraction for flat in self._flats.values() if flat.represented)
            * 100
        )

    def represent_flat(self, shortname, person: Person):
        self._flats[shortname].represented = person


class AppCmd(cmd.Cmd):
    def __init__(self, building):
        self.building = building
        self.present_persons = {}
        self.set_prompt()
        super().__init__()

    def set_prompt(self):
        percent = self.building.percent_represented
        can_start = "Y" if percent > 50 else "N"
        self.prompt = f"{can_start}{float(percent):.1f}> "

    def do_flat(self, args):
        """List all flats in the building."""
        # TODO: add notification which flats are represented
        if args and not args.isspace():
            try:
                flat = self.building.get_flat(args)
            except KeyError:
                print(f'Unit "{args}" not found.')
                return
            print("Owners:")
            for i, owner in enumerate(flat.owners, start=1):
                print(f"{i:2d}. {owner}")
            if flat.represented:
                print(f"Represented by {flat.represented.name}")
        else:
            self.columnize(self.building.flat_names)

    def complete_flat(self, text, line, beginx, endx):
        return [n for n in self.building.flat_names if n.startswith(text)]

    def do_add(self, args):
        """Adds the representation for flats."""
        # The command seems bit non intuitive.
        # We first enter name of flat so we don't have to
        # enter the name of owner in the most common case.
        if not args or args.isspace():
            print("No flats passed.")
            print('use "add [flat1] [flat2]"')
            return

        persons = set()
        flats = [arg.strip() for arg in args.split(" ")]
        try:
            for fname in flats:
                flat = self.building.get_flat(fname)
                persons.update(flat.persons)
                print(f"{fname} owners:")
                for i, owner in enumerate(flat.owners, start=1):
                    print(f"{i:2d}. {owner}")
        except KeyError:
            print(f'Unit "{flat}" not found.')
            return
        persons = ["Somebody else"] + sorted(persons)
        owner_index = choice_from("Select owner", persons)
        if owner_index == -1:
            return
        if owner_index == 0:
            # TODO: autocomplete on name
            # this is needed only when somebody gives a will to foreign person
            # during the meeting.
            # Can be solved by specifying extra persons as options.
            name = input("Name: ")
            if not prompt("Create new person?"):
                return
        else:
            name = persons[owner_index]
        if name not in self.present_persons:
            self.present_persons[name] = Person(name)
        for fname in flats:
            represented = self.building.get_flat(fname).represented
            if represented:
                print(
                    f"Ignoring {fname}. It is already represented by {represented.name}."
                )
            else:
                self.building.represent_flat(fname, self.present_persons[name])
        self.set_prompt()

    complete_add = complete_flat

    def do_remove(self, args):
        """
    > remove
    Novák Jan, Příčná ulice 34, Praha left the gathering.
    > remove 218
    Novák Petr, Příčná ulice 34, Praha no longer represents 218.
    """
        pass

    def do_presence(self, args):
        """Print presence."""
        if args and not args.isspace():
            try:
                flat = self.building.get_flat(args)
            except KeyError:
                print(f'Unit "{args}" not found.')
                return
            
          
        # Without parameter, writes who is present
        # With the name it writes the flats
        # TODO: finish
        pass

    def do_quit(self, args):
        """Quit the app."""
        return prompt("Really quit?")

    # Shortcuts
    do_q = do_quit
    do_f = do_flat
    complete_f = complete_flat
    do_EOF = do_quit


def main():
    if len(sys.argv) != 2:
        print("Error: Missing mandatory argument.")
        print("Usage: shromazdeni.py <flats.json>")
        sys.exit(1)

    setup_readline_if_available()
    building = Building.load(sys.argv[1])
    AppCmd(building).cmdloop()


if __name__ == "__main__":
    main()
