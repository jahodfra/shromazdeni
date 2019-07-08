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
    represented: Optional[Person] = None

    @property
    def sort_key(self):
        return tuple(int(n) for n in self.name.split("/"))

    @property
    def nice_name(self):
        return ("*" if self.represented else " ") + self.name

    @property
    def persons(self) -> Set[str]:
        return set(person for owner in self.owners for person in format_persons(owner))


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


class Building:
    """Abstraction layer above json file from the parser."""

    def __init__(self, flats: List[Flat]):
        self._flats = collections.OrderedDict((flat.name, flat) for flat in flats)

    @staticmethod
    def _convert_flat(flat, shorten_name):
        if shorten_name:
            shortname = flat["name"]
        else:
            shortname = flat["name"].split("/", 1)[1]

        return Flat(
            name=shortname,
            owners=[owner["name"] for owner in flat["owners"]],
            fraction=fractions.Fraction(flat["fraction"]),
        )

    @classmethod
    def load(cls, json_flats):
        prefixes = set(flat["name"].split("/")[0] for flat in json_flats)
        shorten_name = len(prefixes) > 1
        flats = [cls._convert_flat(flat, shorten_name) for flat in json_flats]
        flats.sort(key=lambda flat: flat.sort_key)
        return cls(flats)

    @property
    def flats(self):
        return list(self._flats.values())

    def get_flat(self, shortname):
        return self._flats[shortname]

    @property
    def percent_represented(self):
        return sum(flat.fraction for flat in self.flats if flat.represented) * 100

    def represent_flat(self, shortname, person: Person):
        self._flats[shortname].represented = person


class AppCmd(cmd.Cmd):
    def __init__(self, building, completekey="tab", stdin=None, stdout=None):
        self.building = building
        self.present_persons = {}
        self.set_prompt()
        super().__init__(completekey=completekey, stdin=stdin, stdout=stdout)

    def set_prompt(self):
        percent = self.building.percent_represented
        can_start = "Y" if percent > 50 else "N"
        self.prompt = f"{can_start}{float(percent):.1f}> "

    def do_flat(self, args):
        """List all flats in the building."""
        if args and not args.isspace():
            try:
                flat = self.building.get_flat(args)
            except KeyError:
                self.stdout.write(f'Unit "{args}" not found.\n')
                return
            self.stdout.write("Owners:\n")
            for i, owner in enumerate(flat.owners, start=1):
                self.stdout.write(f"{i:2d}. {owner}\n")
            if flat.represented:
                self.stdout.write(f"Represented by {flat.represented.name}\n")
        else:
            self.columnize([flat.nice_name for flat in self.building.flats])

    def complete_flat(self, text, line, beginx, endx):
        names = [flat.name for flat in self.building.flats]
        return [n for n in names if n.startswith(text)]

    def do_add(self, args):
        """Adds the representation for flats."""
        # The command seems bit nonintuitive.
        # We first enter name of flat so we don't have to
        # enter the name of owner in the most common case.
        if not args or args.isspace():
            self.stdout.write('No flats passed.\nuse "add [flat1] [flat2]"\n')
            return

        persons = set()
        flats = [arg.strip() for arg in args.split(" ")]
        new_flats = []
        try:
            for fname in flats:
                flat = self.building.get_flat(fname)
                persons.update(flat.persons)
                if flat.represented:
                    self.stdout.write(
                        f"Ignoring {fname}. It is already "
                        f"represented by {flat.represented.name}.\n"
                    )
                else:
                    new_flats.append(fname)
                    self.stdout.write(f"{fname} owners:\n")
                    for i, owner in enumerate(flat.owners, start=1):
                        self.stdout.write(f"{i:2d}. {owner}\n")
        except KeyError:
            self.stdout.write(f'Unit "{fname}" not found.\n')
            return
        flats = new_flats
        persons = ["New Person"] + sorted(persons)
        owner_index = choice_from("Select representation", persons, self.stdout)
        if owner_index == -1:
            return
        if owner_index == 0:
            # TODO: autocomplete on name
            # this is needed only when somebody gives a will to foreign person
            # during the meeting.
            # Can be solved by specifying extra persons as options.
            name = input("Name: ")
            if not confirm("Create new person?"):
                return
        else:
            name = persons[owner_index]
        if name not in self.present_persons:
            self.present_persons[name] = Person(name)
        for fname in flats:
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
        # TODO: remove person from the gathering
        # TODO: remove person representing the flat from the gathering
        pass

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


def main():
    if len(sys.argv) != 2:
        print("Error: Missing mandatory argument.")
        print("Usage: shromazdeni.py <flats.json>")
        sys.exit(1)

    setup_readline_if_available()
    with open(sys.argv[1], "r") as fin:
        json_flats = json.load(fin)
    building = Building.load(json_flats)
    AppCmd(building).cmdloop()


if __name__ == "__main__":
    main()
