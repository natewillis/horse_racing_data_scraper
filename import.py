import urllib.request
import json
import datetime
import os
import argparse
from pytz import timezone, utc
from models import db_connect, Races, Horses, Entries, EntryPools, Payoffs, Probables, create_drf_live_table
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from pint import UnitRegistry


def s2f(x):
    try:
        return float(x)
    except ValueError:
        return 'NaN'


def p2f(x):
    try:
        return float(x.strip('%'))/100
    except ValueError:
        return 'NaN'


def convert_drf_distance_description_to_furlongs(distance_string):

    # Load unit conversion
    ureg = UnitRegistry()

    # Distance Calcs
    # Error check distance values
    if distance_string == 'NaN':
        return 0

    # Split description up
    split_description = distance_string.lower().split()
    if len(split_description) == 2:
        distance_string = distance_string.lower()
        distance = ureg(distance_string)
    elif len(split_description) == 3:
        split_division = split_description[1].split('/')
        if len(split_division) == 2:
            split_number = float(split_description[0]) + (float(split_division[0]) / float(split_division[1]))
            distance_string = f'{split_number} {split_description[2]}'
            distance = ureg(distance_string)
        else:
            return 0
    elif len(split_description) == 4:
        distance = ureg(f'{split_description[0]} {split_description[1]}') + \
                   ureg(f'{split_description[2]} {split_description[3]}')
    else:
        print(f'Something really weird is with {distance_string.lower()}')
        return 0

    # Error check conversion
    if not (distance.check('[length]')):
        print(f'Something is wrong with {distance_string}')
        return 0

    return distance.to(ureg.furlong).magnitude


def load_drf_race_data_into_database(data, scrape_time, session):

    # Create Race Dict
    item = dict()

    # Error Checking (malformed post_time)
    if data['postTimeLong'] < 956861285000:

        # Get post time string
        if data['postTimeDisplay'] is not None:
            post_time_string = data['postTimeDisplay']
        elif data['postTime'] is not None:
            post_time_string = data['postTime']
        else:
            print('both post time strings are bad')
            return

        # Strip out the components of the post time
        post_time_time_part, post_time_am_pm = post_time_string.split(' ')
        post_time_hour, post_time_minute = post_time_time_part.split(':')
        if post_time_am_pm == 'PM':
            if int(post_time_hour) < 12:
                post_time_hour = int(post_time_hour) + 12
            else:
                post_time_hour = int(post_time_hour)
        else:
            if int(post_time_hour) < 12:
                post_time_hour = int(post_time_hour)
            else:
                post_time_hour = int(post_time_hour) - 12
        post_time_minute = int(post_time_minute)
        if post_time_hour < 0 or post_time_hour > 23:
             print(f'{post_time_string} is weird!')

        # Get Time Zone
        if data['timeZone'] != 'NaN':
            time_zone_dict = {
                'E': 'US/Eastern',
                'C': 'US/Central',
                'M': 'US/Mountain',
                'P': 'US/Pacific'
            }
            time_zone_selection = time_zone_dict.get(data['timeZone'], 'Invalid')
            if time_zone_selection == 'Invalid':
                print(f'{data["timeZone"]} is not a valid timezone')

        # Assemble Time
        post_time_local = datetime.datetime(
            year=data['raceKey']['raceDate']['year'],
            month=data['raceKey']['raceDate']['month']+1,
            day=data['raceKey']['raceDate']['day'],
            hour=post_time_hour,
            minute=post_time_minute,
            tzinfo=timezone(time_zone_selection)
        )
        post_time = post_time_local.astimezone(timezone('UTC'))

    else:
        post_time = datetime.datetime.fromtimestamp(data['postTimeLong'] / 1000.0)  # UTC Already

    # Identifying Info
    item['track_id'] = data['raceKey']['trackId']
    item['race_number'] = data['raceKey']['raceNumber']
    item['post_time'] = post_time  # UTC Already
    item['day_evening'] = data['raceKey']['dayEvening']
    item['country'] = data['raceKey']['country']

    # Common
    item['distance'] = convert_drf_distance_description_to_furlongs(data['distanceDescription'])
    if item['distance'] <= 0:
        return
    item['age_restriction'] = data['ageRestrictionDescription']
    item['race_restriction'] = data['raceRestrictionDescription']
    item['sex_restriction'] = data['sexRestrictionDescription']
    item['race_surface'] = data['surfaceDescription']
    item['race_type'] = data['raceTypeDescription']
    item['breed'] = data['breed']

    # Results
    if 'payoffs' in data:
        # Results Datafiles
        item['results'] = True
        item['purse'] = int(data['totalPurse'].replace(',', ''))
        item['track_condition'] = data['trackConditionDescription']
    else:
        # Odds Datafiles
        item['purse'] = data['purse']
        item['wager_text'] = data['wagerText']


    # Scraping info
    item['latest_scrape_time'] = scrape_time

    # Check for existing record
    race = session.query(Races).filter(
        Races.track_id == item['track_id'],
        Races.race_number == item['race_number'],
        func.date_trunc('day', Races.post_time) == func.date_trunc('day', item['post_time'])
    ).first()

    # If its new, create a new one in the database
    if race is None:

        # Process Race
        race = Races(**item)

        # Add To Table (after commit, id is filled in)
        session.add(race)

    # Otherwise, update the record with the new values and commit it
    else:

        # Set the new attributes
        for key, value in item.items():
            setattr(race, key, value)

    # Commit changes whichever way it went
    session.commit()

    # Return race instance
    return race


