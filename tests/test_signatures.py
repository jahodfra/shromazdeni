import pathlib

import pytest

from shromazdeni.tools import signatures


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


def test_signatures(tmp_path: pathlib.Path) -> None:
    fpath = tmp_path / "flats.json"
    fpath.write_text(CONTENT)
    signatures.main([fpath.as_posix()])


if __name__ == "__main__":
    pytest.main()
