""" Spider for parsing katastr nemovitosti.

Output is onwers of the units in the building.
"""

import scrapy


def parse_owners(response):
    rows = response.css("table.vlastnici tr")
    owners = []
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
    name = "katastr"
    start_urls = ["https://nahlizenidokn.cuzk.cz/VyberBudovu.aspx?typ=Stavba"]
    download_delay = 1.0
    allowed_domains = ["nahlizenidokn.cuzk.cz"]
    custom_settings = {}

    def __init__(
        self,
        region="Praha (okres Hlavní město Praha);554782",
        town_part="400807",
        building="365",
    ):
        self.region = region
        self.town_part = town_part
        self.building = building

    def parse(self, response):
        yield scrapy.FormRequest.from_response(
            response,
            formdata={
                "ctl00$bodyPlaceHolder$vyberObec$txtObec": self.region,
                "ctl00$bodyPlaceHolder$vyberObec$btnObec": "Vyhledat",
            },
            callback=self.parse_address,
        )

    def parse_address(self, response):
        yield scrapy.FormRequest.from_response(
            response,
            formdata={
                "ctl00$bodyPlaceHolder$listCastObce": self.town_part,
                "ctl00$bodyPlaceHolder$txtBudova": self.building,
                "ctl00$bodyPlaceHolder$listTypBudovy": "1",
                "ctl00$bodyPlaceHolder$btnVyhledat": "Vyhledat",
            },
            callback=self.parse_building,
        )

    def parse_building(self, response):
        for link in response.xpath("//table[@summary='Vymezené jednotky']//a"):
            yield scrapy.Request(
                response.urljoin(link.attrib["href"]), callback=self.parse_flat
            )

    def parse_flat(self, response):
        table = response.xpath("//table[@summary='Atributy jednotky']")
        yield {
            "name": table.xpath("tr[1]/td[2]/strong/text()").get(),
            "fraction": table.xpath("tr[last()]/td[2]/text()").get(),
            "owners": parse_owners(response),
        }
