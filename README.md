# Aplikace pro hlasování v SVJ.

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