def load_drf_horse_data_into_database(runner, session):

    # Create Horse Dict
    item = dict()
    item['horse_name'] = runner['horseName'].strip()

    # Check for existing record
    horse = session.query(Horses).filter(Horses.horse_name == item['horse_name']).first()

    # If its new, create a new one in the database
    if horse is None:

        # Process New Record
        horse = Horses(**item)

        # Add To Table (after commit, d is filled in)
        session.add(horse)

    # Otherwise, update the record with the new values and commit it
    else:

        # Set the new attributes
        for key, value in item.items():
            setattr(horse, key, value)

    # Commit changes whichever way it went
    session.commit()

    # Return horse record
    return horse


def load_drf_entry_data_into_database(runner, session, horse, race, finish_position):

    # Create Entry Dict
    item = dict()
    item['race_id'] = race.race_id
    item['horse_id'] = horse.horse_id
    if 'scratchIndicator' in runner:
        item['scratch_indicator'] = runner['scratchIndicator']
    else:
        item['scratch_indicator'] = 'N'

    if 'postPos' in runner:
        item['post_position'] = runner['postPos']

    if 'programNumber' in runner:
        item['program_number'] = runner['programNumber']

    # Results
    if 'winPayoff' in runner:
        item['win_payoff'] = runner['winPayoff']
        item['place_payoff'] = runner['placePayoff']
        item['show_payoff'] = runner['showPayoff']

        if item['win_payoff'] > 0:
            item['finish_position'] = 1
        elif item['place_payoff'] > 0:
            item['finish_position'] = 2
        elif item['show_payoff'] > 0:
            item['finish_position'] = 3

    # Finish Position
    if finish_position > 0:
        item['finish_position'] = finish_position

    # Check for existing record
    entry = session.query(Entries).filter(Entries.race_id == item['race_id'],
                                          Entries.horse_id == item['horse_id']).first()

    # If its new, create a new one in the database
    if entry is None:

        # Process New Record
        entry = Entries(**item)

        # Add To Table (after commit, id is filled in)
        session.add(entry)

    # Otherwise, update the record with the new values and commit it
    else:

        # Set the new attributes
        for key, value in item.items():
            setattr(entry, key, value)

    # Commit changes whichever way it went
    session.commit()

    # Return entry variable
    return entry


