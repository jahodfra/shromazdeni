from typing import IO, List, NamedTuple, Tuple


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


def write_table(
    fout: IO[str], rows: List, header: str, fields: List[Field], last_row: Tuple = None
) -> None:
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
        """
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


def convert_name(name: str) -> str:
    if name and "," in name:
        name, extra = name.split(",", 1)
    if name.startswith("SJM"):
        name = name[4:] + " SJM"
    return name
