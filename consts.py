HEADER = '\033[95m'
OKBLUE = '\033[94m' + 'OK: '
OKGREEN = '\033[92m' + 'OK: '
WARNING = '\033[93m' + 'WARNING: '
FAIL = '\033[91m' + 'FAIL: '
ENDC = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[1;30m'
BLUE = '\033[94m'
RED = '\033[91m'
YELLOW = '\033[93m'

# Menu messages
login_menu = f"""
{HEADER}|=================| LOGIN MENU |=================|{ENDC}
1. Register a new account
2. Log into an account
3. Exit
{HEADER}|================================================|{ENDC}
"""

main_menu = f"""
{HEADER}|=================| MAIN MENU |=================|{ENDC}
1. Show all connected users & my contact list
2. Add a user to my contact list
3. Show user details
4. Private chat
5. Group chat
6. Presence message
7. Send file
8. Log out
9. Delete my account
{HEADER}|===============================================|{ENDC}
"""

group_options = f"""
\tSelect one of the options below:
\t1. Create a group chat
\t2. Join a group chat
\t3. Send message to group
\t4. Exit a group chat
\t5. Cancel
"""

show_options = f"""
Select one of the options below:
1. chat
2. away
3. xa (eXtended away)
4. dnd (do not disturb)
"""

# Errors messages
error_msg = f"""
{FAIL}Something went wrong...{ENDC}
"""
invalid_option = f'{FAIL}please enter a valid option!{ENDC}'

chat_session = f"""
********************************************************
|        YOUR ARE NOW IN A PRIVATE CHAT SESSION        |
********************************************************

Type {BOLD}exit{ENDC} to leave this chat session.
"""

# Userful variables
show_array = ['chat', 'away', 'xa', 'dnd']

# NOTIFICATIONS:
NEW_MESSAGE = '''
|==============> NEW MESSAGE <==============|
'''

FILE_OFFER = '''
<==============| OFFERED FILE |==============>
'''

SUSCRIPTION = '''
|==============| SUSCRIPTION |==============|
'''

GOT_ONLINE = '''
|==============> NOW ONLINE <==============|
'''

GROUPCHAT = '''
|==============>  GROUP CHAT <==============|
'''

STREAM_TRANSFER = '''
|==============> STREAM STARTED <==============|
            File transfer initiated!

Please wait...
'''
