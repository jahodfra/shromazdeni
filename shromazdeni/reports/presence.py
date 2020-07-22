from datetime import datetime
import enum
import locale

from shromazdeni import business
from shromazdeni.reports import utils


PRESENCE_FIELDS = [
    utils.Field("Vlastník", "owner"),
    utils.Field("Jednotka", "unit"),
    utils.Field("Podíl", "size"),
]

SIGNATURE_FIELDS = [utils.Field("PM", "ref"), utils.Field("Podpis", "ref")]

FINAL_FIELDS = [utils.Field("Hlasuje", "owner"), utils.Field("Čas registrace", "time")]


class ReportType(enum.Enum):
    SIGNATURE = enum.auto()
    FINAL = enum.auto()


def write_presence(building: business.Building, filename: str) -> None:
    _write_presence(building, filename, ReportType.FINAL)


def write_signatures(building: business.Building, filename: str) -> None:
    _write_presence(building, filename, ReportType.SIGNATURE)


def _write_presence(
    building: business.Building, filename: str, kind: ReportType
) -> None:
    """Prints presence into file."""
    rows = []
    sum_share = 0.0
    max_time = datetime.min
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

        names = " a ".join(utils.convert_name(owner.name) for owner in flat.owners)
        share = float(flat.fraction)
        if kind == ReportType.FINAL:
            rows.append((names, flat.name, f"{share:.2%}", repr_name, time))
        else:
            rows.append((names, flat.name, f"{share:.2%}", "", ""))

    rows.sort(key=lambda x: locale.strxfrm(x[0]))
    if kind == ReportType.FINAL:
        last_row = (
            "Celkem",
            n_flats,
            f"{sum_share:.2%}",
            str(len(representatives)),
            max_time.strftime("%H:%M"),
        )
        fields = PRESENCE_FIELDS + FINAL_FIELDS
    else:
        last_row = ("Celkem", len(building.flats), "100%", "", "")
        fields = PRESENCE_FIELDS + SIGNATURE_FIELDS
    with open(filename, "w") as fout:
        fout.write(utils.CSS_STYLE)
        utils.write_table(fout, rows, "Presenční listina", fields, last_row=last_row)
