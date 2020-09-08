import logging
import sleekxmpp
import client
from getpass import getpass
from bcolors import HEADER, WARNING, ENDC, FAIL, OKBLUE, OKGREEN
from sleekxmpp.exceptions import IqError, IqTimeout

close = False
option = 0

login_menu = f"""
{HEADER}==========| MENU |=========={ENDC}
1. Register a new account
2. Unregister an existing account
2. Log into an account
{HEADER}============================{ENDC}
"""

error_msg = f"""
{FAIL}Something went wrong...{ENDC}
"""

main_menu = f"""
{HEADER}==========| MENU |=========={ENDC}
1. Show all connected users
2. Add a user to my contact list
3. Show contact details
4. Private chat
5. Group chat
6. Presence message
7. Log out
8. Delete my account
{HEADER}============================{ENDC}
"""

logging.basicConfig(level=logging.INFO,
                    format='%(levelname)-8s %(message)s')

while not close:

    print(login_menu)
    option = input('Enter an option: ')

    try:
        option = int(option)
    except:
        print(f"{WARNING}Please enter a valid number!{ENDC}")
        continue

    # Register a new user
    if option == 1:
        username = input('Enter your username: ')
        password = getpass('Enter your password: ')

        if client.Register(username=username, password=password):
            print(f'{OKBLUE}{username} registered succesfully!{ENDC}')
        else:
            print(error_msg)

    elif option == 2:
        # username = input('Enter your username: ')
        # password = getpass('Enter your password: ')
        username = None
        password = None

        if client.Unregister(username=username, password=password):
            print(f'{OKBLUE}{username} unregistered succesfully!{ENDC}')
        else:
            print(error_msg)
