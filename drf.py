import datetime
from pytz import timezone
from utils import convert_drf_distance_description_to_furlongs


def create_track_item_from_drf_data(data):

    # Time Zone Dict
    time_zone_dict = {
        'E': 'US/Eastern',
        'C': 'US/Central',
        'M': 'US/Mountain',
        'P': 'US/Pacific'
    }

    # Create Track Dict
    item = dict()
    if 'raceKey' in data:
        if 'trackId' in data['raceKey']:
            item['code'] = data['raceKey']['trackId'].strip().upper()
        if 'country' in data['raceKey']:
            item['country'] = data['raceKey']['country'].strip().upper()
        else:
            item['country'] = 'USA'

    if 'code' not in item:
        return

    if 'trackName' in data:
        item['name'] = data['trackName'].strip().upper()

    # Return created track item
    return item


def create_race_item_from_drf_data(data, track, scrape_time):

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

        # Let python do the processing
        post_time_local_naive = datetime.datetime.strptime(
            f'{data["raceKey"]["raceDate"]["year"]}-'
            f'{data["raceKey"]["raceDate"]["month"] + 1}-'
            f'{data["raceKey"]["raceDate"]["day"]} '
            f'{post_time_string}',
            '%Y-%m-%d %I:%M %p'
        )
        tz = timezone('US/Eastern')  # Display time is always eastern
        post_time_local_aware = tz.localize(post_time_local_naive)
        post_time = post_time_local_aware.astimezone(timezone('UTC')).replace(tzinfo=None)

    else:

        tz = timezone(track.time_zone)
        post_time_local = datetime.datetime.fromtimestamp(data['postTimeLong'] / 1000.0)  # Not UTC already
        post_time_aware = tz.localize(post_time_local)
        post_time = post_time_aware.astimezone(timezone('UTC')).replace(tzinfo=None)

    # Identifying Info
    item['card_date'] = datetime.date(
        year=data['raceKey']['raceDate']['year'],
        month=(data['raceKey']['raceDate']['month']+1),
        day=data['raceKey']['raceDate']['day']
    )
    item['track_id'] = track.track_id
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
    item['race_class'] = data['raceClass']

    # Results Files
    if 'payoffs' in data:
        # Results Datafiles
        item['drf_results'] = True
        item['purse'] = int(data['totalPurse'].replace(',', ''))
        item['track_condition'] = data['trackConditionDescription']
        if data['minimumClaimPrice'] is not None and data['maximumClaimPrice'] is not None:
            if data['maximumClaimPrice'] != '' and data['minimumClaimPrice'] != '':
                item['max_claim_price'] = float(data['maximumClaimPrice'].replace(',', ''))
                item['min_claim_price'] = float(data['minimumClaimPrice'].replace(',', ''))

    else:
        # Odds Datafiles or Entries
        item['purse'] = data['purse']
        item['wager_text'] = data['wagerText']
        if data['minClaimPrice'] is not None and data['maxClaimPrice'] is not None:
            item['min_claim_price'] = data['minClaimPrice']
            item['max_claim_price'] = data['maxClaimPrice']
        if 'totalWinPool' in data:  # Odds data

            # This is a live odds file
            item['drf_live_odds'] = True

            # MTP
            if 'mtpDisplay' in data:
                if data['mtpDisplay'] is not None:
                    if data['mtpDisplay'].strip().upper() == 'OFF':
                        item['off_time'] = scrape_time

        else:  # Entries data
            item['drf_entries'] = True

    # Scraping info
    item['latest_scrape_time'] = scrape_time

    # Return completed item
    return item


def create_horse_item_from_drf_data(runner):

    # Create Horse Dict
    item = dict()

    # Fill in horse data
    item['horse_name'] = runner['horseName'].strip().upper()

    # Return completed item
    return item


def create_jockey_item_from_drf_data(runner):

    # Create Horse Dict
    item = dict()

    # File specific items
    if 'jockeyFirstName' in runner:  # results file
        item['first_name'] = runner['jockeyFirstName'].strip().upper()
        item['last_name'] = runner['jockeyLastName'].strip().upper()
    elif 'jockey' in runner:
        item['first_name'] = runner['jockey']['firstName'].strip().upper()
        item['last_name'] = runner['jockey']['lastName'].strip().upper()
        item['drf_jockey_id'] = runner['jockey']['id']
        item['drf_jockey_type'] = runner['jockey']['type'].strip().upper()
        if runner['jockey']['alias'] is not None:
            item['alias'] = runner['jockey']['alias'].strip()

    # Return completed item
    return item


