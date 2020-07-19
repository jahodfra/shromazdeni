# Aplikace pro hlasování v SVJ.

[![Build Status](https://api.travis-ci.org/jahodfra/shromazdeni.svg?branch=master)](https://travis-ci.org/jahodfra/shromazdeni)
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
python shromazdeni/tools/crawler.py --region=Praha --street=Národní --home_number=55 --output=narodni55.json
python shromazdeni narodni55.json
```
