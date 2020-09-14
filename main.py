import logging
import time
from getpass import getpass

import sleekxmpp
from prettytable import PrettyTable
from sleekxmpp.exceptions import IqError, IqTimeout

import client
from bcolors import *

close_login = False

logging.basicConfig(level=logging.INFO,
                    format='%(levelname)-8s %(message)s')

# Prints a table with every user and its index


def print_contact_index(user_dict):
    table = PrettyTable(border=False)
    table.field_names = [f'{BOLD}No. {ENDC}', f'{BOLD}JID{ENDC}']
    table.align = 'l'
    counter = 1
    for jid in user_dict.keys():
        table.add_row([counter, jid])
        counter += 1

    print(table)


def print_all_users(user_dict):
    table = PrettyTable(border=False)
    table.field_names = [f'{BOLD}USERNAME{ENDC}',
                         f'{BOLD}NAME{ENDC}',
                         f'{BOLD}EMAIL{ENDC}',
                         f'{BOLD}JID{ENDC}']
    table.align = 'l'
    for jid, user_info in user_dict.items():
        table.add_row([user_info[0], user_info[1], user_info[2], jid])

    print(table)

# Prints a table with every user and its connection data


def print_users_connection(user_dict):
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

# Hanldes the client once the user logged in


def handle_session(event):
    close_session = False
    xmpp.session_start()
    option = ''
    print(f'{OKGREEN}Logged in as {xmpp.boundjid.bare}{ENDC}')

    while not close_session:
        print(main_menu)
        option = input('Enter an option: ')

        # OPTION 1: Show connected users
        if option == '1':
            print(f'\n{BOLD}Every user un this server:{ENDC}\n')
            users = xmpp.get_all_online()
            print_all_users(users)

            print(f'\n{BLUE}========================================={ENDC}')
            print(f'\n{BOLD}My roster:{ENDC}\n')
            roster = xmpp.get_user_dict()
            print_users_connection(roster)

        # OPTION 2: Add a user to my contact list
        elif option == '2':
            print(f'\n{BOLD}Add user to contact list{ENDC}')
            user_jid = input('Enter user jid: ')
            xmpp.add_user(user_jid)

        # OPTION 4: Private session
        elif option == '4':
            # Get updated roster
            roster = xmpp.get_user_dict()

            # Get all users as list
            users = list(roster.keys())

            # Print table of users with their index
            print_contact_index(roster)
            recipient = input('\nEnter recipient index: ')

            try:
                # Check if user index was correct
                dest = users[int(recipient)-1]
            except:
                # Else, repeat
                print(invalid_option)
                continue

            print(
                f'\nRecipient is: {dest}\nThe unread messages from this user are:')
            for msg in roster[dest].get_messages():
                print(f'\t--> {msg}')

            new_message = input('Enter a message: ')
            xmpp.send_session_message(dest, new_message)

        elif option == '5':

            print(group_options)

            group_option = input('\tEnter an option: ')

            # 1. Create a group
            if group_option == '1':
                print(f'\n{BOLD}Create a group chat{ENDC}')
                group_name = input('Room URL: ')
                nick = input('Nick: ')

                if nick and group_name:
                    xmpp.create_new_room(group_name, nick)
                    print(f'{OKGREEN}{group_name} created!{ENDC}')
                else:
                    print(f'{FAIL}Please set a group name and a nick{ENDC}')
                    continue

            # 2. Join a group
            elif group_option == '2':
                print(f'\n{BOLD}Join a group chat{ENDC}')
                room = input('Room URL: ')
                nick = input('Nick: ')

                if nick and room:
                    xmpp.join_room(room, nick)
                    print(f'{OKGREEN}Joined {room}{ENDC}')
                else:
                    print(f'{FAIL}Please set a group name and a nick{ENDC}')
                    continue

            # 3. Send message to a group
            elif group_option == '3':
                print(f'\n{BOLD}Send message to room{ENDC}')
                room = input('Room URL: ')
                message = input('Message: ')

                if xmpp.send_groupchat_message(room, message):
                    print(f'{OKGREEN}Message sent!{ENDC}')
                else:
                    print(error_msg)

            # 4. Leave group
            elif group_option == '4':
                print(f'\n{BOLD}Leave room{ENDC}')
                room = input('Room URL: ')
                nick = input('Nick: ')

                xmpp.leave_room(room, nick)
                print(f'{OKGREEN}You left the group.{ENDC}')
            

            # 5. Cancel
            elif group_option == '5':
                continue

            # Invalid option
            else:
                print(invalid_option)

        # OPTION 6: Presence message
        elif option == '6':
            print(f'\n{BOLD}Presence message{ENDC}')
            print(show_options)

            # Let user decide his options
            show_input = input('Show: ')
            status = input('Status: ')

            try:
                # Validate if user selected a valid option
                show = show_array[int(show_input)-1]
            except:
                # If not, go to the default one.
                print(
                    f'{WARNING}Incorrect show option selected... Seting show to "available".')
                show = 'available'

            # Send the presence message and inform the user about it.
            xmpp.presence_message(show, status)
            print(f'{OKGREEN}Presence message sent!{ENDC}')

        # OPTION 9: Log out.
        elif option == '7':
            print(f'\n{BOLD}Logging out of {xmpp.boundjid.bare}{ENDC}')
            xmpp.disconnect()
            close_session = True

        # OPTION 10: Delete account from server.
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
            username = input('Enter your jid: ')
            password = getpass('Enter your password: ')

            if username and password:
                print(
                    f'{WARNING}Initiating registration process... please wait.{ENDC}')
                xmpp = client.RegisterBot(username, password)
                xmpp.register_plugin('xep_0030')  # Service Discovery
                xmpp.register_plugin('xep_0004')  # Data forms
                xmpp.register_plugin('xep_0066')  # Out-of-band Data
                xmpp.register_plugin('xep_0077')  # In-band Registration
                xmpp.register_plugin('xep_0045')  # Groupchat
                xmpp.register_plugin('xep_0199')  # XMPP Ping
                xmpp['xep_0077'].force_registration = True

                if xmpp.connect():
                    xmpp.process(block=True)
                else:
                    print(f'{FAIL}Unable to connect to the server{ENDC}')
            else:
                print(f'{FAIL}Input is incorrect.')

        # Login with credentials
        elif option == '2':
            print(f'\n{BOLD}Login to your account{ENDC}')
            # username = input('Enter your username: ')
            # password = getpass('Enter your password: ')
            # username = 'jua17315@redes2020.xyz'
            # password = 'jua17315'
            username = 'testing@redes2020.xyz'
            password = 'testing'

            xmpp = client.Client(username, password)
            xmpp.register_plugin('xep_0030')
            xmpp.register_plugin('xep_0004')
            xmpp.register_plugin('xep_0066')
            xmpp.register_plugin('xep_0077')
            xmpp.register_plugin('xep_0050')
            xmpp.register_plugin('xep_0045')  # Groupchat
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