def create_trainer_item_from_drf_data(runner):

    # Create Jockey Dict
    item = dict()
    if 'trainerFirstName' in runner:  # results file
        item['first_name'] = runner['trainerFirstName'].strip().upper()
        item['last_name'] = runner['trainerLastName'].strip().upper()
    elif 'trainer' in runner:
        item['first_name'] = runner['trainer']['firstName'].strip().upper()
        item['last_name'] = runner['trainer']['lastName'].strip().upper()
        item['drf_trainer_id'] = runner['trainer']['id']
        item['drf_trainer_type'] = runner['trainer']['type'].strip().upper()
        if runner['trainer']['alias'] is not None:
            item['alias'] = runner['trainer']['alias'].strip()

    # Return completed item
    return item


def create_owner_item_from_drf_data(runner):

    # Create Owner Dict
    item = dict()
    item['first_name'] = runner['ownerFirstName'].strip().upper()
    item['last_name'] = runner['ownerLastName'].strip().upper()

    # Return completed item
    return item


def create_entry_item_from_drf_data(runner, horse, race, trainer, jockey, owner, finish_position):

    # Create Entry Dict
    item = dict()
    item['race_id'] = race.race_id
    item['horse_id'] = horse.horse_id
    if owner is not None:
        item['owner_id'] = owner.owner_id
    if trainer is not None:
        item['trainer_id'] = trainer.trainer_id
    if jockey is not None:
        item['jockey_id'] = jockey.jockey_id
    if 'scratchIndicator' in runner:
        item['scratch_indicator'] = runner['scratchIndicator']
    else:
        item['scratch_indicator'] = 'N'

    if 'postPos' in runner:
        item['post_position'] = runner['postPos']

    if 'programNumber' in runner:
        item['program_number'] = runner['programNumber'].strip().upper()

    # Finish Position
    if finish_position > 0:
        item['finish_position'] = finish_position

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

    # Return completed item
    return item


def create_entry_pool_item_from_drf_data(data_pool, entry, scrape_time):

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
    item['pool_type'] = data_pool['poolTypeName'].strip().upper()
    item['amount'] = float(data_pool['amount'])
    if odds_value >= 0:
        item['odds'] = odds_value
    item['dollar'] = float(data_pool['dollar'])

    # Return completed item
    return item


def create_base_wager_amount_dict_from_drf_data(data):

    # Create base amount dict
    base_amount_dict = {}
    for wager in data['wagerTypes']:
        base_amount_dict[wager['wagerType'].strip().upper()] = wager['baseAmount'].strip()

    # Return Base Wager Amount Dictionary
    return base_amount_dict


def create_payoff_item_from_drf_data(payoff, race, base_amount_dict):

    # Create Payoff Dict
    item = dict()
    item['race_id'] = race.race_id
    item['wager_type'] = payoff['wagerType'].strip().upper()
    item['wager_type_name'] = payoff['wagerName'].strip().upper()
    item['winning_numbers'] = payoff['winningNumbers'].strip().upper()
    item['number_of_tickets'] = payoff['numberOfTicketsBet']
    item['total_pool'] = payoff['totalPool']
    item['payoff_amount'] = payoff['payoffAmount']
    item['base_amount'] = base_amount_dict.get(payoff['wagerType'].strip().upper(), 0)

    # Return completed item
    return item


def create_probable_item_from_drf_data(probable_dict, race, scrape_time):

    # Check for will pay
    if not isinstance(probable_dict, dict):
        return

    # Create Probable Dict
    item = dict()
    item['race_id'] = race.race_id
    item['scrape_time'] = scrape_time
    item['probable_type'] = probable_dict['probType'].strip().upper()
    item['program_numbers'] = probable_dict['progNum'].strip().upper()
    item['probable_value'] = probable_dict['probValue']
    item['probable_pool_amount'] = probable_dict['poolAmount']

    # Return completed item
    return item




