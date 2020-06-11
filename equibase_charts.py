import pdfquery
import re
import datetime
from pdfminer.layout import LTChar, LTTextLineHorizontal, LTAnno
from utils import convert_equibase_chart_distance_string_to_furlongs, get_horse_origin_from_name, lb_text_to_float
import math
import json
from pprint import pprint
from models import Tracks
import os

def get_equibase_embedded_chart_link_from_params(track_code, card_date, track_country):

    # Format date object
    eb_date = card_date.strftime('%m/%d/%Y')

    return f'https://www.equibase.com/premium/chartEmb.cfm?track={track_code}&raceDate={eb_date}&cy={track_country}'


def get_equibase_embedded_chart_link_from_race(session, race):

    # Get associated track
    track = session.query(Tracks).filter(Tracks.track_id == race.track_id).first()

    # Call function to assemble url
    return get_equibase_embedded_chart_link_from_params(track.code, race.card_date, track.country)


def whole_line_selector_string(y0, y1):

    return f'LTTextLineHorizontal:overlaps_bbox' \
                      f'("{0:.3f}, ' \
                      f'{y0:.3f}, ' \
                      f'{612:.3f}, ' \
                      f'{y1:.3f}")'


def get_stats_from_character_list(character_list):

    if len(character_list) == 0:
        return {
            'min_y0': 0,
            'max_y0': 0,
            'min_height': 0,
            'max_height': 0
        }
    else:
        return {
            'min_y0': min([item['y0'] for item in character_list]),
            'max_y0': max([item['y0'] for item in character_list]),
            'min_height': min([item['height'] for item in character_list]),
            'max_height': max([item['height'] for item in character_list])
        }


def parse_line_items_based_on_header_list(pdf_items, header_list):

    # define variables
    line_dict = dict()
    for header_item in header_list:
        line_dict[header_item['name']] = {
            'main_text': '',
            'super_text': '',
            'whole_text': ''
        }

    # parse pdf items to sorted list
    sorted_character_list = get_sorted_character_list_from_lt_text_line_horizontal(pdf_items)

    # get stats
    list_stats = get_stats_from_character_list(sorted_character_list)

    if len(sorted_character_list) == 0:
        return None, list_stats

    # iterate through characters
    for item in sorted_character_list:
        for header_item in header_list:
            if (header_item['start_x'] - 0.5) <= item['x0'] < (header_item['end_x'] - 0.5):

                # Add the character where it belongs
                line_dict[header_item['name']]['whole_text'] += item['text']
                if item['y0'] > list_stats['min_y0'] and item['height'] < list_stats['max_height']:
                    line_dict[header_item['name']]['super_text'] += item['text']
                else:
                    line_dict[header_item['name']]['main_text'] += item['text']

                # Stop searching, we found it
                break

    # Return parsed line
    return line_dict, list_stats


def get_sorted_character_list_from_lt_text_line_horizontal(pdf_items):

    # Define Variables
    character_list = []

    # Iterate the line
    for text_line_item in pdf_items:
        for character_item in text_line_item.layout:
            if isinstance(character_item, LTChar):
                character_list.append({
                    'x0': character_item.x0,
                    'width': character_item.width,
                    'text': character_item._text,
                    'height': character_item.height,
                    'y0': character_item.y0,
                    'y1': character_item.y1,
                })
            elif isinstance(character_item, LTAnno):
                if len(character_list) > 0:
                    if character_item._text == ' ':
                        character_list[-1]['text'] += ' '

    # Sort Column List
    sorted_character_list = sorted(character_list, key=lambda x: float(x['x0']))

    # Return finished list
    return sorted_character_list


