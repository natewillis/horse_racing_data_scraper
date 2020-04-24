from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Date, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine.url import URL
from settings import DATABASE


DeclarativeBase = declarative_base()


def db_connect():
    """
    Performs database connection using database settings from settings.py.
    Returns sqlalchemy engine instance
    """
    return create_engine(URL(**DATABASE))


def create_drf_live_table(engine):
    """"""
    # DeclarativeBase.metadata.drop_all(bind=engine)
    DeclarativeBase.metadata.create_all(engine)


class Races(DeclarativeBase):
    """Sqlalchemy Races model"""
    __tablename__ = "races"
    __table_args__ = {'schema': 'drf'}

    id = Column(Integer, primary_key=True)
    track_id = Column('track_id', String)
    race_number = Column('race_number', Integer)
    race_date = Column('race_date', Date)
    post_time = Column('post_time', DateTime, nullable=True)
    day_evening = Column('day_evening', String, nullable=True)
    country = Column('country', String, nullable=True)
    distance_description = Column('distance_description', String, nullable=True)
    purse = Column('purse', Integer, nullable=True)
    has_exacta = Column('has_exacta', Boolean)
    exacta_minimum_wager = Column('exacta_minimum_wager', Float, nullable=True)
    exacta_minimum_box_wager = Column('exacta_minimum_box_wager', Float, nullable=True)
    exacta_pool_total = Column('exacta_pool_total', Float, nullable=True)
    exacta_winning_ticket_numbers = Column('exacta_winning_ticket_numbers', String, nullable=True)
    exacta_winning_ticket_base = Column('exacta_winning_ticket_base', Float, nullable=True)
    exacta_winning_ticket_payoff = Column('exacta_winning_ticket_payoff', Float, nullable=True)
    win_pool_total = Column('win_pool_total', Float, nullable=True)
    place_pool_total = Column('place_pool_total', Float, nullable=True)

    def live_odds_link(self):
        return ("http://www.drf.com/liveOdds/tracksPoolDetails" +
                "/currentRace/" + str(self.race_number) +
                "/trackId/" + self.track_id +
                "/country/" + self.country +
                "/dayEvening/" + self.day_evening +
                "/date/" + self.race_date.strftime("%m-%d-%Y"))

    def results_link(self):
        return("https://www.drf.com/results/resultDetails/id/" +
               self.track_id + "/country/" + self.country +
               "/date/" + self.race_date.strftime("%m-%d-%Y"))


class Horses(DeclarativeBase):
    """Sqlalchemy Horses model"""
    __tablename__ = "horses"
    __table_args__ = {'schema': 'drf'}

    id = Column(Integer, primary_key=True)
    horse_name = Column('horse_name', String)


class Entries(DeclarativeBase):
    """Sqlalchemy Entries model"""
    __tablename__ = "entries"
    __table_args__ = {'schema': 'drf'}

    id = Column(Integer, primary_key=True)
    race_id = Column('race_id', Integer)
    horse_id = Column('horse_id', Integer)
    scratch_indicator = Column('scratch_indicator', String)
    post_position = Column('post_position', Integer, nullable=True)
    program_number = Column('program_number', String, nullable=True)
    win_pool_percent = Column('win_pool_percent', Float, nullable=True)
    place_pool_percent = Column('place_pool_percent', Float, nullable=True)
    win_payoff = Column('win_payoff', Float, nullable=True)
    place_payoff = Column('place_payoff', Float, nullable=True)


class Exacta_Probables(DeclarativeBase):
    """Sqlalchemy Entries model"""
    __tablename__ = "exacta_probables"
    __table_args__ = {'schema': 'drf'}

    id = Column(Integer, primary_key=True)
    race_id = Column('race_id', Integer)
    exacta_ticket_numbers = Column('exacta_ticket_numbers', String)
    exacta_probable_value = Column('exacta_probable_value', Float, nullable=True)
    exacta_pool_amount = Column('exacta_pool_amount', Float, nullable=True)






