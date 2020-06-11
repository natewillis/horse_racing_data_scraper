from models import Tracks
from bs4 import BeautifulSoup
import datetime
import re
from utils import get_horse_origin_from_name

def get_equibase_horse_history_link_from_params(equibase_horse_id, equibase_horse_registry):

    return f'http://www.equibase.com/profiles/Results.cfm?type=Horse&' \
           f'refno={equibase_horse_id}&registry={equibase_horse_registry}'


def get_equibase_horse_history_link_from_horse(horse):

    return get_equibase_horse_history_link_from_params(horse.equibase_horse_id, horse.equibase_horse_registry)


def get_equibase_result_url_from_params(code, card_date, country, race_number):

    # Format date object
    eb_date = card_date.strftime('%m%d%y')

    # Return url
    return f'https://www.equibase.com/static/chart/summary/{code}{eb_date}{country}{race_number}-EQB.html'


def get_equibase_result_url_from_race(session, race):

    # Get associated track
    track = session.query(Tracks).filter(Tracks.track_id == race.track_id).first()

    # Call function to assemble url
    return get_equibase_result_url_from_params(track.code, race.card_date, track.country, race.race_number)


def get_equibase_entry_url_from_params(code, card_date, country, race_number):

    # Format date object
    eb_date = card_date.strftime('%m%d%y')

    # Return url
    return f'https://www.equibase.com/static/entry/{code}{eb_date}{country}{race_number}-EQB.html'


def get_equibase_entry_url_from_race(session, race):

    # Get associated track
    track = session.query(Tracks).filter(Tracks.track_id == race.track_id).first()

    # Call function to assemble url
    return get_equibase_entry_url_from_params(track.code, race.card_date, track.country, race.race_number)


def get_equibase_whole_card_entry_url_from_params(code, card_date, country):

    # Format date object
    eb_date = card_date.strftime('%m%d%y')

    # Return url
    return f'https://www.equibase.com/static/entry/{code}{eb_date}{country}-EQB.html'


def get_equibase_whole_card_entry_url_from_race(session, race):

    # Get associated track
    track = session.query(Tracks).filter(Tracks.track_id == race.track_id).first()

    # Call function to assemble url
    return get_equibase_whole_card_entry_url_from_params(track.code, race.card_date, track.country)


