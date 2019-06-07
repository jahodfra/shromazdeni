"""
Installation

brew install geckodriver
python3 -m venv env
source env/bin/activate
pip install selenium
"""

import json
import pprint

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


REGION = 'Praha'
TOWN_PART = 'Letňany'
BUILDING_NO = '365'


def load_flat_links(driver):
    driver.get('https://nahlizenidokn.cuzk.cz/VyberBudovu.aspx?typ=Stavba')

    obec = driver.find_element_by_id('ctl00_bodyPlaceHolder_vyberObec_txtObec')
    obec.send_keys(REGION)
    obec.send_keys(Keys.RETURN)

    town_part_xpath = f"//*[text()='{TOWN_PART}']"
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, town_part_xpath)))
    driver.find_element_by_xpath(town_part_xpath).click()
    driver.find_element_by_id('ctl00_bodyPlaceHolder_txtBudova').send_keys(BUILDING_NO)
    driver.find_element_by_id('ctl00_bodyPlaceHolder_btnVyhledat').click()
    links = driver.find_element_by_xpath('//table[@summary=\'Vymezené jednotky\']').find_elements_by_tag_name('a')
    return [(link.text, link.get_attribute('href')) for link in links]


def format_persons(name):
    if name.startswith('SJM'):
        name = name[3:].strip()
        names, address = name.split(',', 1)
        address = address.strip()
        name1, name2 = names.split(' a ')
        return ', '.join((name1, address)), ', '.join((name2, address))
    else:
        return name, ''


def parse_owners(driver):
    rows = driver.find_element_by_css_selector('table.vlastnici').find_elements_by_tag_name('tr')
    owners = []
    person_index = 0

    for row in rows[1:]:
        if row.find_elements_by_class_name('partnerSJM'):
            person = row.find_element_by_tag_name('i').text
            if person_index == 0:
                owners[-1]['person1'] = person
            else:
                owners[-1]['person2'] = person
            person_index += 1
        else:
            try:
                name = row.find_element_by_tag_name('td').text
            except NoSuchElementException:
                # we are reading another header - different part of the table
                break
            person_index = 0
            fraction_el = row.find_element_by_class_name('right')
            person1, person2 = format_persons(name)
            owners.append({
                'name': name,
                'fraction': fraction_el.text or '1',
                'person1': person1,
                'person2': person2,
            })
    return owners


def load_flat_details(driver, link):
    driver.get(link)
    cells = driver.find_element_by_xpath('//table[@summary=\'Atributy jednotky\']').find_elements_by_tag_name('td')
    name = cells[1].text
    fraction = cells[-1].text

    owners = parse_owners(driver)
    return {
        'name': name,
        'fraction': fraction,
        'owners': owners,
    }


def main():
    try:
        driver = webdriver.Firefox()
        flat_links = load_flat_links(driver)
        flats = []
        for name, link in flat_links:
            print(f'Loading {name}...')
            try:
                flats.append(load_flat_details(driver, link))
            except NoSuchElementException as e:
                print(name, e)
    finally:
        driver.quit()
    with open('flats.json', 'w') as fout:
        json.dump(flats, fout)


if __name__ == '__main__':
    main()
