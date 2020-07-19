import argparse
import json
import locale
import sys
from typing import IO

from shromazdeni import business

# TODO: move to reports
from shromazdeni.reports import utils as rutils
from shromazdeni import utils


FIELDS = [
    rutils.Field("Vlastník", "owner"),
    rutils.Field("Jednotka", "unit"),
    rutils.Field("Část", "sub"),
    rutils.Field("Podíl", "size"),
    rutils.Field("PM", "ref"),
    rutils.Field("Podpis", "signature"),
]


def write_flat_table(fout: IO[str], flat: business.Flat) -> None:
    rows = []
    for i, owner in enumerate(flat.owners, start=1):
        share = float(owner.fraction)
        name = rutils.convert_name(owner.name)
        rows.append((name, flat.name, i, f"{share:.2%}", "", ""))
    rutils.write_table(fout, rows, f"Plná moc pro jednotku {flat.name}", FIELDS)


def main() -> None:
    locale.setlocale(locale.LC_ALL, "cs_CZ.UTF-8")
    parser = argparse.ArgumentParser(description="Prepare list for signatures.")
    parser.add_argument(
        "flats",
        type=argparse.FileType("rb"),
        help="the json file with flats definition",
    )
    parser.add_argument(
        "--separate",
        metavar="flat",
        nargs="*",
        type=str,
        help="units with separate table",
        default=[],
    )

    args = parser.parse_args()
    json_flats = json.load(args.flats)
    flats = utils.from_json_to_flats(json_flats)

    rows = []
    for flat in flats:
        if flat.name in args.separate:
            share = float(flat.fraction)
            rows.append(("", flat.name, 1, f"{share:.2%}", "", ""))
            continue
        for i, owner in enumerate(flat.owners, start=1):
            share = float(flat.fraction * owner.fraction)
            name = rutils.convert_name(owner.name)
            rows.append((name, flat.name, i, f"{share:.2%}", "", ""))
    rows.sort(key=lambda x: locale.strxfrm(x[0]))

    sys.stdout.write(rutils.CSS_STYLE)
    for excluded in args.separate:
        filtered = [flat for flat in flats if flat.name == excluded]
        if not filtered:
            print(f'Cannot find flat "{excluded}"')
            continue
        flat = filtered[0]
        write_flat_table(sys.stdout, flat)

    rutils.write_table(sys.stdout, rows, "Prezenční listina", FIELDS)


if __name__ == "__main__":
    main()
