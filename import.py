import urllib.request
import json
import datetime
import os
import argparse
import time
import random
from sqlalchemy import or_, and_
from db_utils import get_db_session, shutdown_session_and_engine, create_new_instance_from_item, \
    load_item_into_database, find_instance_from_item
from utils import get_list_of_files, remove_empty_folders, get_files_in_folders
from models import Races, Tracks, Entries, Horses
import csv
from drf import create_track_item_from_drf_data, create_race_item_from_drf_data, create_horse_item_from_drf_data, \
    create_jockey_item_from_drf_data, create_trainer_item_from_drf_data, create_entry_item_from_drf_data, \
    create_owner_item_from_drf_data, create_entry_pool_item_from_drf_data, create_base_wager_amount_dict_from_drf_data, \
    create_payoff_item_from_drf_data, create_probable_item_from_drf_data
from brisnet import scrape_spot_plays, create_track_item_from_brisnet_spot_play, \
    create_race_item_from_brisnet_spot_play, create_horse_item_from_brisnet_spot_play, \
    create_entry_item_from_brisnet_spot_play, create_pick_item_from_brisnet_spot_play
from equibase import get_db_items_from_equibase_whole_card_entry_html, get_equibase_whole_card_entry_url_from_race, \
    get_db_items_from_equibase_horse_html, get_equibase_horse_history_link_from_horse, equibase_entries_link_getter
from distil import initialize_stealth_browser, shutdown_stealth_browser, get_html_from_page_with_captcha
from equibase_charts import convert_equibase_result_chart_pdf_to_item, get_equibase_embedded_chart_link_from_race
from settings import EQUIBASE_PDF_PATH

def test_rp():
    race_url = 'https://www.racingpost.com/results/272/gulfstream-park/2020-01-25/750172'
    with urllib.request.urlopen(race_url) as url:
        print(url.read())


def import_track_codes():

    # setup script dir
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Set file name
    file_name = os.path.join(script_dir, 'resources', 'track_codes.csv')

    # Connect to the database
    session = get_db_session()

    # USA Track Codes
    with open(file_name) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for row in csv_reader:

            # Parse CSV into Variables
            track_item = {
                'code': row[0].strip().upper(),
                'name': row[2].strip().upper(),
                'time_zone': row[3].strip(),
                'country': 'USA'
            }

            # Track Info
            track = load_item_into_database(track_item, 'track', session)

    # Racing Post Codes

    # Set file name
    file_name = os.path.join(script_dir, 'resources', 'rp_track_codes.json')
    with open(file_name) as json_file:
        data = json.load(json_file)

    for rp_track_item in data['usa']:

        # Process String
        rp_code, track = rp_track_item.split(' - ')
        rp_code = int(rp_code.strip())
        track = track.strip().upper()

        # Create db item
        track_item = {
            'name': track,
            'rp_track_code': rp_code
        }

        # Track Info
        track = find_instance_from_item(track_item, 'track', session)
        if track is not None:
            track.rp_track_code = rp_code
            session.commit()

    # Chart Parser Codes

    # Set file name
    file_name = os.path.join(script_dir, 'resources', 'track-codes-chart-parser.csv')
    with open(file_name) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=';')
        for row in csv_reader:
            # Parse CSV into Variables
            track_item = {
                'code': row[0].strip().upper(),
                'equibase_chart_name': row[2].strip().upper(),
                'country': row[1].strip().upper()
            }

            # Track Info
            track = load_item_into_database(track_item, 'track', session)

            if track.time_zone is None:
                track.time_zone = 'US/Eastern'
                session.commit()

    # Close everything out
    shutdown_session_and_engine(session)


