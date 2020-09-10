import logging
import sleekxmpp
import client
from prettytable import PrettyTable
import time
from getpass import getpass
from bcolors import HEADER, WARNING, ENDC, FAIL, OKBLUE, OKGREEN, BOLD
from sleekxmpp.exceptions import IqError, IqTimeout

close_login = False

login_menu = f"""
{HEADER}=============| LOGIN MENU |============={ENDC}
1. Register a new account
2. Log into an account
3. Exit
{HEADER}======================================={ENDC}
"""

error_msg = f"""
{FAIL}Something went wrong...{ENDC}
"""

main_menu = f"""
{HEADER}=============| MAIN MENU |============={ENDC}
1. Show all connected users
2. Add a user to my contact list
3. Show contact details
4. Private chat
5. Group chat
6. Presence message
7. Log out
8. Delete my account
{HEADER}======================================={ENDC}
"""

invalid_option = f'{FAIL}please enter a valid option!{ENDC}'

logging.basicConfig(level=logging.ERROR,
                    format='%(levelname)-8s %(message)s')


def print_users(user_dict):
    table = PrettyTable(border=False)
    table.field_names = [f'{BOLD}JID{ENDC}',
                         f'{BOLD}SHOW{ENDC}',
                         f'{BOLD}STATUS{ENDC}']
    table.align = 'l'
    for jid, user in user_dict.items():
        user_data = user.get_connection_data()
        user_data.insert(0, jid)
        table.add_row(user_data)

    table.sortby = f'{BOLD}SHOW{ENDC}'
    print(table)


def handle_session(event):
    close_session = False
    xmpp.session_start()
    option = ''
    print(f'{OKGREEN}Logged in as {xmpp.boundjid.bare}{ENDC}')

    while not close_session:
        print(main_menu)
        option = input('Enter an option: ')

        # Show connected users
        if option == '1':
            roster = xmpp.get_user_dict()
            print_users(roster)

        # Add a user to my contact list
        elif option == '2':
            user_jid = input('Enter user jid: ')
            xmpp.add_user(user_jid)

        elif option == '7':
            print(f'\nLogging out of {xmpp.boundjid.bare}')
            xmpp.disconnect()
            close_session = True

        elif option == '8':
            print(f'\n{WARNING}Deleting account: {xmpp.boundjid.bare}{ENDC}')
            xmpp.delete_account()
            xmpp.disconnect()
            close_session = True

        else:
            print(invalid_option)


if __name__ == "__main__":
    while not close_login:

        print(login_menu)
        option = input('Enter an option: ')

        # Register a new user
        if option == '1':
            print('\nRegister a new account')
            username = input('Enter your username: ')
            password = getpass('Enter your password: ')

            if username and password:
                print(
                    f'{WARNING}Initiating registration process... please wait.{ENDC}')
                xmpp = client.RegisterBot(username, password)
                xmpp.register_plugin('xep_0030')  # Service Discovery
                xmpp.register_plugin('xep_0004')  # Data forms
                xmpp.register_plugin('xep_0066')  # Out-of-band Data
                xmpp.register_plugin('xep_0077')  # In-band Registration
                xmpp['xep_0077'].force_registration = True

                if xmpp.connect():
                    xmpp.process(block=True)
                else:
                    print(f'{FAIL}Unable to connect to the server{ENDC}')
            else:
                print(f'{FAIL}Input is incorrect.')

        # Login with credentials
        elif option == '2':
            print('\nLogin to your account')
            # username = input('Enter your username: ')
            # password = getpass('Enter your password: ')
            username = 'jua17315@redes2020.xyz'
            password = 'jua17315'

            xmpp = client.Client(username, password)
            xmpp.register_plugin('xep_0030')
            xmpp.register_plugin('xep_0004')
            xmpp.register_plugin('xep_0066')
            xmpp.register_plugin('xep_0077')
            xmpp['xep_0077'].force_registration = True
            xmpp.add_event_handler(
                "session_start", handle_session, threaded=True)
            if xmpp.connect():
                xmpp.process(block=False)
                close_login = True
            else:
                print(f'{FAIL}Unable to connect to the server{ENDC}')
                xmpp.disconnect()
                continue

        elif option == '3':
            print('Exiting the program...')
            close_login = True

        else:
            print(invalid_option)
