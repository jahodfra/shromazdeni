from datetime import datetime
import locale

from shromazdeni import business
from shromazdeni.reports import utils


PRESENCE_FIELDS = [
    utils.Field("Vlastník", "owner"),
    utils.Field("Jednotka", "unit"),
    utils.Field("Část", "sub"),
    utils.Field("Podíl", "size"),
    utils.Field("PM", "ref"),
    utils.Field("Hlasuje", "owner"),
    utils.Field("Čas registrace", "time"),
]


def write_presence(building: business.Building, filename: str) -> None:
    """Prints presence into file."""
    rows = []
    sum_share = 0.0
    max_time = datetime.min
    max_pm = 0
    n_flats = 0
    representatives = set()
    for flat in building.flats:
        if flat.represented:
            repr_name = utils.convert_name(flat.represented.name)
            time = flat.represented.created_at.strftime("%H:%M")
            sum_share += float(flat.fraction)
            max_time = max(max_time, flat.represented.created_at)
            n_flats += 1
            representatives.add(flat.represented.name)
        else:
            repr_name = ""
            time = ""
        for i, owner in enumerate(flat.owners, start=1):
            share = float(flat.fraction * owner.fraction)
            name = utils.convert_name(owner.name)
            rows.append((name, flat.name, i, f"{share:.2%}", "", repr_name, time))
    rows.sort(key=lambda x: locale.strxfrm(x[0]))
    last_row = (
        "Celkem",
        n_flats,
        "",
        f"{sum_share:.2%}",
        max_pm,
        len(representatives),
        max_time.strftime("%H:%M"),
    )
    with open(filename, "w") as fout:
        fout.write(utils.CSS_STYLE)
        utils.write_table(
            fout, rows, "Presenční listina", PRESENCE_FIELDS, last_row=last_row
        )