def load_drf_odds_entry_pool_data_into_database(runner, session, entry, scrape_time):

    if runner['horseDataPools'] is None:
        return

    for data_pool in runner['horseDataPools']:

        # Odds processing
        odds_split = data_pool['fractionalOdds'].split('-')
        if len(odds_split) != 2:
            odds_value = -1
        else:
            odds_value = float(odds_split[0])/float(odds_split[1])

        # Create Entry Dict
        item = dict()
        item['entry_id'] = entry.entry_id
        item['scrape_time'] = scrape_time
        item['pool_type'] = data_pool['poolTypeName']
        item['amount'] = float(data_pool['amount'])
        if odds_value >= 0:
            item['odds'] = odds_value
        item['dollar'] = float(data_pool['dollar'])

        # Check for existing record
        if 1==1:
            entry_pool = session.query(EntryPools).filter(
                EntryPools.entry_id == item['entry_id'],
                EntryPools.scrape_time == item['scrape_time'],
                EntryPools.pool_type == item['pool_type']
            ).first()
        else:
            entry_pool = None

        # If its new, create a new one in the database
        if entry_pool is None:

            # Process New Record
            entry_pool = EntryPools(**item)

            # Add To Table (after commit, id is filled in)
            session.add(entry_pool)

        # Otherwise, update the record with the new values and commit it
        else:

            # Set the new attributes
            for key, value in item.items():
                setattr(entry_pool, key, value)

        # Commit changes whichever way it went
        session.commit()


def load_drf_payoff_data_into_database(data, session, race):

    # Create base amount dict
    base_amount_dict = {}
    for wager in data['wagerTypes']:
        base_amount_dict[wager['wagerType'].strip()] = wager['baseAmount'].strip()

    # Loop through payoffs
    for payoff in data['payoffDTOs']:

        # Create Entry Dict
        item = dict()
        item['race_id'] = race.race_id
        item['wager_type'] = payoff['wagerType'].strip()
        item['wager_type_name'] = payoff['wagerName'].strip()
        item['winning_numbers'] = payoff['winningNumbers'].strip()
        item['number_of_tickets'] = payoff['numberOfTicketsBet']
        item['total_pool'] = payoff['totalPool']
        item['payoff_amount'] = payoff['payoffAmount']
        item['base_amount'] = base_amount_dict.get(payoff['wagerType'], 0)

        # Check for existing record
        payoff_record = session.query(Payoffs).filter(
            Payoffs.race_id == item['race_id'],
            Payoffs.wager_type == item['wager_type']
        ).first()

        # If its new, create a new one in the database
        if payoff_record is None:

            # Process New Record
            payoff_record = Payoffs(**item)

            # Add To Table (after commit, id is filled in)
            session.add(payoff_record)

        # Otherwise, update the record with the new values and commit it
        else:

            # Set the new attributes
            for key, value in item.items():
                setattr(payoff_record, key, value)

        # Commit changes whichever way it went
        session.commit()


def load_drf_probable_data_into_database(data, session, race, scrape_time):

    # Loop through payoffs
    for probable_type in data['wagerToteProbables']:
        for probable_dict in data['wagerToteProbables'][probable_type]:

            if not isinstance(probable_dict, dict):
                # print(f'{probable_dict} is almost certainly a will pay which we do not care about')
                continue

            # Create Entry Dict
            item = dict()
            item['race_id'] = race.race_id
            item['scrape_time'] = scrape_time
            item['probable_type'] = probable_dict['probType'].strip()
            item['program_numbers'] = probable_dict['progNum'].strip()
            item['probable_value'] = probable_dict['probValue']
            item['probable_pool_amount'] = probable_dict['poolAmount']

            # Check for existing record
            if 1==1:
                probable_record = session.query(Probables).filter(
                    Probables.race_id == item['race_id'],
                    Probables.probable_type == item['probable_type'],
                    Probables.program_numbers == item['program_numbers'],
                    Probables.scrape_time == item['scrape_time']
                ).first()
            else:
                probable_record = None

            # If its new, create a new one in the database
            if probable_record is None:

                # Process New Record
                probable_record = Probables(**item)

                # Add To Table (after commit, id is filled in)
                session.add(probable_record)

            # Otherwise, update the record with the new values and commit it
            else:

                # Set the new attributes
                for key, value in item.items():
                    setattr(probable_record, key, value)

            # Commit changes whichever way it went
            session.commit()


def load_drf_odds_data_into_database(data, scrape_time, session):

    # Race Info
    race = load_drf_race_data_into_database(data, scrape_time, session)
    if race is None:
        return

    # Probable Data
    load_drf_probable_data_into_database(data, session, race, scrape_time)

    # Parse Runner Data
    for runner in data['runners']:

        # Load Horse Data
        horse = load_drf_horse_data_into_database(runner, session)
        if horse is None:
            return

        # Load Entry Data
        entry = load_drf_entry_data_into_database(runner, session, horse, race, 0)
        if entry is None:
            return

        # Load Entry Pool Data
        load_drf_odds_entry_pool_data_into_database(
            runner,
            session,
            entry,
            scrape_time
        )

    # Close Session
    session.close()