def load_drf_odds_data_into_database(data, scrape_time, session):

    # Track Info
    track_item = create_track_item_from_drf_data(data)
    track = find_instance_from_item(track_item, 'track', session)
    if track is None:
        return

    # Race Info
    race_item = create_race_item_from_drf_data(data, track, scrape_time)
    race = load_item_into_database(race_item, 'race', session)
    if race is None:
        return

    # Probable Data
    # Loop through probables
    if data['wagerToteProbables'] is not None:
        for probable_type in data['wagerToteProbables']:
            for probable_dict in data['wagerToteProbables'][probable_type]:
                probable_item = create_probable_item_from_drf_data(probable_dict, race, scrape_time)

                # We're creating a new instance instead of loading the item due to database constraints
                if probable_item is not None:
                    probable = create_new_instance_from_item(probable_item, 'probable', session)

    # Parse Runner Data
    for runner in data['runners']:

        # Load Horse Data
        horse_item = create_horse_item_from_drf_data(runner)
        horse = load_item_into_database(horse_item, 'horse', session)
        if horse is None:
            continue

        # Load Trainer Data
        trainer_item = create_trainer_item_from_drf_data(runner)
        trainer = load_item_into_database(trainer_item, 'trainer', session)
        if trainer is None:
            continue

        # Load Jockey Data
        jockey_item = create_jockey_item_from_drf_data(runner)
        jockey = load_item_into_database(jockey_item, 'jockey', session)
        if jockey is None:
            continue

        # Load Owner Data
        owner = None

        # Load Entry Data
        entry_item = create_entry_item_from_drf_data(runner, horse, race, trainer, jockey, owner, 0)
        entry = load_item_into_database(entry_item, 'entry', session)
        if entry is None:
            continue

        # Load Entry Pool Data
        if runner['horseDataPools'] is not None:
            for data_pool in runner['horseDataPools']:
                entry_pool_item = create_entry_pool_item_from_drf_data(data_pool, entry, scrape_time)

                # We're creating a new instance instead of loading the item due to database constraints
                entry_pool = create_new_instance_from_item(entry_pool_item, 'entry_pool', session)


def load_drf_results_data_into_database(data, scrape_time, session):

    # Track Info
    track_item = create_track_item_from_drf_data(data)
    track = find_instance_from_item(track_item, 'track', session)
    if track is None:
        return

    # Race Info
    race_item = create_race_item_from_drf_data(data, track, scrape_time)
    race = load_item_into_database(race_item, 'race', session)
    if race is None:
        return

    # Payoff Info
    if data['payoffDTOs'] is not None:

        # Get base amount dictionary
        base_wager_amount_dict = create_base_wager_amount_dict_from_drf_data(data)

        # Loop through payoffs
        for payoff in data['payoffDTOs']:
            payoff_item = create_payoff_item_from_drf_data(payoff, race, base_wager_amount_dict)
            payoff = load_item_into_database(payoff_item, 'payoff', session)
            if payoff is None:
                continue

    # Parse Runner Data
    for runner in data['runners']:

        # Load Horse Data
        horse_item = create_horse_item_from_drf_data(runner)
        horse = load_item_into_database(horse_item, 'horse', session)
        if horse is None:
            continue

        # Load Trainer Data
        trainer_item = create_trainer_item_from_drf_data(runner)
        trainer = load_item_into_database(trainer_item, 'trainer', session)
        if trainer is None:
            continue

        # Load Jockey Data
        jockey_item = create_jockey_item_from_drf_data(runner)
        jockey = load_item_into_database(jockey_item, 'jockey', session)
        if jockey is None:
            continue

        # Load Owner Data
        owner_item = create_owner_item_from_drf_data(runner)
        owner = load_item_into_database(owner_item, 'owner', session)

        # Load Entry Data (pools tell order of finish so thats why its zero)
        entry_item = create_entry_item_from_drf_data(runner, horse, race, trainer, jockey, owner, 0)
        entry = load_item_into_database(entry_item, 'entry', session)
        if entry is None:
            continue

    # Parse finish position out of also ran
    if data['alsoRan'] is None:
        order_of_finish = []
    elif isinstance(data['alsoRan'], list):
        order_of_finish = data['alsoRan']
    else:
        first_horses, last_horse = data['alsoRan'].split('  and   ')
        order_of_finish = first_horses.split(', ')
        order_of_finish.append(last_horse)

    for finish_index, horse_name in enumerate(order_of_finish):

        # Load Horse Data
        runner = {'horseName': horse_name.strip().upper()}
        horse_item = create_horse_item_from_drf_data(runner)
        horse = load_item_into_database(horse_item, 'horse', session)
        if horse is None:
            continue

        # Load Entry Data
        entry_item = create_entry_item_from_drf_data(runner, horse, race, None, None, None, finish_index+4)
        entry = load_item_into_database(entry_item, 'entry', session)
        if entry is None:
            continue