def parse_starter_header_line(pdf_items):

    # Define Variables
    column_list = []
    column_div_width = 2.5

    # Get sorted list
    character_list = get_sorted_character_list_from_lt_text_line_horizontal(pdf_items)

    # Setup loop of characters
    current_column_text = ''
    last_character_x1 = 0
    current_column_x0 = 0
    for character_item in character_list:

        # Store new column start
        if current_column_text == '':
            last_character_x1 = character_item['x0']

        # Check for division
        if (character_item['x0'] - last_character_x1) > column_div_width or character_item['text'] == 'M':
            column_list.append({
                'start_x': current_column_x0,
                'end_x': character_item['x0'],
                'name': current_column_text.strip()
            })
            current_column_x0 = character_item['x0']
            current_column_text = ''

        # Store the new character and move on
        current_column_text += character_item['text']
        last_character_x1 = character_item['x0'] + character_item['width']

    # Add the last column manually
    if current_column_text != '':
        column_list.append({
            'start_x': current_column_x0,
            'end_x': 612,
            'name': current_column_text
        })

    # Return assembled dictionary
    return column_list


def process_race_string(race_string):

    # Setup Variables
    return_race_dict = {}

    # Split the string
    split_race_string = race_string.split(' - ')
    if len(split_race_string) != 3:
        return

    # Track name
    track_name = split_race_string[0].strip()
    reg_pattern = re.compile(r'[^a-zA-Z ]')
    return_race_dict['track_name'] = reg_pattern.sub('', track_name).strip().upper()

    # Race Date
    race_date_string = split_race_string[1]
    return_race_dict['race_date'] = datetime.datetime.strptime(race_date_string, '%B %d, %Y').date()

    # Race Number
    race_number_string = split_race_string[2]
    race_number_split = race_number_string.split('Race ')
    return_race_dict['race_number'] = int(race_number_split[1].strip())

    # Return dictionary
    return return_race_dict


def get_whole_horizontal_line_text_from_contains(page, contains_text):

    # Search page for contains text
    contains_text_object = page(f'LTTextLineHorizontal:contains("{contains_text}")')

    # Check for existence
    if contains_text_object:

        # Get bbox
        y0 = float(contains_text_object.attr('y0'))
        y1 = float(contains_text_object.attr('y1'))

        # grab whole line
        pdf_items = page(whole_line_selector_string(y0, y1))

        return pdf_items.text()

    else:

        return ''


def get_race_type_breed_from_race_page(page, y0):

    # Define best y0 and y1
    actual_y0 = y0 + 7/2 - 1
    actual_y1 = actual_y0 + 2

    # Perform selection
    race_type_pdf_items = page(whole_line_selector_string(actual_y0, actual_y1))

    # Get text
    if race_type_pdf_items:
        race_type_line_text = race_type_pdf_items.text()
        race_type = race_type_line_text.split(' - ')[0].strip().upper()
        race_type_class_words = race_type.split(' ')
        race_class_words = []
        for word in race_type_class_words:
            if word in ['MAIDEN', 'CLAIMING', '1', '2', '3', 'SPECIAL', 'WEIGHT', 'ALLOWANCE', 'STAKES', 'GRADE', 'OPTIONAL', 'STARTER']:
                race_class_words.append(word)
        race_class = ' '.join(race_class_words)

        breed = race_type_line_text.split(' - ')[-1].strip()

        if breed == 'Quarter Horse':
            breed = 'Quarterhorse'

        # Return it
        return race_type, race_class, breed
    else:
        return None, None, None


def get_distance_surface_from_race_page(page):

    # Get the whole line
    distance_whole_line = get_whole_horizontal_line_text_from_contains(page, 'Track Record:')

    # Split the record off
    distance_surface_string = distance_whole_line.split('Track Record:')[0]

    # Split the distance and track
    split_distance_surface_string = distance_surface_string.split(' On The ')

    # Get the base strings
    if len(split_distance_surface_string) == 2:
        surface = split_distance_surface_string[1]
        distance_string = split_distance_surface_string[0].upper()
    else:
        surface = None
        distance_string = ''

    # Perform distance conversion
    distance_furlongs = convert_equibase_chart_distance_string_to_furlongs(distance_string)

    # Return Value
    return distance_furlongs, surface


