import fractions
from datetime import datetime
from dataclasses import dataclass
from typing import NamedTuple, List, Optional, Set


@dataclass
class Person:
    """Represents a person present on the gathering."""

    name: str
    created_at: datetime
    # Eventually it will contain a code


@dataclass
class Owner:
    name: str
    fraction: fractions.Fraction = fractions.Fraction(1)


@dataclass
class Flat:
    name: str
    fraction: fractions.Fraction
    owners: List[Owner]  # Owner can be SJM
    represented: Optional[Person] = None

    @property
    def sort_key(self):
        return tuple(int(n) for n in self.name.split("/"))

    @property
    def nice_name(self):
        return ("*" if self.represented else " ") + self.name

    @property
    def persons(self) -> Set[str]:
        return set(
            person for owner in self.owners for person in format_persons(owner.name)
        )


def _convert_flat(flat, shorten_name):
    if shorten_name:
        shortname = flat["name"].split("/", 1)[1]
    else:
        shortname = flat["name"]

    owners = []
    for json_owner in flat["owners"]:
        owners.append(
            Owner(
                name=json_owner["name"],
                fraction=fractions.Fraction(json_owner["fraction"]),
            )
        )
    return Flat(
        name=shortname, owners=owners, fraction=fractions.Fraction(flat["fraction"])
    )


def from_json_to_flats(json_flats):
    prefixes = set(flat["name"].split("/")[0] for flat in json_flats)
    shorten_name = len(prefixes) == 1
    flats = [_convert_flat(flat, shorten_name) for flat in json_flats]
    flats.sort(key=lambda flat: flat.sort_key)
    return flats


def format_persons(name: str) -> List[str]:
    if name.startswith("SJM"):
        name = name[3:].strip()
        names, address = name.split(",", 1)
        address = address.strip()
        name1, name2 = names.split(" a ")
        return [", ".join((name1, address)), ", ".join((name2, address))]
    else:
        return [name]


def convert_name(name):
    if name and "," in name:
        name, extra = name.split(",", 1)
    if name.startswith("SJM"):
        name = name[4:] + " SJM"
    return name


CSS_STYLE = """
<style>
td.unit {
    font-size: 120%;
}
.unit, .sub, .size {
    text-align: center;
}
.ref {
    min-width: 1.5cm;
}
.signature {
    min-width: 4cm;
}
.surname {
    font-size: 120%;
    font-weight: bold;
}
table {
    border: 1px solid black;
    border-collapse: collapse;
    width: 100%;
    font-size: 9pt;
    page-break-after: always;
}
th, td {
    border: 1px solid black;
    padding: 2px;
}
tr.last td {
    border-top: double;
}
</style>"""


class Field(NamedTuple):
    name: str
    style: str


def write_table(fout, rows, header, fields: List[Field], last_row=None):
    fout.write(
        f"""
<h2>{header}</h2>
<table>
<thead>
<tr>"""
    )
    for field in fields:
        fout.write(f'<th class="{field.style}">{field.name}</th>')
    fout.write(
        f"""
</tr>
</thead>
<tbody>"""
    )
    for row in rows:
        fout.write("<tr>")
        for field, value in zip(fields, row):
            if field.style == "owner" and " " in value:
                surname, rest = value.split(" ", 1)
                value = f'<span class="surname">{surname}</span> {rest}'
            fout.write(f'<td class="{field.style}">{value}</td>')
        fout.write("</tr>")
    if last_row:
        fout.write('<tr class="last">')
        for field, value in zip(fields, last_row):
            fout.write(f'<td class="{field.style}">{value}</td>')
        fout.write("</tr>")

    fout.write("""</tbody></table>""")
