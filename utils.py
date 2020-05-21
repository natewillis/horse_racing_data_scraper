from pint import UnitRegistry
import os
import re


def convert_drf_distance_description_to_furlongs(distance_string):

    # Load unit conversion
    ureg = UnitRegistry()

    # Distance Calcs
    # Error check distance values
    if distance_string is None:
        return 0
    if distance_string == '':
        return 0
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

    return round(distance.to(ureg.furlong).magnitude, 4)


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


def get_horse_origin_from_name(horse_name_with_origin):

    # Initialize Return
    horse_name = horse_name_with_origin.strip().upper()
    country = 'USA'
    state = None

    # Perform Matching
    horse_name_pattern = r'([A-Z\' .-]+)(\(([A-Z]+)\))?'
    horse_name_search_obj = re.search(horse_name_pattern, horse_name)
    if horse_name_search_obj:
        horse_name = horse_name_search_obj.group(1).strip().upper()
        if horse_name_search_obj.group(3) is not None:
            origin_text = horse_name_search_obj.group(3).strip().upper()
            if origin_text in usa_state_dict():
                country = 'USA'
                state = origin_text
            else:
                country = origin_text
                state = None

    return horse_name, country, state


def usa_state_dict():

    return {
        "AL": "Alabama",
        "AK": "Alaska",
        "AS": "American Samoa",
        "AZ": "Arizona",
        "AR": "Arkansas",
        "CA": "California",
        "CO": "Colorado",
        "CT": "Connecticut",
        "DE": "Delaware",
        "DC": "District Of Columbia",
        "FM": "Federated States Of Micronesia",
        "FL": "Florida",
        "GA": "Georgia",
        "GU": "Guam",
        "HI": "Hawaii",
        "ID": "Idaho",
        "IL": "Illinois",
        "IN": "Indiana",
        "IA": "Iowa",
        "KS": "Kansas",
        "KY": "Kentucky",
        "LA": "Louisiana",
        "ME": "Maine",
        "MH": "Marshall Islands",
        "MD": "Maryland",
        "MA": "Massachusetts",
        "MI": "Michigan",
        "MN": "Minnesota",
        "MS": "Mississippi",
        "MO": "Missouri",
        "MT": "Montana",
        "NE": "Nebraska",
        "NV": "Nevada",
        "NH": "New Hampshire",
        "NJ": "New Jersey",
        "NM": "New Mexico",
        "NY": "New York",
        "NC": "North Carolina",
        "ND": "North Dakota",
        "MP": "Northern Mariana Islands",
        "OH": "Ohio",
        "OK": "Oklahoma",
        "OR": "Oregon",
        "PW": "Palau",
        "PA": "Pennsylvania",
        "PR": "Puerto Rico",
        "RI": "Rhode Island",
        "SC": "South Carolina",
        "SD": "South Dakota",
        "TN": "Tennessee",
        "TX": "Texas",
        "UT": "Utah",
        "VT": "Vermont",
        "VI": "Virgin Islands",
        "VA": "Virginia",
        "WA": "Washington",
        "WV": "West Virginia",
        "WI": "Wisconsin",
        "WY": "Wyoming"
    }
