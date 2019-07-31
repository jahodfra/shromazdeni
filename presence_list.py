import argparse
import json
import locale
import sys

import utils


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
</style>"""
FIELD_NAMES = ["owner", "unit", "sub", "size", "ref", "signature"]


def write_table(fout, rows, header):
    fout.write(
        f"""
<h2>{header}</h2>
<table>
<thead>
<tr>
<th class="owner">Vlastník</th>
<th class="unit">Jednotka</th>
<th class="sub">Část</th>
<th class="size">Podíl</th>
<th class="ref">PM</th>
<th class="signature">Podpis</th>
</tr>
</thead>
<tbody>"""
    )
    for row in rows:
        fout.write("<tr>")
        for field, value in zip(FIELD_NAMES, row):
            if field == "owner" and " " in value:
                surname, rest = value.split(" ", 1)
                value = f'<span class="surname">{surname}</span> {rest}'
            fout.write(f'<td class="{field}">{value}</td>')
        fout.write("</tr>")
    fout.write("""</tbody></table>""")


def write_flat_table(fout, flat):
    rows = []
    for i, owner in enumerate(flat.owners, start=1):
        share = float(owner.fraction)
        name = convert_name(owner.name)
        rows.append((name, flat.name, i, f"{share:.2%}", "", ""))
    write_table(fout, rows, f"Plná moc pro jednotku {flat.name}")


def main():
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
            name = convert_name(owner.name)
            rows.append((name, flat.name, i, f"{share:.2%}", "", ""))
    rows.sort(key=lambda x: locale.strxfrm(x[0]))

    sys.stdout.write(CSS_STYLE)
    for excluded in args.separate:
        filtered = [flat for flat in flats if flat.name == excluded]
        if not filtered:
            print(f'Cannot find flat "{excluded}"')
            continue
        flat = filtered[0]
        write_flat_table(sys.stdout, flat)

    write_table(sys.stdout, rows, "Prezenční listina")


if __name__ == "__main__":
    main()
