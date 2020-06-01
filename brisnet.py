import os
from selenium import webdriver
from bs4 import BeautifulSoup
import re
import datetime
import time
from settings import SELENIUM_DRIVER_PATH
from sqlalchemy.sql import null
from utils import get_horse_origin_from_name

def create_driver():

    # Create Options
    driver_options = webdriver.ChromeOptions()
    driver_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    driver_options.add_experimental_option('useAutomationExtension', False)
    driver_options.headless = True

    # Create driver
    return_driver = webdriver.Chrome(options=driver_options, executable_path=SELENIUM_DRIVER_PATH)

    # Return created driver
    return return_driver


def scrape_spot_plays():

    # Create return data
    spot_plays = []

    # Spot Plays URL
    url = 'http://www.brisnet.com/content/category/spot-plays/'

    # Setup selenium for scraping
    driver = create_driver()

    # Goto first url
    driver.get(url)

    # Get html of main page
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')

    # Get the links we need to follow
    spot_play_links = []
    spot_play_h3_list = soup.findAll('h3', {'class': ['entry-title', 'mh-loop-title']})
    for spot_play_h3 in spot_play_h3_list:
        spot_play_h3_href = spot_play_h3.find('a', href=True)
        spot_play_links.append(spot_play_h3_href['href'])

    # Follow the links
    for spot_play_link in spot_play_links:

        # Go to the page
        time.sleep(3)  # so they don't catch on to us
        driver.get(spot_play_link)

        # Get html of spot play page
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # Find Title
        title_h1 = soup.find('h1', class_='entry-title')
        if title_h1 is None:
            continue
        title_text = title_h1.text.strip().upper()

        # Find Entry Date
        entry_data_p = soup.find('p', {'class': ['mh-meta', 'entry-meta']})
        if entry_data_p is None:
            continue
        entry_data_spans = entry_data_p.findAll('span')

        try:
            entry_date = datetime.datetime.strptime(entry_data_spans[0].text.strip(), '%b %d, %Y').date()
        except ValueError:
            entry_date = datetime.datetime.strptime(entry_data_spans[0].text.strip(), '%B %d, %Y').date()

        # Find Pick Date
        spot_play_pattern = r'SPOT PLAYS ([a-zA-Z]+) ([0-9]+)'
        search_object = re.search(spot_play_pattern, title_text)
        if search_object:
            try:
                pick_date = datetime.datetime.strptime(
                    f'{search_object.group(1)} {search_object.group(2)}, {entry_date.year}',
                    '%b %d, %Y'
                ).date()
            except ValueError:
                pick_date = datetime.datetime.strptime(
                    f'{search_object.group(1)} {search_object.group(2)}, {entry_date.year}',
                    '%B %d, %Y'
                ).date()
        else:
            break
        if pick_date < entry_date:
            pick_date = pick_date + datetime.timedelta(year=1)

        # Find Tables
        tables = soup.findAll('table')

        # Check if the number of tables has changed
        if len(tables) != 2:
            continue
        cells = tables[0].findAll('td')

        # Check if the first table is correct
        if cells is None:
            continue
        if cells[0].text != 'TRACK':
            continue

        # Loop through tracks
        current_track = ''
        for row in tables[1].findAll('tr'):
            cells = row.findAll('td')
            if cells[0].text != '':
                current_track = cells[0].text.strip().upper()

            pick_text = cells[2].text.strip().upper()
            pick_pattern = r'\((\d+)[a-zA-Z]+\) ([a-zA-Z0-9 \(\)\.\-]+), '
            search_object = re.search(pick_pattern, pick_text)
            if search_object is None:
                continue
            race_number = search_object.group(1)
            horse_name = search_object.group(2)

            # Create Spot Pick
            spot_play = {
                'track_name': current_track,
                'race_date': pick_date,
                'race_number': race_number,
                'horse_name': horse_name
            }
            spot_plays.append(spot_play)

    # Close the driver
    driver.quit()

    # Return finished list
    return spot_plays


def create_track_item_from_brisnet_spot_play(spot_play):

    # Create Track Dict
    item = dict()
    item['name'] = spot_play['track_name'].strip().upper()

    # Return created track item
    return item


def create_race_item_from_brisnet_spot_play(spot_play, track):

    # Create Track Dict
    item = dict()
    item['track_id'] = track.track_id
    item['race_number'] = spot_play['race_number']
    item['card_date'] = spot_play['race_date']

    # Return created track item
    return item


def create_horse_item_from_brisnet_spot_play(spot_play):

    # Create Horse Dict
    item = dict()

    # Parse name
    horse_name, horse_country, horse_state = get_horse_origin_from_name(spot_play['horse_name'].strip().upper())

    # Fill in horse data
    item['horse_name'] = horse_name
    item['horse_country'] = horse_country
    if horse_state is not None:
        item['horse_state'] = horse_state

    # Return created track item
    return item


def create_entry_item_from_brisnet_spot_play(race, horse):

    # Create Horse Dict
    item = dict()
    item['horse_id'] = horse.horse_id
    item['race_id'] = race.race_id

    # Return created track item
    return item


def create_pick_item_from_brisnet_spot_play(spot_play, race, entry):

    # Create Horse Dict
    item = dict()
    item['bettor_family'] = 'brisnet'
    item['bettor_name'] = 'spot play'
    item['race_id'] = race.race_id
    item['bet_type'] = 'WIN'
    item['bet_cost'] = 2
    item['bet_return'] = null()
    item['bet_win_text'] = entry.program_number
    item['bet_origin_date'] = datetime.datetime.now()


    # Return created track item
    return item