def load_drf_entries_data_into_database(data, scrape_time, session):

    # Track Info
    track_item = create_track_item_from_drf_data(data)
    track = find_instance_from_item(track_item, 'track', session)
    if track is None:
        return

    # Race Info
    race_item = create_race_item_from_drf_data(data, track, scrape_time)

    # We don't want to overwrite live odds data with entry data
    race = find_instance_from_item(race_item, 'race', session)
    if race is not None:
        if race.drf_live_odds or race.drf_results:
            return

    # Since we haven't had live odds yet, write the info at will
    race = load_item_into_database(race_item, 'race', session)
    if race is None:
        return

    # Parse Runner Data
    for runner in data['runners']:

        # Load Horse Data
        horse_item = create_horse_item_from_drf_data(runner)
        horse = load_item_into_database(horse_item, 'horse', session)
        if horse is None:
            continue

        # Load Trainer Data
        trainer_item = create_trainer_item_from_drf_data(runner)
        trainer = load_item_into_database(trainer_item, 'trainer', session)
        if trainer is None:
            continue

        # Load Jockey Data
        jockey_item = create_jockey_item_from_drf_data(runner)
        jockey = load_item_into_database(jockey_item, 'jockey', session)
        if jockey is None:
            continue

        # Load Owner Data
        owner = None

        # Load Entry Data
        entry_item = create_entry_item_from_drf_data(runner, horse, race, trainer, jockey, owner, 0)
        entry = load_item_into_database(entry_item, 'entry', session)
        if entry is None:
            continue


def get_single_drf_odds_track_data_from_file(filename):

    if os.path.exists(filename):
        with open(filename) as json_file:
            data = json.load(json_file)
        return data
    else:
        return {}


def get_single_drf_results_track_data_from_file(filename):

    if os.path.exists(filename):
        with open(filename) as json_file:
            data = json.load(json_file)
        return data
    else:
        return {}


def get_all_drf_odds_json_filenames_from_storage(storage_base):

    # Get list of all files in the base directory
    raw_file_list = get_list_of_files(storage_base)

    # Filter them down
    filtered_file_list = list(filter(lambda x: x.endswith('_odds.json'), raw_file_list))

    # Return Data
    return filtered_file_list


def get_all_drf_results_json_filenames_from_storage(storage_base):

    # Get list of all files in the base directory
    raw_file_list = get_list_of_files(storage_base)

    # Filter them down
    filtered_file_list = list(filter(lambda x: x.endswith('_results.json'), raw_file_list))

    # Return Data
    return filtered_file_list


def get_single_track_data_from_drf(track):

    # Form URL
    race_url = f'https://www.drf.com/liveOdds/tracksPoolDetails/currentRace/{track["currentRace"]}/' \
               f'trackId/{track["trackId"]}/' \
               f'country/{track["country"]}/' \
               f'dayEvening/{track["dayEvening"]}/' \
               f'date/{datetime.datetime.now().strftime("%m-%d-%Y")}'

    # Get Data
    with urllib.request.urlopen(race_url) as url:
        data = json.loads(url.read().decode())

    data['drf_scrape'] = {
        'time_scrape_utc': datetime.datetime.utcnow().isoformat()
    }

    # Return
    return data


def get_drf_odds_track_list(request_date):

    # Get current track list
    drf_format_date = request_date.strftime("%m-%d-%Y")
    drf_track_url = f'http://www.drf.com/liveOdds/getTrackList/date/{drf_format_date}'
    with urllib.request.urlopen(drf_track_url) as url:
        data = json.loads(url.read().decode())

    # Return track list
    return data


def get_drf_results_track_list(request_date):

    # Get current track list
    drf_format_date = request_date.strftime("%m-%d-%Y")
    drf_track_url = f'https://www.drf.com/results/raceTracks/page/results/date/{drf_format_date}'
    with urllib.request.urlopen(drf_track_url) as url:
        data = json.loads(url.read().decode())

    # Return track list
    return data


def get_drf_entries_track_list(request_date):

    # Get current track list
    drf_format_date = request_date.strftime("%m-%d-%Y")
    # https://www.drf.com/results/raceTracks/page/entries/date/05-08-2020
    # https://www.drf.com/entries/entryDetails/id/GP/country/USA/date/05-07-2020
    drf_track_url = f'https://www.drf.com/results/raceTracks/page/entries/date/{drf_format_date}'
    with urllib.request.urlopen(drf_track_url) as url:
        data = json.loads(url.read().decode())

    # Return track list
    return data