def load_drf_results_data_into_database(data, scrape_time, session):

    # Race Info
    race = load_drf_race_data_into_database(data, scrape_time, session)
    if race is None:
        return

    # Payoff Info
    load_drf_payoff_data_into_database(data, session, race)

    # Parse Runner Data
    for runner in data['runners']:

        # Load Horse Data
        horse = load_drf_horse_data_into_database(runner, session)
        if horse is None:
            return

        # Load Entry Data
        entry = load_drf_entry_data_into_database(runner, session, horse, race, 0)
        if entry is None:
            return

    # Parse finish position out of also ran
    if isinstance(data['alsoRan'], list):
        order_of_finish = data['alsoRan']
    else:
        first_horses, last_horse = data['alsoRan'].split('  and   ')
        order_of_finish = first_horses.split(', ')
        order_of_finish.append(last_horse)
    for finish_index, horse_name in enumerate(order_of_finish):

        # Load Horse Data
        runner = {'horseName': horse_name.strip()}
        horse = load_drf_horse_data_into_database(runner, session)
        if horse is None:
            return

        # Load Entry Data
        entry = load_drf_entry_data_into_database(runner, session, horse, race, finish_index+4)
        if entry is None:
            return


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


def get_list_of_files(dir_name):

    # create a list of file and sub directories
    # names in the given directory
    list_of_files = os.listdir(dir_name)
    all_files = list()

    # Iterate over all the entries
    for entry in list_of_files:

        # Create full path
        full_path = os.path.join(dir_name, entry)

        # If entry is a directory then get the list of files in this directory
        if os.path.isdir(full_path):
            all_files = all_files + get_list_of_files(full_path)
        else:
            all_files.append(full_path)

    return all_files


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
        filter_by(results=False).\
        filter(Races.post_time <= datetime.datetime.utcnow()).all()

    # Organize in list
    race_list = []
    for race in races:

        # Convert to pacific time
        post_time_utc = utc.localize(race.post_time)
        post_time_pacific = post_time_utc.astimezone(timezone('US/Pacific'))

        # Append to list
        race_list.append({
            'post_time': post_time_pacific,
            'track_id': race.track_id,
            'country': race.country,
            'race_id': race.race_id
        })

    # Return Missing
    return race_list


