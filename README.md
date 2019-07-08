# Aplikace pro hlasování v SVJ.

[![Coverage Status](https://coveralls.io/repos/github/jahodfra/shromazdeni/badge.svg?branch=master)](https://coveralls.io/github/jahodfra/shromazdeni?branch=master)

Tato aplikace není hotová. Aktuálně nescháním pomoc.

## Instalace
```bash
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

## Použití
```bash
env/bin/scrapy runspider katastr_spider.py -o flats.json -a region="Praha (okres Hlavní město Praha);554782" -a town_part=400807 -a building=365
```

