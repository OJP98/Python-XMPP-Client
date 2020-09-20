# Python-XMPP-Client
XMPP chat client application made with python and SleekXMPP.

## Requirements

* Python 3.1+

## Installation guide

**Optional:** It's better if you try this in a python virtual enviroment

1. Clone this repo with the following url `https://github.com/OJP98/Python-XMPP-Client`
2. With you favorite terminal, install the dependencies with the command `pip install -r requirements.txt`
3. Run the main code with `python main.py`

## Features

This client provides basic features like sending messages, receiving messages and other essential chat-application stuff; all throughout a basic python CLI program.

* Register an account or login to an existing one.
* Show all users registered to the server & show your roster.
* Add a user to the roster/contact list.
* Get any user details (search).
* Send a private message to any user.
* Group chat options:
  * Create a group.
  * Join an existing group.
  * Send a message to a group.
  * Leave a group you are part of.
* Send a presence message (define show and status).
* Send any file to a contact.
* Log out of your account.
* Delete account from server.

## Useful notes

* In order to read any message that a user sent you, first you must "send a private message" and then select the desired user. This will show you a list containing all the messages that you haven't read yet (if any). You may then skip sending a message to the user by just pressing enter, without entering any text on the input.
* This project **DOES NOT** handle all of the errors from the server. Actually, some features might not work as desired with other created clients.

## Developer

* Oscar Juárez

Universidad del Valle de Guatemala - 2020

## License
MIT license, Copyright (c) 2020 Oscar Juárez.