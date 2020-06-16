from distil import shutdown_stealth_browser, initialize_stealth_browser, get_html_from_page_with_captcha
from db_utils import get_db_session, shutdown_session_and_engine
import argparse
from utils import str2bool
from equibase import get_db_items_from_equibase_whole_card_entry_html
from import_data import load_equibase_entries_into_database
from pprint import pprint


if __name__ == '__main__':

    # Argument Parsing
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--mode',
                            help="Mode of operation (odds: store odds files)",
                            type=str,
                            required=True,
                            metavar='MODE'
                            )
    arg_parser.add_argument('--debug',
                            help="Debug mode, disables error handling if false",
                            type=str2bool,
                            required=False,
                            default=False,
                            metavar='DEBUG'
                            )
    args = arg_parser.parse_args()

    # Handle debug
    global debug_flag
    debug_flag = args.debug
    if debug_flag:
        print(f'debug mode is {debug_flag}')

    # Setup mode tracker
    modes_run = []

    # Check mode
    if args.mode in ('equibase_entries', 'equibase', 'all'):

        # Mode Tracking
        modes_run.append('equibase_entries')

        # Initialize browser
        browser = initialize_stealth_browser()

        # Connect to the database
        db_session = get_db_session()

        # Get Link
        equibase_link_url = 'https://www.equibase.com/static/entry/BEL061920USA-EQB.html'

        print(f'getting {equibase_link_url}')
        whole_card_html = get_html_from_page_with_captcha(browser, equibase_link_url, 'div.race-nav.center')
        db_items = get_db_items_from_equibase_whole_card_entry_html(whole_card_html)
        pprint(db_items)
        load_equibase_entries_into_database(db_items, db_session)

        # Close everything out
        shutdown_session_and_engine(db_session)
        shutdown_stealth_browser(browser)

    if args.mode in ('equibase_entries_from_html', 'equibase', 'all'):

        # Mode Tracking
        modes_run.append('equibase_entries_from_html')

        # Connect to the database
        db_session = get_db_session()

        # Get Link
        equibase_link_url = 'https://www.equibase.com/static/entry/BEL061920USA-EQB.html'

        print(f'getting {equibase_link_url}')
        with open('C:\\Users\\natew\Desktop\\BEL061920USA.html','r') as html_file:
            whole_card_html = html_file.read()

        #whole_card_html = get_html_from_page_with_captcha(browser, equibase_link_url, 'div.race-nav.center')
        db_items = get_db_items_from_equibase_whole_card_entry_html(whole_card_html)
        load_equibase_entries_into_database(db_items, db_session)

        # Close everything out
        shutdown_session_and_engine(db_session)

    if len(modes_run) == 0:

        print(f'"{args.mode}" is not a valid operational mode!')
        exit(1)

    else:

        print(f'We ran the following modes successfully: {",".join(modes_run)}')
