import pathlib
import sys

import pytest

from shromazdeni import presence_list


CONTENT = """
[
{"name": "777/126", "fraction": "472/90393", "owners": [
    {"name": "Petr Jakub", "fraction": "1/2"}]},
{"name": "777/125", "fraction": "644/90393", "owners": [
    {"name": "Firma s.r.o.", "fraction": "1"}]},
{"name": "777/100", "fraction": "425/90393", "owners": [
    {"name": "Elma Akra", "fraction": "1"}]}
]
"""


def test_presence_list(tmp_path: pathlib.Path) -> None:
    fpath = tmp_path / "flats.json"
    fpath.write_text(CONTENT)
    sys.argv = ["presence_list.py", fpath.as_posix(), "--separate", "1"]
    presence_list.main()


if __name__ == "__main__":
    pytest.main()
