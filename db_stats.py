from models import Races, Entries, Horses, Tracks
import datetime
from db_utils import load_item_into_database
from sqlalchemy import or_, and_


def log_total_number_of_races(session):

    # Get total number of races in the database
    number_of_races = session.query(Races.race_id).count()

    # If it returns a value enter it into the database
    if number_of_races:

        # Create item
        stat_item = {
            'statistic_name': 'number_of_races_total',
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
            'statistic_name': 'drf_entry_races_totals',
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
            'statistic_name': 'equibase_chart_scraped_race_total',
            'statistic_date': datetime.datetime.utcnow(),
            'statistic_value': number_of_races,
        }

        # Write to db
        stat = load_item_into_database(stat_item, 'database_statistic', session)


def log_total_number_of_horse_detail_races(session):
    # Get total number of races in the database
    number_of_races = session.query(Races.race_id) \
        .filter(Races.equibase_horse_results == True) \
        .count()

    # If it returns a value enter it into the database
    if number_of_races:

        # Create item
        stat_item = {
            'statistic_name': 'equibase_horse_detail_race_total',
            'statistic_date': datetime.datetime.utcnow(),
            'statistic_value': number_of_races,
        }

        # Write to db
        stat = load_item_into_database(stat_item, 'database_statistic', session)


def log_total_number_of_missing_equibase_ids(session):

    # Get total number of races in the database
    number_of_horses = session.query(
        Horses, Races, Tracks, Entries
    ).filter(
        Horses.horse_id == Entries.horse_id
    ).filter(
        Races.race_id == Entries.race_id
    ).filter(
        Tracks.track_id == Races.track_id
    ).filter(
        Horses.equibase_horse_id.is_(None)
    ).filter(
        Races.drf_entries == True,
        Races.equibase_entries == True,
        Entries.scratch_indicator == 'N'
    ).count()

    # If it returns a value enter it into the database
    if number_of_horses:
        # Create item
        stat_item = {
            'statistic_name': 'equibase_id_backlog',
            'statistic_date': datetime.datetime.utcnow(),
            'statistic_value': number_of_horses,
        }

        # Write to db
        stat = load_item_into_database(stat_item, 'database_statistic', session)


def log_total_number_of_remaining_detail_scrapes(session):

    # Get horse count
    number_of_horses = session.query(Horses, Races, Entries).filter(
        Races.race_id == Entries.race_id,
        Horses.horse_id == Entries.horse_id,
        Races.drf_entries == True,
        Horses.equibase_horse_id.isnot(None),
        Entries.scratch_indicator == 'N',
        or_(
            Horses.equibase_horse_detail_scrape_date.is_(None),
            and_(
                (Races.card_date - Horses.equibase_horse_detail_scrape_date) > datetime.timedelta(days=7),
                Races.card_date <= datetime.date.today()
            ),
            and_(
                (datetime.date.today() - Races.card_date) >= 2,
                Races.card_date > Horses.equibase_horse_detail_scrape_date
            )
        )
    ).count()

    # If it returns a value enter it into the database
    if number_of_horses:
        # Create item
        stat_item = {
            'statistic_name': 'detail_scrape_backlog',
            'statistic_date': datetime.datetime.utcnow(),
            'statistic_value': number_of_horses,
        }

        # Write to db
        stat = load_item_into_database(stat_item, 'database_statistic', session)


def log_total_number_of_remaining_chart_downloads(session):

    # Get horse count
    number_of_charts = session.query(Races.card_date, Races.track_id).filter(
            or_(
                Races.equibase_chart_download_date.is_(None),
                Races.equibase_chart_download_date < datetime.datetime(year=1910, month=1, day=1)
            ),
            Races.equibase_chart_scrape.isnot(True),
            Races.card_date < datetime.date.today()
        ).group_by(Races.card_date, Races.track_id).count()

    # If it returns a value enter it into the database
    if number_of_charts:
        # Create item
        stat_item = {
            'statistic_name': 'chart_download_backlog',
            'statistic_date': datetime.datetime.utcnow(),
            'statistic_value': number_of_charts,
        }

        # Write to db
        stat = load_item_into_database(stat_item, 'database_statistic', session)


def record_all_statistics(session):

    log_total_number_of_remaining_chart_downloads(session)
    log_total_number_of_horse_detail_races(session)
    log_total_number_of_missing_equibase_ids(session)
    log_total_number_of_equibase_chart_scraped_races(session)
    log_total_number_of_drf_entry_races(session)
    log_total_number_of_races(session)
    log_total_number_of_remaining_detail_scrapes(session)