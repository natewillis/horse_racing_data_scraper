from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Boolean, Date
from sqlalchemy.ext.declarative import declarative_base

# Setup base
base = declarative_base()


class Tracks(base):
    """Sqlalchemy Races model"""
    __tablename__ = "tracks"

    track_id = Column(Integer, primary_key=True)
    code = Column('code', String)
    name = Column('name', String)
    time_zone = Column('time_zone', String)
    country = Column('country', String)


class Jockeys(base):
    """Sqlalchemy Jockey model"""
    __tablename__ = "jockeys"
    jockey_id = Column('jockey_id', Integer, primary_key=True)
    first_name = Column('first_name', String)
    last_name = Column('last_name', String)
    drf_jockey_id = Column('drf_jockey_id', Integer)
    drf_jockey_type = Column('drf_jockey_type', String)
    alias = Column('alias', String)


class Trainers(base):
    """Sqlalchemy Jockey model"""
    __tablename__ = "trainers"
    trainer_id = Column('trainer_id', Integer, primary_key=True)
    first_name = Column('first_name', String)
    last_name = Column('last_name', String)
    drf_trainer_id = Column('drf_trainer_id', Integer)
    drf_trainer_type = Column('drf_trainer_type', String)
    alias = Column('alias', String)


class Owners(base):
    """Sqlalchemy Jockey model"""
    __tablename__ = "owners"
    owner_id = Column('owner_id', Integer, primary_key=True)
    first_name = Column('first_name', String)
    last_name = Column('last_name', String)


class Races(base):
    """Sqlalchemy Races model"""
    __tablename__ = "races"

    race_id = Column(Integer, primary_key=True)

    # Identifying Info
    track_id = Column('track_id', Integer, ForeignKey('tracks.track_id'))
    race_number = Column('race_number', Integer)
    card_date = Column('card_date', Date)
    day_evening = Column('day_evening', String)
    country = Column('country', String)

    # Race Info
    post_time = Column('post_time', DateTime)  # UTC
    distance = Column('distance', Float)  # In furlongs
    purse = Column('purse', Integer, nullable=True)
    age_restriction = Column('age_restriction', String, nullable=True)
    race_restriction = Column('race_restriction', String, nullable=True)
    sex_restriction = Column('sex_restriction', String, nullable=True)
    wager_text = Column('wager_text', String, nullable=True)
    race_surface = Column('race_surface', String)
    race_type = Column('race_type', String, nullable=True)
    breed = Column('breed', String, nullable=True)
    track_condition = Column('track_condition', String, nullable=True)
    min_claim_price = Column('min_claim_price', Float)
    max_claim_price = Column('max_claim_price', Float)
    race_class = Column('race_class', String)

    # Inferred Data
    off_time = Column('off_time', DateTime)

    # Types of Parsing
    drf_results = Column('drf_results', Boolean, default=False)
    drf_live_odds = Column('drf_live_odds', Boolean, default=False)
    drf_entries = Column('drf_entries', Boolean, default=False)

    # Scraping Info
    latest_scrape_time = Column('latest_scrape_time', DateTime)  # UTC


class Horses(base):
    """Sqlalchemy Races model"""
    __tablename__ = "horses"

    horse_id = Column('horse_id', Integer, primary_key=True)

    # Identifying Info
    horse_name = Column('horse_name', String)


class Entries(base):

    """Sqlalchemy Races model"""
    __tablename__ = "entries"

    entry_id = Column('entry_id', Integer, primary_key=True)
    race_id = Column('race_id', Integer, ForeignKey('races.race_id'))
    horse_id = Column('horse_id', Integer, ForeignKey('horses.horse_id'))
    scratch_indicator = Column('scratch_indicator', String)
    post_position = Column('post_position', Integer, nullable=True)
    program_number = Column('program_number', String, nullable=True)
    trainer_id = Column('trainer_id', Integer, ForeignKey('trainers.trainer_id'))
    jockey_id = Column('jockey_id', Integer, ForeignKey('jockeys.jockey_id'))
    owner_id = Column('owner_id', Integer, ForeignKey('owners.owner_id'))

    # Results
    win_payoff = Column('win_payoff', Float, default=0)
    place_payoff = Column('place_payoff', Float, default=0)
    show_payoff = Column('show_payoff', Float, default=0)
    finish_position = Column('finish_position', Integer, nullable=True)


class EntryPools(base):

    """Sqlalchemy Races model"""
    __tablename__ = "entry_pools"

    entry_pool_id = Column('entry_pool_id', Integer, primary_key=True)
    entry_id = Column('entry_id', ForeignKey('entries.entry_id'))
    scrape_time = Column('scrape_time', DateTime)
    pool_type = Column('pool_type', String)
    amount = Column('amount', Float)
    odds = Column('odds', Float, nullable=True)
    dollar = Column('dollar', Float, nullable=True)


class Payoffs(base):
    """Sqlalchemy Races model"""
    __tablename__ = "payoffs"

    payoff_id = Column('entry_pool_id', Integer, primary_key=True)
    race_id = Column('race_id', Integer, ForeignKey('races.race_id'))
    wager_type = Column('wager_type', String)
    wager_type_name = Column('wager_type_name', String)
    winning_numbers = Column('winning_numbers', String)
    number_of_tickets = Column('number_of_tickets', Integer)
    total_pool = Column('total_pool', Integer)
    payoff_amount = Column('payoff_amount', Float)
    base_amount = Column('base_amount', Float)  # Check the wagertypes section


class Probables(base):
    """Sqlalchemy Races model"""
    __tablename__ = "probables"

    probable_id = Column('entry_pool_id', Integer, primary_key=True)
    race_id = Column('race_id', Integer, ForeignKey('races.race_id'))
    scrape_time = Column('scrape_time', DateTime)
    probable_type = Column('probable_type', String)
    program_numbers = Column('program_numbers', String)
    probable_value = Column('probable_value', Float)
    probable_pool_amount = Column('probable_pool_amount', Float)


class Picks(base):
    __tablename__ = "picks"
    pick_id = Column('pick_id', Integer, primary_key=True)
    bettor_family = Column('bettor_family', String)
    bettor_name = Column('bettor_name', String)
    race_id = Column('race_id', Integer, ForeignKey('races.race_id'))  # The race the ticket would collect (last race)
    bet_type = Column('bet_type', String)
    bet_cost = Column('bet_cost', Float)
    bet_return = Column('bet_return', Float, default=0)
    bet_win_text = Column('bet_win_text', String)
    bet_origin_date = Column('bet_origin_date', DateTime)


class BettingResults(base):
    """Sqlalchemy Races model"""
    __tablename__ = "betting_results"

    betting_result_id = Column('betting_result_id', Integer, primary_key=True)
    strategy = Column('strategy', String)
    track_id = Column('track_id', String)
    bet_type_text = Column('bet_type_text', String)
    time_frame_text = Column('time_frame_text', String)
    bet_count = Column('bet_count', Integer)
    bet_cost = Column('bet_cost', Float)
    bet_return = Column('bet_return', Float)
    bet_roi = Column('bet_roi', Float)
    bet_success_count = Column('bet_success_count', Integer)
    update_time = Column('update_time', DateTime)