if __name__ == '__main__':

    # Argument Parsing
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--mode',
                            help="Mode of operation (odds: store odds files)",
                            type=str,
                            required=True,
                            metavar='MODE'
                            )
    arg_parser.add_argument('--output_dir',
                            help="Base directory for storing json files",
                            type=str,
                            metavar='PATH'
                            )
    args = arg_parser.parse_args()

    # Check mode
    if args.mode in ('odds', 'drf', 'all'):

        # Check output directory
        base_data_dir = args.output_dir.strip()
        if base_data_dir == '' or not os.path.exists(base_data_dir):
            print(f'The output directory of "{base_data_dir}" is invalid!')
            exit(1)

        # Get currently running tracks
        track_data = get_current_drf_odds_track_list()

        if len(track_data) > 0:

            # Connect to the database
            engine = db_connect()
            create_drf_live_table(engine, False)
            session_maker_class = sessionmaker(bind=engine)
            db_session = session_maker_class()

            # Iterate through tracks
            for current_track in track_data:
                if current_track['country'] == 'USA':
                    race_data = get_single_track_data_from_drf(current_track)
                    save_single_track_drf_odds_data_to_file(race_data, base_data_dir)
                    current_scrape_time = datetime.datetime.fromisoformat(race_data['drf_scrape']['time_scrape_utc'])
                    load_drf_odds_data_into_database(race_data, current_scrape_time, db_session)

            # Close everything out
            db_session.close()
            engine.dispose()

    elif args.mode in ('results', 'drf', 'all'):

        # Check output directory
        base_data_dir = args.output_dir.strip()
        if base_data_dir == '' or not os.path.exists(base_data_dir):
            print(f'The output directory of "{base_data_dir}" is invalid!')
            exit(1)

        # Get yesterdays tracks
        yesterday = datetime.datetime.utcnow()+datetime.timedelta(days=-1)
        track_data = get_current_drf_results_track_list()

        # Loop if theres tracks
        if len(track_data['raceTracks']['allTracks']) > 0:

            # Connect to the database
            engine = db_connect()
            create_drf_live_table(engine, False)
            session_maker_class = sessionmaker(bind=engine)
            db_session = session_maker_class()

            for current_track in track_data['raceTracks']['allTracks']:
                for card in current_track['cards']:
                    race_card_date_int = int(card['raceDate']['date'])/1000.0
                    if race_card_date_int > 0:
                        card_date = datetime.datetime.utcfromtimestamp(race_card_date_int)
                        if card_date.date() == yesterday.date():
                            results_data = get_single_race_day_drf_results(
                                card_date,
                                current_track['trackId'],
                                current_track['country']
                            )
                            save_single_track_drf_results_data_to_file(results_data, base_data_dir)
                            current_scrape_time = datetime.datetime.fromisoformat(
                                results_data['drf_scrape']['time_scrape_utc']
                            )
                            for index, race_data in enumerate(results_data['races']):
                                race_data['postTimeLong'] = results_data['allRaces'][index]['postTime']
                                load_drf_results_data_into_database(race_data, current_scrape_time, db_session)

            # Close everything out
            db_session.close()
            engine.dispose()

    elif args.mode in ('missing', 'drf', 'all'):

        # Check output directory
        base_data_dir = args.output_dir.strip()
        if base_data_dir == '' or not os.path.exists(base_data_dir):
            print(f'The output directory of "{base_data_dir}" is invalid!')
            exit(1)

        # Connect to the database
        engine = db_connect()
        create_drf_live_table(engine, False)
        session_maker_class = sessionmaker(bind=engine)
        db_session = session_maker_class()

        # Get missing tracks
        missing_races = get_races_with_no_results(db_session)

        # Loop if theres races
        for current_race in missing_races:

            # Double check its still missing data
            race = db_session.query(Races).filter_by(race_id=current_race['race_id']).one()
            if race.results:
                continue

            # Get data
            results_data = get_single_race_day_drf_results(
                current_race['post_time'],
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
        db_session.close()
        engine.dispose()

    elif args.mode in ('files', 'all'):

        # Check output directory
        base_data_dir = args.output_dir.strip()
        if base_data_dir == '' or not os.path.exists(base_data_dir):
            print(f'The output directory of "{base_data_dir}" is invalid!')
            exit(1)

        # Connect to the database
        engine = db_connect()
        create_drf_live_table(engine, False)
        session_maker_class = sessionmaker(bind=engine)
        db_session = session_maker_class()

        # Get list of odds files to parse
        odds_file_list = sorted(get_all_drf_odds_json_filenames_from_storage(base_data_dir))
        wait_until_flag = ''
        # Load file into database
        for odds_file in odds_file_list:
            print(f'Working on {odds_file}')
            if wait_until_flag != '':
                if odds_file == wait_until_flag:
                    wait_until_flag = ''
                else:
                    continue
            odds_data = get_single_drf_odds_track_data_from_file(odds_file)
            current_scrape_time = datetime.datetime.fromisoformat(odds_data['drf_scrape']['time_scrape_utc'])
            load_drf_odds_data_into_database(odds_data, current_scrape_time, db_session)

        # Get list of results files to parse
        results_file_list = sorted(get_all_drf_results_json_filenames_from_storage(base_data_dir))

        # Load file into database
        for results_file in results_file_list:
            print(f'Working on {results_file}')
            results_data = get_single_drf_results_track_data_from_file(results_file)
            current_scrape_time = datetime.datetime.fromisoformat(results_data['drf_scrape']['time_scrape_utc'])
            for index, race_data in enumerate(results_data['races']):
                race_data['postTimeLong'] = results_data['allRaces'][index]['postTime']
                load_drf_results_data_into_database(race_data, current_scrape_time, db_session)

        # Close everything out
        db_session.close()
        engine.dispose()

    else:

        print(f'"{args.mode}" is not a valid operational mode!')
        exit(1)