def get_purse_from_race_page(page):

    # Get the whole line
    purse_whole_line = get_whole_horizontal_line_text_from_contains(page, 'Purse: $')

    if purse_whole_line != '':
        purse_string = purse_whole_line.replace('Purse: $', '').replace(',', '').strip()
        if ' ' in purse_string:
            purse_string = purse_string.split(' ')[0]
        purse_value = float(purse_string)

        return purse_value

    else:

        return None


def get_claiming_price_from_race_page(page):

    # Get the whole line
    claiming_price_whole_line = get_whole_horizontal_line_text_from_contains(page, 'Price: $')

    if claiming_price_whole_line != '':

        # Process claiming price
        claiming_price_string = claiming_price_whole_line.split('Price: $')[1].replace(',', '').replace('$', '')

        # Check for min/max
        if ' - ' in claiming_price_string:
            claiming_price_split = claiming_price_string.split(' - ')
            if not claiming_price_split[0].strip().isnumeric() or not claiming_price_split[1].strip().isnumeric():
                return None, None
            else:
                max_claiming_price = float(claiming_price_split[0].strip())
                min_claiming_price = float(claiming_price_split[1].strip())
        else:
            if not claiming_price_string.strip().isnumeric():
                return None, None
            else:
                max_claiming_price = float(claiming_price_string.strip())
                min_claiming_price = max_claiming_price

        return min_claiming_price, max_claiming_price

    else:

        return None, None


def get_track_condition_weather_from_race_page(page):

    # Get the whole line
    track_condition_weather_whole_line = get_whole_horizontal_line_text_from_contains(page, 'Weather: ')

    if track_condition_weather_whole_line != '':

        track_condition_pattern = re.compile(r'Weather: (.*)Track: (.*)')
        match_object = re.search(track_condition_pattern, track_condition_weather_whole_line)
        if match_object:
            weather = match_object.group(1).strip()
            track_condition = match_object.group(2).replace('Video Race Replay', '').strip()
            return track_condition, weather
        else:
            return None, None

    else:

        return None, None


def get_fractional_times_from_race_page(page, distance_feet, fractional_time_definition_list):

    # Init variables
    fractional_times = []

    # Figure out which fractional time object we need
    fractional_time_definition = next(
        (x for x in fractional_time_definition_list if abs(x['floor'] - distance_feet) < 10),
        None
    )
    if fractional_time_definition is None:
        return fractional_times

    # Get the whole line
    fractional_times_whole_line = get_whole_horizontal_line_text_from_contains(page, 'Fractional Times: ')

    if fractional_times_whole_line != '':

        track_condition_pattern = re.compile(r'(\d+:)?(\d+\.\d+)')
        match_list = re.findall(track_condition_pattern, fractional_times_whole_line)
        for index, fractional_match in enumerate(match_list):

            # Parse Minutes
            if fractional_match[0] == '':
                minutes = 0
            else:
                minutes = float(fractional_match[0][:-1])

            # Parse Seconds
            seconds = float(fractional_match[1])

            # Create total
            total_seconds = round((minutes * 60) + seconds, 2)

            # Find which point of call this is
            if len(match_list) == len(fractional_time_definition['fractionals']) + 1:
                if index == (len(fractional_time_definition['fractionals']) - 1):
                    continue
                elif index == len(fractional_time_definition['fractionals']):
                    fractional = fractional_time_definition['fractionals'][index-1]
                else:
                    fractional = fractional_time_definition['fractionals'][index]
            elif len(match_list) == len(fractional_time_definition['fractionals']):
                fractional = fractional_time_definition['fractionals'][index]
            else:
                return []

            # Append item
            fractional_times.append({
                'time': total_seconds,
                'point': fractional['point'],
                'text': fractional['text'],
                'distance': round(fractional['feet']/660, 4)
            })

        return fractional_times

    else:

        return fractional_times


