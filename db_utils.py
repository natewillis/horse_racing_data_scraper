from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import null
from settings import DATABASE
from sqlalchemy.ext.declarative import declarative_base
from models import Races, Horses, Entries, EntryPools, Payoffs, Probables, Tracks, Jockeys, Owners, Trainers, \
    Picks, BettingResults, Workouts, base, AnalysisProbabilities
from sqlalchemy import func


def db_connect():
    """
    Performs database connection using database settings from settings.py.
    Returns sqlalchemy engine instance
    """
    return create_engine(URL(**DATABASE))


def create_drf_live_table(engine, destroy_flag):
    """"""
    if destroy_flag:
        base.metadata.drop_all(bind=engine)
    base.metadata.create_all(engine)


def get_db_session(destroy_flag=False):

    # Connect to the database
    engine = db_connect()
    create_drf_live_table(engine, destroy_flag)
    session_maker_class = sessionmaker(bind=engine)
    session = session_maker_class()

    # Return session
    return session


def shutdown_session_and_engine(session):

    # Get engine from session
    engine = session.get_bind()

    # Close everything out
    session.close()
    engine.dispose()


def find_track_instance_from_item(item, session):
    if 'code' in item:
        return session.query(Tracks).filter(
            Tracks.code == item['code']
        ).first()
    elif 'name' in item:
        return session.query(Tracks).filter(
            Tracks.name == item['name']
        ).first()
    else:
        return


def find_race_instance_from_item(item, session):
    return session.query(Races).filter(
        Races.track_id == item['track_id'],
        Races.race_number == item['race_number'],
        Races.card_date == item['card_date']
    ).first()


def find_jockey_instance_from_item(item, session):
    if len(item['first_name']) == 1:
        return session.query(Jockeys).filter(
            Jockeys.first_name.startswith(item['first_name']),
            Jockeys.last_name == item['last_name']
        ).first()
    else:
        return session.query(Jockeys).filter(
            Jockeys.first_name == item['first_name'],
            Jockeys.last_name == item['last_name']
        ).first()


def find_trainer_instance_from_item(item, session):
    if len(item['first_name']) == 1:
        return session.query(Trainers).filter(
            Trainers.first_name.startswith(item['first_name']),
            Trainers.last_name == item['last_name']
        ).first()
    else:
        return session.query(Trainers).filter(
            Trainers.first_name == item['first_name'],
            Trainers.last_name == item['last_name']
        ).first()


def find_horse_instance_from_item(item, session):
    return session.query(Horses).filter(
        Horses.horse_name == item['horse_name']
    ).first()


def find_entry_instance_from_item(item, session):
    return session.query(Entries).filter(
        Entries.race_id == item['race_id'],
        Entries.horse_id == item['horse_id']
    ).first()


def find_owner_instance_from_item(item, session):
    return session.query(Owners).filter(
        Owners.first_name == item['first_name'],
        Owners.last_name == item['last_name']
    ).first()


def find_entry_pool_instance_from_item(item, session):
    return session.query(EntryPools).filter(
        EntryPools.entry_id == item['entry_id'],
        EntryPools.scrape_time == item['scrape_time'],
        EntryPools.pool_type == item['pool_type']
    ).first()


def find_payoff_instance_from_item(item, session):
    return session.query(Payoffs).filter(
        Payoffs.race_id == item['race_id'],
        Payoffs.wager_type == item['wager_type']
    ).first()


def find_probable_instance_from_item(item, session):
    return session.query(Probables).filter(
        Probables.race_id == item['race_id'],
        Probables.probable_type == item['probable_type'],
        Probables.program_numbers == item['program_numbers'],
        Probables.scrape_time == item['scrape_time']
    ).first()


def find_pick_instance_from_item(item, session):
    return session.query(Picks).filter(
        Picks.bettor_family == item['bettor_family'],
        Picks.bettor_name == item['bettor_name'],
        Picks.race_id == item['race_id'],
        Picks.bet_type == item['bet_type'],
        Picks.bet_win_text == item['bet_win_text']
    ).first()


def find_workout_instance_from_item(item, session):
    return session.query(Workouts).filter(
        Workouts.horse_id == item['horse_id'],
        Workouts.workout_date == item['workout_date'],
        Workouts.track_id == item['track_id'],
    ).first()


def find_analysis_probability_instance_from_item(item, session):
    return session.query(AnalysisProbabilities).filter(
        AnalysisProbabilities.entry_id == item['entry_id'],
        AnalysisProbabilities.analysis_type == item['analysis_type'],
        AnalysisProbabilities.finish_place == item['finish_place'],
    ).first()


def find_betting_result_instance_from_item(item, session):
    return session.query(BettingResults).filter(
        BettingResults.time_frame_text == item['time_frame_text'],
        BettingResults.track_id == item['track_id'],
        BettingResults.bet_type_text == item['bet_type_text'],
        BettingResults.strategy == item['strategy']
    ).first()


def find_instance_from_item(item, item_type, session):

    # Instance Finder Dict
    instance_finder = {
        'track': find_track_instance_from_item,
        'race': find_race_instance_from_item,
        'horse': find_horse_instance_from_item,
        'jockey': find_jockey_instance_from_item,
        'trainer': find_trainer_instance_from_item,
        'entry': find_entry_instance_from_item,
        'owner': find_owner_instance_from_item,
        'entry_pool': find_entry_pool_instance_from_item,
        'payoff': find_payoff_instance_from_item,
        'probable': find_probable_instance_from_item,
        'pick': find_pick_instance_from_item,
        'workout': find_workout_instance_from_item,
        'betting_result': find_betting_result_instance_from_item,
        'analysis_probability': find_analysis_probability_instance_from_item,
    }

    # Return instance
    return instance_finder[item_type](item, session)


def create_new_instance_from_item(item, item_type, session):

    # Model Dict
    model_dict = {
        'track': Tracks,
        'race': Races,
        'horse': Horses,
        'jockey': Jockeys,
        'trainer': Trainers,
        'entry': Entries,
        'owner': Owners,
        'entry_pool': EntryPools,
        'payoff': Payoffs,
        'probable': Probables,
        'pick': Picks,
        'workout': Workouts,
        'analysis_probability': AnalysisProbabilities,
        'betting_result': BettingResults
    }

    # Fix any nulls
    for key, value in item.items():
        if value is None:
            item[key] = null()

    # Create Instance
    instance = model_dict[item_type](**item)

    # Add and commit
    session.add(instance)
    session.commit()

    # Return Instance
    return instance


def load_item_into_database(item, item_type, session):

    # Check if item exists
    if item is None:
        return

    # Get Existing Record
    instance = find_instance_from_item(item, item_type, session)

    # If its new, create a new one in the database
    if instance is None:

        # Process Race
        instance = create_new_instance_from_item(item, item_type, session)

    else:

        # Set the new attributes
        for key, value in item.items():

            # Exceptions
            if item_type == 'race':
                # Never move the off_time later
                if key == 'off_time':
                    if instance.off_time is not None:
                        if value > instance.off_time:
                            continue
            if value is None:
                value = null()

            # Set the attributes
            setattr(instance, key, value)

        # Commit changes
        session.commit()

    # Return race instance
    return instance