def save_single_track_drf_odds_data_to_file(data, save_dir):

    # Get necessary data
    race_scraped_datetime = datetime.datetime.fromisoformat(data['drf_scrape']['time_scrape_utc'])
    if int(data['raceKey']['raceDate']['date']) > 0:
        race_datetime = datetime.datetime(
            day=data['raceKey']['raceDate']['day'],
            month=data['raceKey']['raceDate']['month'] + 1,
            year=data['raceKey']['raceDate']['year']
        )
    else:
        print('date is negative!')
        race_datetime = datetime.datetime.fromisoformat(data['drf_scrape']['time_scrape_utc'])
    track_id = data['raceKey']['trackId']

    # Assemble path
    data_path = os.path.join(
        save_dir,
        track_id,
        str(race_datetime.year),
        str(race_datetime.month),
        str(race_datetime.day)
    )
    data_filepath = os.path.join(
        data_path,
        f'{track_id}_'
        f'{race_datetime.year:04.0f}{race_datetime.month:02.0f}{race_datetime.day:02.0f}_'
        f'{data["raceKey"]["raceNumber"]}_'
        f'{race_scraped_datetime.year:04.0f}{race_scraped_datetime.month:02.0f}{race_scraped_datetime.day:02.0f}T'
        f'{race_scraped_datetime.hour:02.0f}{race_scraped_datetime.minute:02.0f}{race_scraped_datetime.second:02.0f}_'
        f'odds.json'
    )

    # Verify Folder Exists
    if not os.path.exists(data_path):
        os.makedirs(data_path)

    # Write File
    with open(data_filepath, 'w') as outfile:
        json.dump(data, outfile)


def get_current_drf_odds_track_list():

    # Wrapper for the current time
    return get_drf_odds_track_list(datetime.datetime.now())


def get_current_drf_results_track_list():

    # Wrapper for the current time
    return get_drf_results_track_list(datetime.datetime.now())


def get_current_drf_entries_track_list():

    # Wrapper for the current time
    return get_drf_entries_track_list(datetime.datetime.now())


def get_single_race_day_drf_results(date, track_id, country):

    # Form URL
    drf_format_date = date.strftime("%m-%d-%Y")
    race_url = f'https://www.drf.com/results/resultDetails/id/{track_id}/country/{country}/date/{drf_format_date}'

    # Get Data
    with urllib.request.urlopen(race_url) as url:
        data = json.loads(url.read().decode())

    data['drf_scrape'] = {
        'time_scrape_utc': datetime.datetime.utcnow().isoformat()
    }

    # Return
    return data


def get_single_race_day_drf_entries(date, track_id, country):

    # Form URL
    drf_format_date = date.strftime("%m-%d-%Y")
    race_url = f'https://www.drf.com/entries/entryDetails/id/{track_id}/country/{country}/date/{drf_format_date}'

    # Get Data
    with urllib.request.urlopen(race_url) as url:
        data = json.loads(url.read().decode())

    data['drf_scrape'] = {
        'time_scrape_utc': datetime.datetime.utcnow().isoformat()
    }

    # Return
    return data


def save_single_track_drf_results_data_to_file(data, save_dir):

    # Figure out the first race
    if len(data['races']) <= 0:
        return
    first_race = data['races'][0]

    # Get necessary data
    if int(first_race['raceKey']['raceDate']['date']) > 0:
        race_datetime = datetime.datetime(
            day=first_race['raceKey']['raceDate']['day'],
            month=first_race['raceKey']['raceDate']['month'] + 1,
            year=first_race['raceKey']['raceDate']['year']
        )
    else:
        print('date is negative!')
        race_datetime = datetime.datetime.fromisoformat(data['drf_scrape']['time_scrape_utc'])
    track_id = first_race['raceKey']['trackId']

    # Assemble path
    data_path = os.path.join(
        save_dir, track_id,
        str(race_datetime.year),
        str(race_datetime.month),
        str(race_datetime.day)
    )
    data_filepath = os.path.join(
        data_path,
        f'{track_id}_'
        f'{race_datetime.year:04.0f}{race_datetime.month:02.0f}{race_datetime.day:02.0f}_'
        f'results.json'
    )

    # Verify Folder Exists
    if not os.path.exists(data_path):
        os.makedirs(data_path)

    # Write File
    with open(data_filepath, 'w') as outfile:
        json.dump(data, outfile)


def get_races_with_no_results(session):

    # Query Races
    races = session.query(Races).\
        filter_by(drf_results=False).\
        filter(Races.post_time <= datetime.datetime.utcnow()).all()

    # Organize in list
    race_list = []
    for race in races:

        # Get Track Code
        track = session.query(Tracks).filter_by(track_id=race.track_id).first()

        # Append to list
        race_list.append({
            'card_date': race.card_date,
            'track_id': track.code,
            'country': race.country,
            'race_id': race.race_id
        })

    # Return Missing
    return race_list