def get_starter_data_from_race_page(page):

    # Init variables
    starter_data = []

    # starter parsing - find header
    starter_header = page('LTTextLineHorizontal:contains("Last Raced")')
    fractional_times_label = page('LTTextLineHorizontal:contains("Fractional Times")')
    if len(fractional_times_label) == 0:
        fractional_times_label = page('LTTextLineHorizontal:contains("Run-Up")')
        if len(fractional_times_label) == 0:
            return starter_data
        else:
            add_on_min_y0 = 0
    else:
        add_on_min_y0 = 9


    # grab y coordinates of the header row we found
    current_y0 = float(starter_header.attr('y0')) + float(starter_header.attr('height')) / 2 - 1
    current_y1 = current_y0 + 2

    # create selector string to return the whole row
    selector_string = whole_line_selector_string(current_y0, current_y1)

    # grab data for whole header from pdf
    header_pdf_items = page(selector_string)

    # parse header for x locations of all columns
    header_column_list = parse_starter_header_line(header_pdf_items)

    # parse starters
    current_y0 = float(starter_header.attr('y0')) - 11.392 + 7 / 2 - 1
    current_y1 = current_y0 + 2

    # figure out where to stop
    min_y0 = float(fractional_times_label.attr('y1')) + add_on_min_y0

    while current_y0 > min_y0:
        # get starter line pdf items
        selector_string = whole_line_selector_string(current_y0, current_y1)
        starter_line_items = page(selector_string)

        # parse items to dictionary
        starter_dict, line_stats = parse_line_items_based_on_header_list(starter_line_items, header_column_list)

        # Append to return dict
        starter_data.append(starter_dict)

        # Increment current y0 to the next value
        current_y0 = line_stats['min_y0'] - 10.306 + line_stats['max_height'] / 2 - 1
        current_y1 = current_y0 + 2

    return starter_data


def get_pp_data_from_race_page(page, next_page):

    # Init variables
    pp_data = []

    # starter parsing - find header
    pp_header = page('LTTextLineHorizontal:contains("Horse Name")').eq(1)
    trainer_label = page('LTTextLineHorizontal:contains("Trainers")')
    next_page_flag = False
    if len(trainer_label) == 0:
        if next_page is not None:
            trainer_label = next_page('LTTextLineHorizontal:contains("Trainers")')
            next_page_flag = True
            if len(trainer_label) == 0:
                return pp_data
        else:
            return pp_data


    # grab y coordinates of the header row we found
    current_y0 = float(pp_header.attr('y0')) + float(pp_header.attr('height')) / 2 - 1
    current_y1 = current_y0 + 2

    # create selector string to return the whole row
    selector_string = whole_line_selector_string(current_y0, current_y1)

    # grab data for whole header from pdf
    header_pdf_items = page(selector_string)

    # parse header for x locations of all columns
    header_column_list = parse_starter_header_line(header_pdf_items)

    # parse starters
    current_y0 = float(pp_header.attr('y0')) - 11.392 + 7 / 2 - 1
    current_y1 = current_y0 + 2

    # figure out where to stop
    if next_page_flag:
        min_y0 = 0
    else:
        min_y0 = float(trainer_label.attr('y1')) + 13

    # Setup loop
    current_page = page
    while current_y0 > min_y0:
        # get starter line pdf items
        selector_string = whole_line_selector_string(current_y0, current_y1)
        starter_line_items = current_page(selector_string)

        # Check if theres a blank line
        if len(starter_line_items) > 0:

            # parse items to dictionary
            pp_dict, line_stats = parse_line_items_based_on_header_list(starter_line_items, header_column_list)

            # Append to return dict
            pp_data.append(pp_dict)

        # Increment current y0 to the next value
        last_y0 = current_y0
        current_y0 = line_stats['min_y0'] - 10.306 + line_stats['max_height'] / 2 - 1

        # Fix bottom of page issues
        if current_y0 >= last_y0:
            current_y0 = last_y0 - 10.306 + line_stats['max_height'] / 2 - 1

        # y1 is based off of y2
        current_y1 = current_y0 + 2

        if next_page_flag and current_y0 < 0:
            min_y0 = float(trainer_label.attr('y1')) + 13
            current_page = next_page
            current_y0 = 760
            current_y1 = 764

    return pp_data


