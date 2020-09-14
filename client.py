import time
import logging
import getpass
import threading
from sleekxmpp import ClientXMPP
from sleekxmpp.exceptions import IqError, IqTimeout
from xml.etree import cElementTree as ET
from sleekxmpp.plugins.xep_0004.stanza.field import FormField, FieldOption
from sleekxmpp.plugins.xep_0004.stanza.form import Form
from bcolors import OKGREEN, OKBLUE, WARNING, FAIL, ENDC


class Client(ClientXMPP, threading.Thread):

    print_lock = threading.Lock()

    def __init__(self, jid, password):

        ClientXMPP.__init__(self, jid, password)
        self.auto_authorize = True
        self.auto_subscribe = True
        self.contact_dict = {}
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

        try:
            self.get_roster(block=True)
        except IqError as err:
            print('Error: %s' % err.iq['error']['condition'])
        except IqTimeout:
            print('Error: Request timed out')

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
                        if not jid in self.contact_dict:
                            self.contact_dict[jid] = User(
                                jid, name, show, status, sub)
                        else:
                            self.contact_dict[jid].update_data(status, show)

                # User is not connected, still add him to the dict
                else:
                    if not jid in self.contact_dict:
                        self.contact_dict[jid] = User(
                            jid, name, 'offline', '', sub)

    # Returns a dict jid - User. If it's empty, create it.
    def get_user_dict(self):
        if not self.contact_dict:
            self.create_user_dict()
        return self.contact_dict

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

            if not sender in self.contact_dict:
                self.contact_dict[sender] = User(sender, '', '', '', '')

            self.contact_dict[sender].add_message_to_list(msg['body'])

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
        if self.boundjid.bare != new_presence and new_presence in self.contact_dict:
            self.contact_dict[new_presence].update_data(
                '', presence['type'])

    def presence_message(self, show, status):
        self.send_presence(pshow=show, pstatus=status)

    def send_session_message(self, recipient, message):
        print('sending a message to', recipient)
        print('from', self.boundjid.full)
        self.send_message(
            mto=recipient,
            mbody=message,
            mtype='chat',
            mfrom=self.boundjid.bare)
        if recipient in self.contact_dict:
            self.contact_dict[recipient].clean_unread_messages()

    def join_room(self, room, nick):
        self.plugin['xep_0045'].joinMUC(
            room,
            nick,
            pstatus='Hello world!',
            pfrom=self.boundjid.full,
            wait=True)

    def create_new_room(self, room, nick):
        self.plugin['xep_0045'].joinMUC(
            room,
            nick,
            pstatus='Hello world!',
            pfrom=self.boundjid.full,
            wait=True)

        self.plugin['xep_0045'].setAffiliation(
            room, self.boundjid.full, affiliation='owner')

        self.plugin['xep_0045'].configureRoom(room, ifrom=self.boundjid.full)

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

    def get_all_online(self):

        iq = self.Iq()

        iq.set_from(self.boundjid.full)
        iq.set_to('search.'+self.boundjid.domain)
        iq.set_type('get')
        iq.set_query('jabber:iq:search')

        resp = iq.send(now=True)

        form = Form()
        form.set_type('submit')
        
        # FORM TYPE
        form.add_field(
            var='FORM_TYPE',
            ftype='hidden',
            type='hidden',
            value='jabber:iq:search'
            )
        
        # SEARCH LABEL
        form.add_field(
            var='search',
            ftype='text-single',
            type='text-single',
            label='Search',
            required=True,
            value='*'
            )
        
        # USERNAME
        form.add_field(
            var='Username',
            ftype='boolean',
            type='boolean',
            label='Username',
            value=1
            )
        
        # NAME 
        form.add_field(
            var='Name',
            ftype='boolean',
            type='boolean',
            label='Name',
            value=1
            )
        
        # EMAIL
        form.add_field(
            var='Email',
            ftype='boolean',
            type='boolean',
            label='Email',
            value=1
            )

        search = self.Iq()
        search.set_type('set')
        search.set_to('search.'+self.boundjid.domain)
        search.set_from(self.boundjid.full)

        query = ET.Element('{jabber:iq:search}query')
        query.append(form.xml)
        search.append(query)
        results = search.send(now=True, block=True)

        root = ET.fromstring(str(results))

        items = []
        for child in root:
            for grandchild in child:
                for grangrandchild in grandchild:
                    items.append(grangrandchild)
        
        for item in items:
            jid = ''
            email = ''
            name = ''
            username = ''

            childrens = item.getchildren()
            
            if len(childrens) > 0:
                
                for field in childrens:
                    try:
                        child = field.getchildren()[0]
                    except:
                        continue

                    if field.attrib['var'] == 'Email':
                        email = child.text if child.text else '---'

                    elif field.attrib['var'] == 'jid':
                        jid = child.text if child.text else '---'

                    elif field.attrib['var'] == 'Name':
                        name = child.text if child.text else '---'
                    
                    elif field.attrib['var'] == 'Username':
                        username = child.text if child.text else '---'

                if jid:
                    self.user_dict[jid] = [username, name, email]
        
        return self.user_dict
        


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
        self.subscription = subscription
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