def load_brisnet_spot_play_into_database(data, session):

    # Track Info
    track_item = create_track_item_from_brisnet_spot_play(data)  # CHANGE TO RETRIEVE ONLY
    track = find_instance_from_item(track_item, 'track', session)
    if track is None:
        return

    # Race Info
    race_item = create_race_item_from_brisnet_spot_play(data, track)
    race = find_instance_from_item(race_item, 'race', session)
    if race is None:
        return

    # Horse Info
    horse_item = create_horse_item_from_brisnet_spot_play(data)
    horse = find_instance_from_item(horse_item, 'horse', session)
    if horse is None:
        return

    # Entry Info
    entry_item = create_entry_item_from_brisnet_spot_play(race, horse)
    entry = find_instance_from_item(entry_item, 'entry', session)
    if entry is None:
        return

    # Pick Info
    pick_item = create_pick_item_from_brisnet_spot_play(data, race, entry)
    pick = find_instance_from_item(pick_item, 'pick', session)
    if pick is None:
        pick = load_item_into_database(pick_item, 'pick', session)


def load_equibase_entries_into_database(whole_card_data, session):

    # Loop through whole card
    for data in whole_card_data:

        # Track Info
        track_item = data['track_item']
        track = find_instance_from_item(track_item, 'track', session)
        if track is None:
            return

        # Race Info (only update if it exists)
        race_item = data['race_item']
        race_item['track_id'] = track.track_id
        race = find_instance_from_item(race_item, 'race', session)
        if race is None:
            return
        else:
            race = load_item_into_database(race_item, 'race', session)

        # Entry Info
        for equibase_entry in data['entry_items']:

            # Horse Info
            horse_item = equibase_entry['horse_item']
            if horse_item is not None:
                horse = load_item_into_database(horse_item, 'horse', session)

            # Trainer Info (only update if it exists)
            trainer_item = equibase_entry['trainer_item']
            if trainer_item is not None:

                # since first name is an initial, find the instance first and update the first name
                trainer = find_instance_from_item(trainer_item, 'trainer', session)
                if trainer is not None:
                    trainer_item['first_name'] = trainer.first_name
                    trainer = load_item_into_database(trainer_item, 'trainer', session)

            # Jockey Info (only update if it exists)
            jockey_item = equibase_entry['jockey_item']
            if jockey_item is not None:

                # since first name is an initial, find the instance first and update the first name
                jockey = find_instance_from_item(jockey_item, 'jockey', session)
                if jockey is not None:
                    jockey_item['first_name'] = jockey.first_name
                    jockey = load_item_into_database(jockey_item, 'jockey', session)


def get_equibase_entry_links_for_races_without_entries(session):

    # Init link list
    link_list = []

    # Earliest Entry Date
    today = datetime.datetime.now().date()
    min_entries = today + datetime.timedelta(days=-1)
    max_entries = today + datetime.timedelta(days=2)

    # Query for races
    races = session.query(Races).filter(
        Races.equibase_entries.is_(False),
        Races.drf_entries.is_(True),
        Races.card_date <= max_entries,
        Races.card_date >= min_entries
    ).all()

    # Create links for races
    for race in races:
        link_list.append(get_equibase_whole_card_entry_url_from_race(session, race))

    # Remove duplicates
    link_list = list(dict.fromkeys(link_list))

    # Return completed list
    return link_list


def get_equibase_horse_links_for_entry_horses_without_details(session):

    # Init link list
    link_list = []

    # Last week
    min_date = datetime.datetime.utcnow() + datetime.timedelta(days=-7)
    min_date_only = datetime.date(min_date.year, min_date.month, min_date.day)

    # Perform Query
    horses = session.query(Horses).join(Entries).join(Races).filter(
        Races.equibase_entries.is_(True),
        Horses.equibase_horse_id.isnot(None),
    ).filter(or_(
        Horses.equibase_horse_detail_scrape_date.is_(None),
        and_(
            Races.post_time > datetime.datetime.utcnow(),
            Horses.equibase_horse_detail_scrape_date < min_date,
        ),
        and_(
            Horses.equibase_horse_detail_scrape_date < Races.post_time,
            Races.post_time < (datetime.datetime.utcnow() + datetime.timedelta(days=-2))
        ),
        and_(
            Entries.equibase_speed_figure == 999,
            Races.card_date > min_date_only
        )
    )).all()

    # Create URLs
    for horse in horses:
        link_list.append(get_equibase_horse_history_link_from_horse(horse))

    # Remove duplicates
    link_list = list(dict.fromkeys(link_list))

    # Return list
    return link_list


