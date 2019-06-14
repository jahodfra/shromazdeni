#!/usr/bin/python3.6

import cmd
import json
import sys

import readline


class Building:
  """Abstraction layer above json file from the parser."""
  def __init__(self, units):
    prefixes = set(unit['name'].split('/')[0] for unit in units)
    if len(prefixes) > 1:
      for unit in units:
        unit['shortname'] = unit['name']
    else:
      for unit in units:
        unit['shortname'] = unit['name'].split('/', 1)[1]

    self._units = units
    self._units_map = {unit['shortname']: unit for unit in units}
  
  @classmethod
  def load(cls, filepath):
    with open(filepath, "r") as fin:
      units = json.load(fin)
    return cls(units)

  @property
  def unit_names(self):
    return sorted(u['shortname'] for u in self._units)

  def get_unit(self, shortname):
    return self._units_map[shortname]


class Presence:
  """Preservers and represent presence.""" 
  pass


class AppCmd(cmd.Cmd):
  def __init__(self, building):
    self.building = building
    super().__init__()

  def do_unit(self, args):
    """List all units in the building."""
    if args:
      try:
        unit = self.building.get_unit(args)
      except KeyError:
        print(f"Unit \"{args}\" not found.")
        return
      print("Owners:")
      for i, owner in enumerate(unit['owners'], start=1):
        print(f"{i:2d}. {owner['name']}")
    else:
      self.columnize(self.building.unit_names)

  def complete_unit(self, text, line, beginx, endx):
    return [n for n in self.building.unit_names if n.startswith(text)]
    

  def do_quit(self, args):
    """Quit the app."""
    return input("\nReally quit? [yN]> ").lower() == "y"

  # Shortcuts
  do_q = do_quit
  do_u = do_unit
  complete_u = complete_unit
  do_EOF = do_quit


def main():
  if len(sys.argv) != 2:
    print("Error: Missing mandatory argument.")
    print("Usage: shromazdeni.py <flats.json>")
    sys.exit(1)
  
  # Slash is used as part of unit names.
  # We don't want to split the names so we can have simple auto completers.
  delims = readline.get_completer_delims().replace("/", "")
  readline.set_completer_delims(delims)

  building = Building.load(sys.argv[1])
  AppCmd(building).cmdloop()


if __name__ == "__main__":
  main()