def parse_horse_name_string_jockey_from_starter_text(starter_text):

    # define search pattern
    search_pattern = re.compile(r'(.*(\(\w+\) )?)\((.*)\)')
    match_object = re.match(search_pattern, starter_text)
    if match_object:

        # Split horse vs jockey
        horse_name_string = match_object.group(1).strip().upper()
        jockey_name_string = match_object.group(3).strip().upper()

        # horse name parsing
        horse_name, country, state = get_horse_origin_from_name(horse_name_string)

        # jockey parsing
        jockey_words = jockey_name_string.split(', ')
        jockey_last_name = ', '.join(jockey_words[:-1])
        jockey_first_name = jockey_words[-1]

        # return
        return horse_name, country, state, jockey_first_name, jockey_last_name

    else:

        return None, None, None, None, None


def convert_equibase_result_chart_pdf_to_item(pdf_filename):

    # logging
    print(f'processing {pdf_filename}')

    # setup script dir
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Init Return List
    data_list = []

    # Load auxilary data
    with open(os.path.join(script_dir, 'resources', 'fractional-times.json'), 'r') as fractional_time_file:
        fractional_time_definition = json.load(fractional_time_file)
    with open(os.path.join(script_dir, 'resources', 'points-of-call.json'), 'r') as points_of_call_file:
        points_of_call_definition = json.load(points_of_call_file)

    # Load pdf chart
    pdf = pdfquery.PDFQuery(pdf_filename)
    pdf.load()

    # stats
    number_pages = pdf.doc.catalog['Pages'].resolve()['Count']

    # Loop through races
    for race_string_object in pdf.pq('LTTextLineHorizontal:contains(" - Race ")'):

        # Process Race String
        race_string_dict = process_race_string(race_string_object.text)
        if not race_string_dict:
            continue

        # Race Page
        race_page_number = next(race_string_object.iterancestors('LTPage')).layout.pageid
        race_page = pdf.pq(f'LTPage[pageid="{race_page_number}"]')
        if race_page_number < number_pages:
            next_race_page = pdf.pq(f'LTPage[pageid="{race_page_number + 1}"]')
        else:
            next_race_page = None


        # Get race type
        race_type, race_class, breed = get_race_type_breed_from_race_page(race_page, float(race_string_object.layout.y0) - 9)

        # Get Race distance
        distance, surface = get_distance_surface_from_race_page(race_page)
        distance_feet = math.floor(distance * 660.0)

        # Get Race Purse
        purse = get_purse_from_race_page(race_page)

        # Get Claiming Price
        min_claiming_price, max_claiming_price = get_claiming_price_from_race_page(race_page)

        # Get Track Condition and weather
        track_condition, weather = get_track_condition_weather_from_race_page(race_page)

        # Get Fractional and final times
        fractional_times = get_fractional_times_from_race_page(race_page, distance_feet, fractional_time_definition)

        # Get starter data
        starter_data = get_starter_data_from_race_page(race_page)

        # past performance data
        pp_data = get_pp_data_from_race_page(race_page, next_race_page)

        #TODO: Trainer data

        # Initialize single return dict for race
        data_item = {
            'track_item': {
                'equibase_chart_name': race_string_dict['track_name']
            },
            'race_item': {
                'race_number': race_string_dict['race_number'],
                'card_date': race_string_dict['race_date'],
                'distance': distance,
                'purse': purse,
                'race_surface': surface,
                'race_type': race_type,
                'breed': breed,
                'track_condition': track_condition,
                'min_claim_price': min_claiming_price,
                'max_claim_price': max_claiming_price,
                'race_class': race_class,
                'weather': weather,
                'equibase_chart_scrape': True,
            },
            'fractional_data': fractional_times,
            'entry_data': []
        }

        # parse starters
        for starter_item in starter_data:

            # Error checking
            if 'Horse Name (Jockey)' not in starter_item:
                print(f'the starter item is missing Horse Name (Jockey) in {pdf_filename}')
                return []

            horse_name, horse_country, horse_state, jockey_first_name, jockey_last_name = \
                parse_horse_name_string_jockey_from_starter_text(starter_item['Horse Name (Jockey)']['whole_text'])

            pp_entry = next(
                (x for x in pp_data if x['Pgm'] == starter_item['Pgm']),
                None
            )

            horse_item = {
                'horse_name': horse_name,
            }

            jockey_item = {
                'first_name': jockey_first_name,
                'last_name': jockey_last_name
            }

            # weight parsing
            if starter_item['Wgt']['main_text'] == '' and starter_item['Wgt']['super_text'] == '':
                weight = None
            elif starter_item['Wgt']['main_text'] != '' and starter_item['Wgt']['super_text'] == '':
                weight_string = starter_item['Wgt']['main_text'].replace('½', '.5').strip()
                if weight_string.isnumeric():
                    weight = float(weight_string)
                else:
                    weight = None
            elif starter_item['Wgt']['main_text'] == '' and starter_item['Wgt']['super_text'] != '':
                weight_string = starter_item['Wgt']['super_text'].replace('½', '.5').strip()
                if weight_string.isnumeric():
                    weight = float(weight_string)
                else:
                    weight = None
            elif starter_item['Wgt']['main_text'] != '' and starter_item['Wgt']['super_text'] != '':
                weight_string = starter_item['Wgt']['main_text'].strip() + '.' + starter_item['Wgt']['super_text'].strip()
                if weight_string.isnumeric():
                    weight = float(weight_string)
                else:
                    weight = None
            else:
                weight = None

            entry_item = {
                'scratch_indicator': 'N',
                'post_position': starter_item['PP']['whole_text'],
                'program_number': starter_item['Pgm']['whole_text'],
                'finish_position': None if not starter_item['Fin']['main_text'].isnumeric() else starter_item['Fin']['main_text'],
                'weight': weight,
                'comments': starter_item['Comments']['whole_text'],
                'medication_equipment': starter_item['M/E']['whole_text'],
            }

            point_of_call_list = []
            if pp_entry:
                pp_definition = next(
                    (x for x in points_of_call_definition if abs(x['floor'] - distance_feet) < 10),
                    None
                )
                if pp_definition:
                    for call in pp_definition['calls']:
                        if call['text'] in pp_entry:

                            # Fix the start call
                            if 'feet' in call:
                                point_furlongs = round(call['feet']/660, 4)
                            elif call['text'] == 'Start':
                                point_furlongs = 0.5
                            else:
                                continue

                            # Fix horse that didn't finish
                            if not pp_entry[call['text']]['main_text'].isnumeric():
                                continue

                            point_of_call_list.append({
                                'point': call['point'],
                                'text': call['text'],
                                'distance': point_furlongs,
                                'position': int(pp_entry[call['text']]['main_text']),
                                'lengths_back': 0 if int(pp_entry[call['text']]['main_text']) == 1 else lb_text_to_float(pp_entry[call['text']]['super_text']),
                            })


            # assemble
            entry_data_item = {
                'jockey_item': jockey_item,
                'entry_item': entry_item,
                'horse_item': horse_item,
                'point_of_call_list': point_of_call_list
            }

            data_item['entry_data'].append(entry_data_item)

        data_list.append(data_item)

    # Return finished product
    return data_list


if __name__ == '__main__':

    data_list = convert_equibase_result_chart_pdf_to_item('E:\\CodeRepo\\drf_chart_scraper\\TAM060320USA.pdf')