def load_equibase_horse_data_into_database(data, session):

    # Load Horse Data
    horse_item = data['horse_item']
    horse = load_item_into_database(horse_item, 'horse', session)
    if horse is None:
        return

    # Cycle through results items
    for results_item in data['entry_items']:

        # Track Info
        track_item = results_item['track_item']
        track = load_item_into_database(track_item, 'track', session)
        if track is None:
            continue

        # Race Info
        race_item = results_item['race_item']
        race_item['track_id'] = track.track_id
        race = load_item_into_database(race_item, 'race', session)
        if race is None:
            return

        # Load Entry Data
        entry_item = results_item['entry_item']
        entry_item['race_id'] = race.race_id
        entry_item['horse_id'] = horse.horse_id
        entry = load_item_into_database(entry_item, 'entry', session)
        if entry is None:
            continue

    # Cycle through results items
    for workout_group_item in data['workout_items']:

        # Track Info
        track_item = workout_group_item['track_item']
        track = load_item_into_database(track_item, 'track', session)
        if track is None:
            continue

        # Workout Info
        workout_item = workout_group_item['workout_item']
        workout_item['horse_id'] = horse.horse_id
        workout_item['track_id'] = track.track_id
        workout = load_item_into_database(workout_item, 'workout', session)
        if workout is None:
            continue


def load_equibase_chart_data_into_database(data, session):

    # init return race list
    races = []

    for data_item in data:

        # Track Info
        track_item = data_item['track_item']
        track = find_instance_from_item(track_item, 'track', session)
        if track is None:
            return

        # Race Info
        race_item = data_item['race_item']
        race_item['track_id'] = track.track_id
        race = load_item_into_database(race_item, 'race', session)
        races.append(race)
        if race is None:
            return


        # Fractional Times
        for fractional_item in data_item['fractional_data']:
            fractional_item['race_id'] = race.race_id
            fractional_instance = load_item_into_database(fractional_item, 'fractional_time', session)

        # Entries
        for entry_data in data_item['entry_data']:

            # Load Horse Data
            horse_item = entry_data['horse_item']
            horse = load_item_into_database(horse_item, 'horse', session)
            if horse is None:
                return

            # Jockey Data
            jockey_item = entry_data['jockey_item']
            jockey = load_item_into_database(jockey_item, 'jockey', session)

            # Load Entry Data
            entry_item = entry_data['entry_item']
            entry_item['race_id'] = race.race_id
            entry_item['horse_id'] = horse.horse_id
            entry = load_item_into_database(entry_item, 'entry', session)
            if entry is None:
                continue

            # Load point of call
            point_of_call_list = entry_data['point_of_call_list']
            for point_of_call_item in point_of_call_list:
                point_of_call_item['entry_id'] = entry.entry_id
                point_of_call = load_item_into_database(point_of_call_item, 'point_of_call', session)

    # return race list so we can check if it finished
    return races


def fix_horse_registry(session):

    # Variables
    registries = ['Q', 'G', 'T', 'K']
    types = ['MX', 'TB', 'QH']

    # Perform query
    horses = session.query(Horses).all()

    # Iterate all
    for horse in horses:
        if horse.equibase_horse_type and horse.equibase_horse_registry:
            if horse.equibase_horse_type in registries and horse.equibase_horse_registry in types:
                old_registry = horse.equibase_horse_registry
                old_type = horse.equibase_horse_type
                horse.equibase_horse_registry = old_type
                horse.equibase_horse_type = old_registry
                print(f'fixing {horse.horse_id}')
            elif horse.equibase_horse_type in types and horse.equibase_horse_registry in registries:
                pass
            else:
                print(f'{horse.horse_id} is weird with type:'
                      f'{horse.equibase_horse_type} and reg:{horse.equibase_horse_registry}')
        else:
            pass

    session.commit()


def download_equibase_charts(session, browser):

    # Loop while theres still charts to download
    while session.query(Races).filter(
            Races.equibase_chart_download_date.is_(None),
            Races.equibase_chart_scrape.isnot(True)
    ).count() > 0:

        # Get oldest race
        race = session.query(Races).filter(
            Races.equibase_chart_download_date.is_(None),
            Races.equibase_chart_scrape.isnot(True)
        ).order_by(
            Races.card_date
        ).first()

        # Download pdf
        chart_link = get_equibase_embedded_chart_link_from_race(db_session, race)
        try:
            pdf_path = get_html_from_page_with_captcha(browser, chart_link, 'object[type][data]')
        except:
            print(f'an exception happened during download of {chart_link}')
            pdf_path = None

        # Verify file download
        if pdf_path:
            if os.path.exists(pdf_path):
                download_date = datetime.datetime.now()
                print(f'Successfully downloaded {pdf_path}')
            else:
                download_date = datetime.datetime(year=1900, month=1, day=1)
        else:
            download_date = datetime.datetime(year=1900, month=1, day=1)

        # Write confirmation of download to database
        downloaded_races = session.query(Races).filter(Races.card_date == race.card_date,
                                                          Races.track_id == race.track_id).all()
        for downloaded_race in downloaded_races:
            downloaded_race.equibase_chart_download_date = download_date
            session.commit()

        # Pause because were nice
        time.sleep(15)