def get_db_items_from_equibase_whole_card_entry_html(html):

    # Initialize horse items
    return_list = []

    # Check for blank html
    if html == '':
        print('Blank html means the scrape must have failed')
        return return_list

    # Parse html
    soup = BeautifulSoup(html, 'html.parser')

    # Find Track Header
    title_h2 = soup.select_one('h2.track-info.center')
    if not title_h2:
        return return_list

    # Extract track code
    track_name_a = title_h2.select_one('a.track-name')
    if track_name_a:
        track_url = track_name_a['href']
    else:
        return return_list

    # Regex to get track code
    track_url_pattern = r'/profiles/Results\.cfm\?type=Track&trk=([A-Z]+)&cy=([A-Z]+)'
    track_url_search_obj = re.search(track_url_pattern, track_url)
    if track_url_search_obj:
        track_code = track_url_search_obj.group(1)
    else:
        return return_list

    # Extract Race Date
    race_date_div = title_h2.find('div', {'class': ['race-date']})
    if race_date_div:
        card_date = datetime.datetime.strptime(race_date_div.text.strip(), '%B %d, %Y').date()
    else:
        return return_list

    # Get each race div
    race_entries_divs = soup.select('div.c-entries-data')
    if not race_entries_divs:
        return return_list

    for race_entries_div in race_entries_divs:

        # Initialize single return dict for race
        return_dict = {
            'track_item': {
                'code': track_code
            },
            'race_item': None,
            'entry_items': []
        }

        # Extract Race Number
        race_number = -1
        race_number_spans = race_entries_div.select('span.whitetxt.allcaps')
        for race_number_span in race_number_spans:
            race_number_pattern = r'Race (\d+) -'
            race_number_search_obj = re.search(race_number_pattern, race_number_span.text)
            if race_number_search_obj:
                race_number = int(race_number_search_obj.group(1).strip())
                break
        if race_number <= 0:
            continue

        # Create race item
        return_dict['race_item'] = {
            'card_date': card_date,
            'race_number': race_number,
            'track_id': 0,
            'equibase_entries': True
        }

        # Entry Table
        entry_table = race_entries_div.select_one('table')
        if not entry_table:
            continue
        entry_table_body = entry_table.select_one('tbody')
        if not entry_table_body:
            continue

        # Iterate through the entries
        for entry_tr in entry_table_body.findAll('tr'):

            # Init Entry Dictionary
            entry_item = {
                'horse_item': None,
                'jockey_item': None,
                'owner_item': None,
                'trainer_item': None
            }

            # Check for scratch
            scratch_flag = False
            if entry_tr.has_attr('class'):
                if entry_tr['class'][0] == 'scratch':
                    scratch_flag = True

            # Break up cells
            entry_tds = entry_tr.findAll('td')
            if len(entry_tds) < 9 and not scratch_flag:
                print('not enough tds for non scratch')
                print(entry_tr)
                continue
            elif len(entry_tds) < 6 and scratch_flag:
                print('not enough tds for non scratch')
                print(entry_tr)
                continue

            # Get horse details
            if scratch_flag:
                horse_name_td = entry_tds[1]
            else:
                horse_name_td = entry_tds[2]
            horse_name_a = horse_name_td.find('a')
            if horse_name_a:

                # Horse name
                horse_name, horse_country, horse_state = get_horse_origin_from_name(horse_name_a.text.strip().upper())

                # Get equibase identifiers
                horse_link = horse_name_a.get('href').replace('®', '&reg')
                horse_link_pattern = r'type=Horse&refno=(\d+)&registry=([A-Za-z0-9]+)&rbt=([A-Za-z0-9]+)'
                horse_link_match_obj = re.search(horse_link_pattern, horse_link)
                if horse_link_match_obj:
                    equibase_id = int(horse_link_match_obj.group(1))
                    equibase_type = horse_link_match_obj.group(3).strip().upper()
                    equibase_registry = horse_link_match_obj.group(2).strip().upper()

                    # store horse object to write
                    entry_item['horse_item'] = {
                        'horse_name': horse_name,
                        'horse_country': horse_country,
                        'horse_state': horse_state,
                        'equibase_horse_id': equibase_id,
                        'equibase_horse_type': equibase_type,
                        'equibase_horse_registry': equibase_registry
                    }

                else:
                    print('no horse link')
                    continue

            if not scratch_flag:
                # Get jockey details
                jockey_td = entry_tds[7]
                jockey_name_a = jockey_td.find('a')
                if jockey_name_a:
                    # Jockey name
                    jockey_name = jockey_name_a.text.strip().upper()
                    jockey_name_pattern = r'([A-Z]) ([A-Z ]) ([A-Z\'\-]+)(, [A-Z0-9\.\-]+)?'
                    jockey_name_search_obj = re.search(jockey_name_pattern, jockey_name)
                    if jockey_name_search_obj:
                        jockey_first_initial = jockey_name_search_obj.group(1)
                        jockey_last_name = jockey_name_search_obj.group(3)
                        if jockey_name_search_obj.group(4) is not None:
                            jockey_last_name += jockey_name_search_obj.group(4)
                    else:
                        continue

                    # Get equibase identifiers
                    jockey_link = jockey_name_a.get('href').replace('®', '&reg')
                    jockey_link_pattern = r'type=People&searchType=J&eID=(\d+)&rbt=([A-Za-z0-9]+)'
                    jockey_link_match_obj = re.search(jockey_link_pattern, jockey_link)
                    if jockey_link_match_obj:
                        equibase_id = int(jockey_link_match_obj.group(1))
                        equibase_type = jockey_link_match_obj.group(2).strip().upper()

                        # store horse object to write
                        entry_item['jockey_item'] = {
                            'first_name': jockey_first_initial,
                            'last_name': jockey_last_name,
                            'equibase_jockey_type': equibase_type,
                            'equibase_jockey_id': equibase_id
                        }

                    else:
                        continue

                # Get trainer details
                trainer_td = entry_tds[9]
                trainer_name_a = trainer_td.find('a')
                if trainer_name_a:

                    # trainer name
                    trainer_name = trainer_name_a.text.strip().upper()
                    trainer_name_pattern = r'([A-Z]) ([A-Z ]) ([A-Z\'\-]+)(, [A-Z0-9\.\-]+)?'
                    trainer_name_search_obj = re.search(trainer_name_pattern, trainer_name)
                    if trainer_name_search_obj:
                        trainer_first_initial = trainer_name_search_obj.group(1)
                        trainer_last_name = trainer_name_search_obj.group(3)
                        if trainer_name_search_obj.group(4) is not None:
                            trainer_last_name += trainer_name_search_obj.group(4)
                    else:
                        continue

                    # Get equibase identifiers
                    trainer_link = trainer_name_a.get('href').replace('®', '&reg')
                    trainer_link_pattern = r'type=People&searchType=T&eID=(\d+)&rbt=([A-Za-z0-9]+)'
                    trainer_link_match_obj = re.search(trainer_link_pattern, trainer_link)
                    if trainer_link_match_obj:
                        equibase_id = int(trainer_link_match_obj.group(1))
                        equibase_type = trainer_link_match_obj.group(2).strip().upper()

                        # store horse object to write
                        entry_item['trainer_item'] = {
                            'first_name': trainer_first_initial,
                            'last_name': trainer_last_name,
                            'equibase_trainer_type': equibase_type,
                            'equibase_trainer_id': equibase_id
                        }

                    else:
                        continue

            # Append to horse items
            return_dict['entry_items'].append(entry_item)

        # Add the whole race to the list
        return_list.append(return_dict)

    return return_list


