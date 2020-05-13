from pint import UnitRegistry
import os

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