def scrape_equibase_charts(session):

    # Remove empty folders
    remove_empty_folders(EQUIBASE_PDF_PATH)

    # get file list
    file_list = sorted(get_files_in_folders(EQUIBASE_PDF_PATH))

    # loop throug list
    for file in file_list:

        # Check if it still exists
        if not os.path.exists(file):
            continue

        if file[-3:] != 'pdf':
            continue

        # parse the file
        pdf_items = convert_equibase_result_chart_pdf_to_item(file)

        # load the file in the database
        updated_races = load_equibase_chart_data_into_database(pdf_items, session)

        if updated_races is None:
            print(f'{file} resulted in 0 updated races')
        elif len(updated_races) == 0:
            print(f'{file} resulted in 0 updated races')
        elif None in updated_races:
            print(f'{file} had a None race')
        else:
            print(f'{file} parsed into {len(updated_races)} races and should be deleted')
            try:
                os.remove(file)
            except PermissionError:
                print(f'there was a problem deleting {file}')

    # remove empty folders again
    remove_empty_folders(EQUIBASE_PDF_PATH)


if __name__ == '__main__':

    # Argument Parsing
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--mode',
                            help="Mode of operation (odds: store odds files)",
                            type=str,
                            required=True,
                            metavar='MODE'
                            )
    args = arg_parser.parse_args()

    # Setup mode tracker
    modes_run = []

    # Check mode
    if args.mode in ('drf_entries', 'drf', 'all'):

        # Mode Tracking
        modes_run.append('drf_entries')

        # Get tracks
        track_data = get_current_drf_entries_track_list()

        # Loop if theres tracks
        if len(track_data['raceTracks']['allTracks']) > 0:

            # Connect to the database
            db_session = get_db_session()

            for current_track in track_data['raceTracks']['allTracks']:
                for card in current_track['cards']:
                    if card['raceDate']['year'] is not None and \
                            card['raceDate']['month'] is not None and \
                            card['raceDate']['day'] is not None:
                        card_date = datetime.date(
                            year=card['raceDate']['year'],
                            month=(card['raceDate']['month']+1),
                            day=card['raceDate']['day']
                        )
                        entry_data = get_single_race_day_drf_entries(
                            card_date,
                            current_track['trackId'],
                            current_track['country']
                        )
                        current_scrape_time = datetime.datetime.fromisoformat(
                            entry_data['drf_scrape']['time_scrape_utc']
                        )
                        for index, race_data in enumerate(entry_data['races']):
                            load_drf_entries_data_into_database(race_data, current_scrape_time, db_session)

            # Close everything out
            shutdown_session_and_engine(db_session)

    if args.mode in ('drf_odds', 'drf', 'all'):

        # Mode Tracking
        modes_run.append('drf_odds')

        # Get currently running tracks
        track_data_list = list()
        track_data = get_current_drf_odds_track_list()

        if len(track_data) > 0:

            # Connect to the database
            db_session = get_db_session()

            # Iterate through tracks
            for current_track in track_data:
                if current_track['country'] == 'USA':
                    track_data_list.append(get_single_track_data_from_drf(current_track))

            # Iterate through tracks
            for race_data in track_data_list:
                current_scrape_time = datetime.datetime.fromisoformat(race_data['drf_scrape']['time_scrape_utc'])
                load_drf_odds_data_into_database(race_data, current_scrape_time, db_session)

            # Close everything out
            shutdown_session_and_engine(db_session)

    if args.mode in ('drf_missing', 'drf', 'all'):

        # Mode Tracking
        modes_run.append('drf_missing')

        # Connect to the database
        db_session = get_db_session()

        # Get missing tracks
        missing_races = get_races_with_no_results(db_session)

        # Loop if theres races
        for current_race in missing_races:

            # Double check its still missing data
            current_race_instance = db_session.query(Races).filter_by(race_id=current_race['race_id']).one()
            if current_race_instance.drf_results:
                continue

            # Get Track Code
            track_code = current_race

            # Get data
            results_data = get_single_race_day_drf_results(
                current_race['card_date'],
                current_race['track_id'],
                current_race['country']
            )
            current_scrape_time = datetime.datetime.fromisoformat(
                results_data['drf_scrape']['time_scrape_utc']
            )
            if results_data['isData']:
                for index, race_data in enumerate(results_data['races']):
                    race_data['postTimeLong'] = results_data['allRaces'][index]['postTime']
                    load_drf_results_data_into_database(race_data, current_scrape_time, db_session)

        # Close everything out
        shutdown_session_and_engine(db_session)

    if args.mode in ('track_codes'):

        # Mode Tracking
        modes_run.append('track_codes')

        import_track_codes()

    # Check mode
    if args.mode in ('brisnet_spot_plays', 'all', 'outside_picks'):

        # Mode Tracking
        modes_run.append('brisnet_spot_plays')

        # Get the picks
        pick_data = scrape_spot_plays()

        # Connect to the database
        db_session = get_db_session()

        for current_pick in pick_data:
            load_brisnet_spot_play_into_database(current_pick, db_session)

        # Close everything out
        shutdown_session_and_engine(db_session)

    # Check mode
    if args.mode in ('equibase_entries', 'equibase', 'all'):

        # Mode Tracking
        modes_run.append('equibase_entries')

        # Initialize browser
        browser = initialize_stealth_browser()

        # Connect to the database
        db_session = get_db_session()

        # Get HTML for entries page
        html = get_html_from_page_with_captcha(
            browser,
            'http://www.equibase.com/static/entry/index.html',
            'a.entrSpacing')

        # Get Links
        equibase_link_list = equibase_entries_link_getter(html)

        # Process links
        for equibase_link_url in equibase_link_list:
            print(f'getting {equibase_link_url}')
            whole_card_html = get_html_from_page_with_captcha(browser, equibase_link_url, 'div.race-nav.center')
            db_items = get_db_items_from_equibase_whole_card_entry_html(whole_card_html)
            load_equibase_entries_into_database(db_items, db_session)
            sleep_number = random.randrange(20, 40)
            print(f'Sleeping {sleep_number} seconds')
            time.sleep(sleep_number)

        # Close everything out
        shutdown_session_and_engine(db_session)
        shutdown_stealth_browser(browser)

    # Check mode
    if args.mode in ('equibase_horse_details', 'equibase', 'all'):

        # Mode Tracking
        modes_run.append('equibase_horse_details')

        # Connect to the database
        db_session = get_db_session()

        # Get links
        equibase_link_list = get_equibase_horse_links_for_entry_horses_without_details(db_session)
        print(f'Running for {len(equibase_link_list)} links')

        # Initialize browser
        browser = initialize_stealth_browser()

        for equibase_link_url in equibase_link_list:
            print(f'getting {equibase_link_url}')
            horse_html = get_html_from_page_with_captcha(browser, equibase_link_url, 'td.track')
            db_items = get_db_items_from_equibase_horse_html(horse_html)
            load_equibase_horse_data_into_database(db_items, db_session)
            sleep_number = random.randrange(15, 30)
            print(f'Sleeping {sleep_number} seconds')
            time.sleep(sleep_number)

        # Close everything out
        shutdown_session_and_engine(db_session)
        shutdown_stealth_browser(browser)

    if args.mode in ('reset_tables'):

        # Mode Tracking
        modes_run.append('reset_tables')

        # Connect and destroy tables
        db_session = get_db_session(destroy_flag=True)
        shutdown_session_and_engine(db_session)

        # Import Tracks
        import_track_codes()

    if args.mode in ('fix_equibase_horse_registry'):

        # Mode Tracking
        modes_run.append('fix_equibase_horse_registry')

        # Get database
        db_session = get_db_session()

        # Fix things
        fix_horse_registry(db_session)

        # Shut it down
        shutdown_session_and_engine(db_session)

    if args.mode in ('download_equibase_charts', 'all'):

        # Mode Tracking
        modes_run.append('download_equibase_charts')

        # Get database
        db_session = get_db_session()

        # Initialize browser
        browser = initialize_stealth_browser()

        # Run code
        download_equibase_charts(db_session, browser)

        # Close everything out
        shutdown_session_and_engine(db_session)
        shutdown_stealth_browser(browser)

    if args.mode in ('scrape_equibase_charts', 'all'):

        # Mode Tracking
        modes_run.append('scrape_equibase_charts')

        # Get database
        db_session = get_db_session()

        # run code
        scrape_equibase_charts(db_session)

        # close database
        shutdown_session_and_engine(db_session)

    if args.mode in ('test'):

        # Mode Tracking
        modes_run.append('scrape_equibase_charts')

        # Get database
        db_session = get_db_session()

        # run code
        scrape_equibase_charts(db_session)

        # close database
        shutdown_session_and_engine(db_session)

    if len(modes_run) == 0:

        print(f'"{args.mode}" is not a valid operational mode!')
        exit(1)

    else:

        print(f'We ran the following modes successfully: {",".join(modes_run)}')