def get_db_items_from_equibase_horse_html(html):


    # Initialize horse items
    return_dict = {
        'horse_item': None,
        'entry_items': [],
        'workout_items': []
    }

    # Check for blank html
    if html == '':
        print('Blank html means the scrape must have failed')
        return return_dict

    # Parse html
    soup = BeautifulSoup(html, 'html.parser')

    # Find horse name
    horse_name_h2 = soup.find('h2', {'class': ['clear horse-name-header']})
    if horse_name_h2 is None:
        print('something went wrong with the horse info scrape')
        return return_dict
    horse_name, horse_country, horse_state = get_horse_origin_from_name(horse_name_h2.text.strip().upper())

    # Find Horse Profile
    horse_profile_h5 = soup.find('h5', {'class': ['horse-profile-top-bar-headings']})
    horse_profile_string = horse_profile_h5.text.strip().upper()
    horse_profile_pattern = r'([A-Z]+), ([A-Z \/]+), ([A-Z]+), FOALED ([A-Z]+ \d+, \d{4})'
    horse_profile_search_obj = re.search(horse_profile_pattern, horse_profile_string)
    if horse_profile_search_obj:
        return_dict['horse_item'] = {
            'horse_type': horse_profile_search_obj.group(1).strip(),
            'horse_color': horse_profile_search_obj.group(2).strip(),
            'horse_gender': horse_profile_search_obj.group(3).strip(),
            'horse_birthday': datetime.datetime.strptime(horse_profile_search_obj.group(4).strip(), '%B %d, %Y'),
            'horse_name': horse_name,
            'horse_country': horse_country,
            'horse_state': horse_state,
            'equibase_horse_detail_scrape_date': datetime.datetime.utcnow()
        }
    else:
        return_dict['horse_item'] = {
            'horse_name': horse_name,
            'horse_country': horse_country,
            'horse_state': horse_state,
            'equibase_horse_detail_scrape_date': datetime.datetime.utcnow()
        }

    # Find Results Table
    results_table = soup.find('table', {'class': ['phone-collapse results']})
    if not results_table:
        return return_dict

    # Get the body
    results_table_body = results_table.find('tbody')
    if not results_table_body:
        return return_dict

    # For each result create an item
    for result_tr in results_table_body.findAll('tr'):

        # Get track
        track_td = result_tr.select_one('td.track')
        if not track_td:
            continue
        track_href = track_td.find('a')
        if not track_href:
            continue
        track_url = track_href['href']
        track_url_pattern = r'/profiles/Results\.cfm\?type=Track&trk=([A-Z]+)&cy=([A-Z]+)'
        track_url_search_obj = re.search(track_url_pattern, track_url)
        if track_url_search_obj:
            track_code = track_url_search_obj.group(1)
        else:
            continue

        # Get race card date
        race_date_td = result_tr.find('td', {'class': ['date']})
        if not race_date_td:
            continue
        card_date = datetime.datetime.strptime(race_date_td.text.strip(), '%m/%d/%Y').date()

        # Get race number
        race_number_td = result_tr.find('td', {'class': ['race']})
        if not race_number_td:
            continue
        if race_number_td.text.strip().isnumeric():
            race_number = int(race_number_td.text.strip())
        else:
            continue

        # Get race type
        race_type_td = result_tr.find('td', {'class': ['type']})
        if not race_type_td:
            continue
        race_type = race_type_td.text.strip().upper()

        # Get speed figure
        speed_figure_td = result_tr.find('td', {'class': ['speedFigure']})
        if not speed_figure_td:
            continue
        if speed_figure_td.text.strip().isnumeric():
            speed_figure = int(speed_figure_td.text.strip())
        else:
            speed_figure = 999

        # Get finish position
        finish_td = result_tr.find('td', {'class': ['finish']})
        if not finish_td:
            continue
        if finish_td.text.strip().isnumeric():
            finish_pos = int(finish_td.text.strip())
        else:
            finish_pos = 999

        # Create entry objects
        return_dict['entry_items'].append({
            'track_item': {
                'code': track_code
            },
            'race_item': {
                'race_number': race_number,
                'card_date': card_date,
                'race_type': race_type,
                'equibase_horse_results': True
            },
            'entry_item': {
                'finish_position': finish_pos,
                'equibase_speed_figure': speed_figure,
                'equibase_history_scrape': True,
                'scratch_indicator': 'N'
            }
        })

    # Find Workout Table
    workouts_table = soup.find('table', {'class': ['phone-collapse workouts']})
    if not workouts_table:
        return return_dict

    # Get the body
    workouts_table_body = workouts_table.find('tbody')
    if not workouts_table_body:
        return return_dict

    # For each result create an item
    for workout_tr in workouts_table_body.findAll('tr'):

        # Get track
        track_td = workout_tr.find('td', {'class': ['track']})
        if not track_td:
            continue
        track_href = track_td.find('a')
        if not track_href:
            continue
        track_url = track_href['href']
        track_url_pattern = r'/profiles/Results\.cfm\?type=Track&trk=([A-Z]+)&cy=([A-Z]+)'
        track_url_search_obj = re.search(track_url_pattern, track_url)
        if track_url_search_obj:
            track_code = track_url_search_obj.group(1)
        else:
            continue

        # Track Name
        track_name = track_td.text.strip().upper()

        # Get Date
        workout_date_td = workout_tr.find('td', {'class': ['date']})
        if not workout_date_td:
            continue
        workout_date = datetime.datetime.strptime(workout_date_td.text.strip(), '%m/%d/%Y').date()

        # Get Course
        course_td = workout_tr.find('td', {'class': ['course']})
        if not course_td:
            continue
        workout_course = course_td.text.strip().upper()

        # Get Distance
        distance_td = workout_tr.find('td', {'class': ['distance']})
        if not distance_td:
            continue
        workout_distance_string = distance_td.text.strip().upper()[:-1]
        if workout_distance_string.isnumeric():
            workout_distance = float(workout_distance_string)
        else:
            continue

        # Get Time
        time_td = workout_tr.find('td', {'class': ['time']})
        if not time_td:
            continue
        workout_time_string = time_td.text.strip()
        workout_time_pattern = r'((\d+):)?(\d+)\.(\d+)'
        workout_time_search_obj = re.search(workout_time_pattern, workout_time_string)
        if workout_time_search_obj:
            workout_time = float(workout_time_search_obj.group(3))+float(workout_time_search_obj.group(4))/100
            if workout_time_search_obj.group(2) is not None:
                workout_time += float(workout_time_search_obj.group(2)) * 60.0
        else:
            continue

        # Note
        note_td = workout_tr.find('td', {'class': ['note']})
        if not note_td:
            continue
        note = note_td.text.strip().upper()

        # Rank
        rank_td = workout_tr.find('td', {'class': ['rank']})
        if not rank_td:
            continue
        rank_td_string = rank_td.text.upper().strip()
        ranks = rank_td_string.split('/')
        if len(ranks) != 2:
            continue
        if not ranks[0].isnumeric():
            continue
        if not ranks[1].isnumeric():
            continue
        workout_rank = int(ranks[0])
        workout_total = int(ranks[1])

        # Create Item
        return_dict['workout_items'].append({
            'track_item': {
                'code': track_code,
                'name': track_name
            },
            'workout_item': {
                'workout_date': workout_date,
                'course': workout_course,
                'distance': workout_distance,
                'time_seconds': workout_time,
                'note': note,
                'workout_rank': workout_rank,
                'workout_total': workout_total
            }
        })

    return return_dict


def equibase_entries_link_getter(html):

    # Link List
    link_list = []

    # Check for blank html
    if html == '':
        print('Blank html means the scrape must have failed')
        return link_list

    # Parse html
    soup = BeautifulSoup(html, 'html.parser')

    # Find links
    link_as = soup.findAll('a', href= re.compile(r'/static/entry/.*[A-Z]{2}\d{6}'))

    # process links
    for link_a in link_as:

        # Get URL
        href = link_a['href']

        # Check for calendar links
        if 'calendar' in href:
            continue

        # Remove race card index if necessary
        href = href.replace('RaceCardIndex', '')

        # Append to link list
        link_list.append(f'http://www.equibase.com/{href}')

    # Return link list
    return link_list

