import json
import pytest
from shromazdeni.tools import split


FLATS = [
    {
        "name": "1",
        "fraction": "1/2",
        "owners": [{"name": "A", "fraction": "1/3"}, {"name": "B", "fraction": "2/3"}],
    },
    {"name": "2", "fraction": "1/2", "owners": [{"name": "C", "fraction": "1/1"}]},
]


def test_split(tmp_path):
    with open(tmp_path / "flats.json", "w") as input_file:
        json.dump(FLATS, input_file)

    split.main(
        ["-f=1", str(tmp_path / "flats.json"), "-o", str(tmp_path / "output.json")]
    )

    with open(tmp_path / "output.json") as output_file:
        output = json.load(output_file)
        assert output == [
            {
                "name": "1-01",
                "fraction": "1/6",
                "owners": [{"name": "A", "fraction": "1"}],
            },
            {
                "name": "1-02",
                "fraction": "1/3",
                "owners": [{"name": "B", "fraction": "1"}],
            },
            {
                "name": "2",
                "fraction": "1/2",
                "owners": [{"name": "C", "fraction": "1"}],
            },
        ]


def test_invalid_flat(tmp_path):
    with open(tmp_path / "flats.json", "w") as input_file:
        json.dump(FLATS, input_file)

    with pytest.raises(SystemExit):
        split.main(
            [
                "-f=100",
                str(tmp_path / "flats.json"),
                "-o",
                str(tmp_path / "output.json"),
            ]
        )
