""" Spider for parsing katastr nemovitosti.

Output is owners of the units in the building.
"""
import argparse
import json
import urllib.parse
import urllib3
from typing import Dict, List

import scrapy
import scrapy.http as http
from scrapy.crawler import CrawlerProcess


def parse_owners(response: http.TextResponse) -> List[Dict]:
    rows = response.css("table.vlastnici tr")
    owners: List[Dict[str, str]] = []
    person_index = 0

    for row in rows[1:]:
        if row.css(".partnerSJM"):
            person = row.xpath(".//i/text()").get()
            if person_index == 0:
                owners[-1]["person1"] = person
            else:
                owners[-1]["person2"] = person
            person_index += 1
        else:
            person_index = 0
            name = row.xpath("td[1]/text()").get()
            if not name:
                # we are reading another header - different part of the table
                break
            fraction_el = row.css(".right").xpath("text()").get()
            owners.append({"name": name, "fraction": fraction_el or "1"})
    return owners


class KatastrSpider(scrapy.Spider):
    name: str = "katastr"  # type: ignore
    start_urls = ["https://nahlizenidokn.cuzk.cz/VyberBudovu.aspx?typ=Stavba"]
    download_delay = 1.0
    allowed_domains = ["nahlizenidokn.cuzk.cz"]

    def __init__(self, region: str, street: str, home_number: str):
        self.region = region
        self.street = street
        self.home_number = home_number

    def parse(self, response: http.TextResponse) -> http.FormRequest:
        yield scrapy.FormRequest.from_response(
            response,
            formdata={
                "ctl00$bodyPlaceHolder$vyberObec$txtObec": self.region,
                "ctl00$bodyPlaceHolder$vyberObec$btnObec": "Vyhledat",
            },
            callback=self.parse_address,
        )

    def parse_address(self, response: http.TextResponse) -> http.FormRequest:
        yield scrapy.FormRequest.from_response(
            response,
            formdata={
                "ctl00$bodyPlaceHolder$txtUlice": self.street,
                "ctl00$bodyPlaceHolder$txtCisloDomovni": self.home_number,
                "ctl00$bodyPlaceHolder$btnVyhledat": "Vyhledat",
                "ctl00$bodyPlaceHolder$listTypBudovy": "1",
                "ctl00$bodyPlaceHolder$txtBudova": "",
                "ctl00$bodyPlaceHolder$txtCisloOr": "",
                "ctl00$bodyPlaceHolder$idAccordionIndex": "1",
            },
            callback=self.parse_building,
        )

    def parse_building(self, response: http.TextResponse) -> http.FormRequest:
        for link in response.xpath("//table[@summary='Vymezené jednotky']//a"):
            yield scrapy.Request(
                response.urljoin(link.attrib["href"]), callback=self.parse_flat
            )

    def parse_flat(self, response: http.TextResponse) -> http.FormRequest:
        table = response.xpath("//table[@summary='Atributy jednotky']")
        yield {
            "name": table.xpath("tr[1]/td[2]/strong/text()").get(),
            "fraction": table.xpath("tr[last()]/td[2]/text()").get(),
            "owners": parse_owners(response),
        }


def download_building(
    file_name: str, street: str, home_number: str, region: str
) -> None:
    process = CrawlerProcess(settings={"FEED_URI": file_name, "FEED_FORMAT": "json"})
    pool = urllib3.PoolManager()
    response = pool.request(
        "GET",
        "https://nahlizenidokn.cuzk.cz/AutoCompleteObecHandler.ashx?{}".format(
            urllib.parse.urlencode({"term": region})
        ),
    )
    regions = json.loads(response.data)
    if len(regions) != 1:
        raise ValueError("Different number of regions then 1: {}".format(regions))
    full_region = regions[0]
    process.crawl(
        KatastrSpider, region=full_region, street=street, home_number=home_number
    )
    process.start()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download flat information from katasrt nemovitosti"
    )
    parser.add_argument("--region", required=True, help="Name of region e.g. Praha")
    parser.add_argument(
        "--street", required=True, help="Exact name of the street with diacritics"
    )
    parser.add_argument("--home_number", required=True, help="Home number")
    parser.add_argument("-o", "--output", help="Output filename", default="flats.json")

    args = parser.parse_args()
    download_building(
        args.output,
        region=args.region,
        street=args.street,
        home_number=args.home_number,
    )


if __name__ == "__main__":
    main()
