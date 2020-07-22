import argparse
import json
import locale
import sys
from typing import List

from shromazdeni import business
from shromazdeni import utils
from shromazdeni import reports


def main(argv: List[str]) -> None:
    locale.setlocale(locale.LC_ALL, "cs_CZ.UTF-8")
    parser = argparse.ArgumentParser(description="Prepare list for signatures.")
    parser.add_argument(
        "flats",
        type=argparse.FileType("rb"),
        help="the json file with flats definition",
    )

    args = parser.parse_args(argv)
    flats = utils.from_json_to_flats(json.load(args.flats))
    building = business.Building(flats=flats)
    reports.write_signatures(building, "signatures.html")


if __name__ == "__main__":
    main(sys.argv[1:])
