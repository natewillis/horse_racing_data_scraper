from pint import UnitRegistry
import os
import re
from word2number import w2n
import fractions


def get_files_in_folders(path):

    # init return list
    file_list = []

    # get all folders but base
    folders = list(os.walk(path))[1:]

    # loop folders
    for folder in folders:
        files = os.listdir(folder[0])
        for file in files:
            file_list.append(os.path.join(folder[0], file))

    # return
    return file_list


def remove_empty_folders(path):

    # get all folders but base
    folders = list(os.walk(path))[1:]

    # loop folders
    for folder in folders:
        if len(os.listdir(folder[0])) == 0:
            print(f'removing {folder[0]}')
            os.rmdir(folder[0])


def lb_text_to_float(lb_text):

    # Process
    lb_text = lb_text.upper().strip()

    if lb_text == 'NOSE':
        return 0.05,
    elif lb_text == 'HEAD':
        return 0.2
    elif lb_text == 'NECK':
        return 0.3
    else:
        return float(sum(fractions.Fraction(term) for term in lb_text.split()))


def convert_mixed_fraction_to_num(num_string):

    # Uppercase everything to make life easier
    num_string = num_string.upper()

    # Fraction dictionary
    denominator_dictionary = {
        'HALF': 2,
        'THIRD': 3,
        'FOURTH': 4,
        'FIFTH': 5,
        'SIXTH': 6,
        'SEVENTH': 7,
        'EIGHTH': 8,
        'NINTH': 9,
        'TENTH': 10,
        'ELEVENTH': 11,
        'TWELFTH': 12,
        'THIRTEENTH': 13,
        'FOURTEENTH': 14,
        'FIFTEENTH': 15,
        'SIXTEENTH': 16
    }

    # Check for fraction
    if 'AND' in num_string:

        # Figure out if its a fraction or a big number
        split_words = num_string.split(' ')
        fraction_flag = False
        for word in split_words:
            if word in denominator_dictionary:
                fraction_flag = True

        if fraction_flag:
            # Split the string into parts
            split_number = num_string.split(' AND ')
            whole_number_string = split_number[0]
            fraction_number_string = split_number[1]

            # Whole number conversion
            whole_number_int = w2n.word_to_num(whole_number_string)

            #Fraction conversion
            split_fraction = fraction_number_string.split(' ')
            if len(split_fraction) == 2:

                # numerator
                numerator = w2n.word_to_num(split_fraction[0].strip())

                # denominator
                denominator_string = split_fraction[1].strip()
                if denominator_string[-1] == 'S':
                    denominator_string = denominator_string[:-1]

                if denominator_string in denominator_dictionary:
                    denominator = denominator_dictionary[denominator_string]
                    fraction_part = round(numerator/denominator,  4)
                else:
                    print(f'{denominator_string} was not recognized!')
                    fraction_part = 0

                fraction_number = whole_number_int + fraction_part

            else:

                print(f'ERROR! {fraction_number_string} doesnt parse out of {num_string}')
                fraction_number = 0
        else:
            # its a big number
            fraction_number = w2n.word_to_num(num_string)

    else:

        fraction_number = w2n.word_to_num(num_string)

    return fraction_number


def convert_equibase_chart_distance_string_to_furlongs(distance_string):

    # Check how many units
    different_units = ['MILE', 'FURLONG', 'YARD']
    num_units = 0
    for unit in different_units:
        if unit in distance_string:
            num_units += 1

    # Check for case with mixed units
    if num_units == 1:

        # Split the units off of the distance string
        units = distance_string.split(' ')[-1]
        distance_string = distance_string[:-len(units)].strip()
        units = units.strip()

        # Convert string to number
        distance_numeric = convert_mixed_fraction_to_num(distance_string)
        final_distance_string = f'{distance_numeric} {units.lower()}'

    elif num_units == 2:

        # split the two different unit strings out
        final_distance_strings = []
        split_different_distance_strings = distance_string.split(' AND ')
        if len(split_different_distance_strings) != 2:
            split_different_distance_strings = distance_string.split(' ')
            if len(split_different_distance_strings) == 4:
                split_different_distance_strings = [
                    split_different_distance_strings[0] + ' ' + split_different_distance_strings[1],
                    split_different_distance_strings[2] + ' ' + split_different_distance_strings[3]
                ]
            else:
                print(f'cant figure {distance_string} out')
                split_different_distance_strings = []

        for different_distance_string in split_different_distance_strings:
            # Split the units off of the distance string
            units = different_distance_string.split(' ')[-1]
            current_different_distance_string = different_distance_string[:-len(units)].strip()
            units = units.strip()

            # Convert string to number
            current_distance_numeric = convert_mixed_fraction_to_num(current_different_distance_string)
            final_distance_strings.append(f'{current_distance_numeric} {units}')

        # Join the strings together
        final_distance_string = ' '.join(final_distance_strings)

    else:
        final_distance_string = ''

    # Convert distance to furlongs
    final_distance = convert_drf_distance_description_to_furlongs(final_distance_string)

    # Return final distance
    return final_distance


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
