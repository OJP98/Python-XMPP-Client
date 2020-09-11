import time
import logging
import getpass
import threading
from sleekxmpp import ClientXMPP
from sleekxmpp.exceptions import IqError, IqTimeout
from bcolors import OKGREEN, OKBLUE, WARNING, FAIL, ENDC


class Client(ClientXMPP, threading.Thread):

    print_lock = threading.Lock()

    def __init__(self, jid, password):

        ClientXMPP.__init__(self, jid, password)
        self.auto_authorize = True
        self.auto_subscribe = True
        self.user_dict = {}

        # self.add_event_handler('session_start', self.session_start)
        self.add_event_handler('message', self.received_message)
        self.add_event_handler('disconnected', self.got_disconnected)
        self.add_event_handler('failed_auth', self.on_failed_auth)
        self.add_event_handler('presence_subscribed',
                               self.new_presence_subscribed)
        self.add_event_handler("got_offline", self.presence_offline)
        self.add_event_handler('changed_status', self.wait_for_presences)
        self.received = set()
        self.presences_received = threading.Event()

    def session_start(self):
        try:
            self.get_roster(block=True)
        except IqError as err:
            print('Error: %s' % err.iq['error']['condition'])
        except IqTimeout:
            print('Error: Request timed out')

        self.send_presence()

    def create_user_dict(self, wait=False):
        groups = self.client_roster.groups()
        for group in groups:
            for jid in groups[group]:
                # Check we are not evaluating ourselves
                if jid == self.boundjid.bare:
                    continue

                # Get some data
                sub = self.client_roster[jid]['subscription']
                name = self.client_roster[jid]['name']
                connections = self.client_roster.presence(jid)

                # Check if connections is empty
                if connections.items():
                    # Go through each connection
                    for res, pres in connections.items():

                        if res:
                            ''

                        show = 'available'
                        status = ''
                        if pres['show']:
                            show = pres['show']
                        if pres['status']:
                            status = pres['status']

                        # Check if the user is in the dict, else add it
                        if not jid in self.user_dict:
                            self.user_dict[jid] = User(
                                jid, name, show, status, sub)
                        else:
                            self.user_dict[jid].update_data(status, show)

                # User is not connected, still add him to the dict
                else:
                    if not jid in self.user_dict:
                        self.user_dict[jid] = User(
                            jid, name, 'offline', '', sub)

    # Returns a dict jid - User. If it's empty, create it.
    def get_user_dict(self):
        if not self.user_dict:
            self.create_user_dict()
        return self.user_dict

    # Create user dict on new presence
    def wait_for_presences(self, pres):
        self.received.add(pres['from'].bare)
        if len(self.received) >= len(self.client_roster.keys()):
            self.presences_received.set()
        else:
            self.presences_received.clear()

        self.create_user_dict()

    def received_message(self, msg):

        sender = str(msg['from'])
        sender = sender.split('/')[0]
        if msg['type'] in ('chat', 'normal'):
            print(f'New message from {sender}')
            
            if not sender in self.user_dict:
                self.user_dict[sender] = User(sender, '', '', '')
            
            self.user_dict[sender].add_message_to_list(msg['body'])

            # msg.reply('Thanks for sending\n%(body)s' % msg).send()

    def got_disconnected(self, event):
        print(f'{OKBLUE}Logged out from the current session{ENDC}')

    def on_failed_auth(self, event):
        print(f'{FAIL}Credentials are not correct.{ENDC}')
        self.disconnect()

    def add_user(self, username):
        self.send_presence_subscription(pto=username,
                                        ptype='subscribe',
                                        pfrom=self.boundjid.bare)
        print(f'{OKBLUE}Subscribed to {username}!{ENDC}')

    def new_presence_subscribed(self, presence):
        print('PRESENCE SUBSCRIBED!')
        print(presence)

    def delete_account(self):
        resp = self.Iq()
        resp['type'] = 'set'
        resp['from'] = self.boundjid.full
        resp['register']['remove'] = True

        try:
            resp.send(now=True)
            print(f'{OKGREEN}Account deleted for {self.boundjid}{ENDC}')
        except IqError as e:
            logging.error('Could not unregister account: %s' %
                          e.iq['error']['text'])
            self.disconnect()
        except IqTimeout:
            logging.error('No response from server.')
            self.disconnect()

    def presence_offline(self, presence):
        new_presence = str(presence['from']).split('/')[0]
        if self.boundjid.bare != new_presence and new_presence in self.user_dict:
            self.user_dict[new_presence].update_data(
                '', presence['type'])
    
    def presence_message(self, show, status):
        self.send_presence(pshow=show, pstatus=status)

    def send_session_message(self, recipient, message):
        print('sending a message to',recipient)
        print('from', self.boundjid.full)
        self.send_message(
                        mto=recipient,
                        mbody=message,
                        mtype='chat',
                        mfrom=self.boundjid.bare)
        if recipient in self.user_dict:
            self.user_dict[recipient].clean_unread_messages()
    

    def join_room(self, room, nick):
        self.plugin['xep_0045'].joinMUC(room, nick, wait=True)
    
    def leave_room(self, room, nick):
        self.plugin['xep_0045'].leaveMUC(room, nick)

    def send_groupchat_message(self, to, message):

        try:
            self.send_message(
                mto=to,
                mbody=message,
                mtype='groupchat',
                mfrom=self.boundjid.full
            )
            return True
        except:
            return False


class RegisterBot(ClientXMPP):
    def __init__(self, jid, password):
        ClientXMPP.__init__(self, jid, password)

        self.add_event_handler('register', self.register, threaded=False)

    def register(self, event):
        resp = self.Iq()
        resp['type'] = 'set'
        resp['register']['username'] = self.boundjid.user
        resp['register']['password'] = self.password

        try:
            resp.send(now=True)
            print(f'{OKGREEN}Account created for {self.boundjid}!{ENDC}')
        except IqError:
            print(
                f'{FAIL}Could not register account.{ENDC}')
        except IqTimeout:
            print(f'{FAIL}No response from server.{ENDC}')

        self.disconnect()


class User():
    def __init__(self, jid, name, show, status, subscription):
        self.jid = jid
        self.name = name
        self.show = show
        self.status = status
        self.messages = []

    def update_data(self, status, show):
        self.show = show
        self.status = status

    def get_connection_data(self):
        return [self.show, self.status]

    def add_message_to_list(self, msg):
        self.messages.append(msg)
    
    def clean_unread_messages(self):
        self.messages = []
    
    def get_messages(self):
        return self.messages
