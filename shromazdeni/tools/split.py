import argparse
import fractions
import json
import sys
from typing import List, Collection, Set

from shromazdeni import business
from shromazdeni import utils


def split_flats(
    flats: List[business.Flat], to_be_split: Collection[str]
) -> List[business.Flat]:
    to_be_split = set(to_be_split)
    new_flats = []
    for flat in flats:
        if flat.name in to_be_split or flat.original_name in to_be_split:
            for order, owner in enumerate(flat.owners, start=1):
                persons = set(person for person in utils.format_persons(owner.name))
                new_flats.append(
                    business.Flat(
                        name=f"{flat.name}-{order:02d}",
                        original_name=f"{flat.original_name}-{order:02d}",
                        owners=[business.Owner(owner.name, fractions.Fraction(1))],
                        fraction=flat.fraction * owner.fraction,
                        persons=persons,
                    )
                )
        else:
            new_flats.append(flat)
    return new_flats


def validate_flat_names(
    parser: argparse.ArgumentParser,
    flats: List[business.Flat],
    to_be_split: Collection[str],
) -> None:
    to_be_split = set(to_be_split)
    names: Set[str] = set()
    names.update(flat.name for flat in flats)
    names.update(flat.original_name for flat in flats)
    unknown_names = to_be_split - names
    if unknown_names:
        parser.exit(1, f"These flat names are not in the dataset: {unknown_names}\n")


def main(argv: List[str]) -> None:
    parser = argparse.ArgumentParser(
        description="Records presence and votes on a gathering."
    )
    parser.add_argument(
        "input_flats",
        type=argparse.FileType("r"),
        help="the json file with flats definition",
    )
    parser.add_argument(
        "-f", "--flat", type=str, nargs="+", help="the flat to be split"
    )
    parser.add_argument(
        "-o",
        "--output",
        default=sys.stdout,
        type=argparse.FileType("w"),
        help="the output file with flats definition",
    )
    args = parser.parse_args(argv)
    flats = utils.from_json_to_flats(json.load(args.input_flats))
    validate_flat_names(parser, flats, args.flat)

    transformed_flats = split_flats(flats, args.flat)
    json_output = utils.from_flats_to_json(transformed_flats)
    json.dump(json_output, args.output)


if __name__ == "__main__":
    main(sys.argv[1:])
