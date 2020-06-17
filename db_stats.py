from models import Races, Entries, Horses
import datetime
from db_utils import load_item_into_database
from sqlalchemy import or_

def log_total_number_of_races(session):

    # Get total number of races in the database
    number_of_races = session.query(Races.race_id).count()

    # If it returns a value enter it into the database
    if number_of_races:

        # Create item
        stat_item = {
            'statistic_name': 'total_number_of_races',
            'statistic_date': datetime.datetime.utcnow(),
            'statistic_value': number_of_races,
        }

        # Write to db
        stat = load_item_into_database(stat_item, 'database_statistic', session)


def log_total_number_of_drf_entry_races(session):

    # Get total number of races in the database
    number_of_races = session.query(Races.race_id)\
        .filter(Races.drf_entries == True)\
        .count()

    # If it returns a value enter it into the database
    if number_of_races:
        # Create item
        stat_item = {
            'statistic_name': 'total_number_of_drf_entry_races',
            'statistic_date': datetime.datetime.utcnow(),
            'statistic_value': number_of_races,
        }

        # Write to db
        stat = load_item_into_database(stat_item, 'database_statistic', session)


def log_total_number_of_equibase_chart_scraped_races(session):
    # Get total number of races in the database
    number_of_races = session.query(Races.race_id) \
        .filter(Races.equibase_chart_scrape == True) \
        .count()

    # If it returns a value enter it into the database
    if number_of_races:

        # Create item
        stat_item = {
            'statistic_name': 'total_number_of_equibase_chart_scraped_races',
            'statistic_date': datetime.datetime.utcnow(),
            'statistic_value': number_of_races,
        }

        # Write to db
        stat = load_item_into_database(stat_item, 'database_statistic', session)


def log_total_number_of_missing_equibase_ids(session):

    # Get total number of races in the database
    number_of_horses = session.query(Horses.horse_id.distinct()).join(Entries).join(Races) \
        .filter(
            Races.race_id == Entries.race_id,
            Horses.horse_id == Entries.horse_id,
            Races.drf_entries == True,
            Horses.equibase_horse_id.is_(None),
        ).count()

    # If it returns a value enter it into the database
    if number_of_horses:
        # Create item
        stat_item = {
            'statistic_name': 'total_number_of_missing_equibase_ids',
            'statistic_date': datetime.datetime.utcnow(),
            'statistic_value': number_of_horses,
        }

        # Write to db
        stat = load_item_into_database(stat_item, 'database_statistic', session)


def log_total_number_of_remaining_detail_scrapes(session):

    # Get total number of races in the database
    number_of_horses = session.query(Horses.horse_id.distinct()).join(Entries).join(Races) \
        .filter(
            Races.race_id == Entries.race_id,
            Horses.horse_id == Entries.horse_id,
            Races.drf_entries == True,
            Races.card_date < datetime.date.today(),
            or_(
                (Horses.equibase_horse_detail_scrape_date - Races.card_date) <= datetime.timedelta(days=-7),
                Horses.equibase_horse_detail_scrape_date.is_(None)
            ),
        ).count()

    # If it returns a value enter it into the database
    if number_of_horses:
        # Create item
        stat_item = {
            'statistic_name': 'total_number_of_remaining_detail_scrapes',
            'statistic_date': datetime.datetime.utcnow(),
            'statistic_value': number_of_horses,
        }

        # Write to db
        stat = load_item_into_database(stat_item, 'database_statistic', session)


def record_all_statistics(session):
    
    log_total_number_of_missing_equibase_ids(session)
    log_total_number_of_equibase_chart_scraped_races(session)
    log_total_number_of_drf_entry_races(session)
    log_total_number_of_races(session)
    log_total_number_of_remaining_detail_scrapes(session)