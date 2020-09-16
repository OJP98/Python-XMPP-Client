import time
import logging
import getpass
import threading
from sleekxmpp import ClientXMPP
from sleekxmpp.exceptions import IqError, IqTimeout
from xml.etree import cElementTree as ET
from sleekxmpp.plugins.xep_0004.stanza.field import FormField, FieldOption
from sleekxmpp.plugins.xep_0004.stanza.form import Form
from bcolors import OKGREEN, OKBLUE, WARNING, FAIL, ENDC, BLUE


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
        self.add_event_handler("got_online", self.presence_online)
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
                username = str(jid.split('@')[0])
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
                                jid, name, show, status, sub, username)
                        else:
                            self.contact_dict[jid].update_data(status, show)

                # User is not connected, still add him to the dict
                else:
                    if not jid in self.contact_dict:
                        self.contact_dict[jid] = User(
                            jid, name, 'unavailable', '', sub, username)

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
        username = sender.split('/')[0]
        if msg['type'] in ('chat', 'normal'):
            print(f'New message from {username}')

            if not sender in self.contact_dict:
                self.contact_dict[sender] = User(
                    sender, '', '', '', '', username)

            self.contact_dict[sender].add_message_to_list(msg['body'])

    def send_bob(self):
        # TODO
        print('send')

    def got_disconnected(self, event):
        print(f'{OKBLUE}Logged out from the current session{ENDC}')

    def on_failed_auth(self, event):
        print(f'{FAIL}Credentials are not correct.{ENDC}')
        self.disconnect()

    def add_user(self, jid):
        self.send_presence_subscription(pto=jid,
                                        ptype='subscribe',
                                        pfrom=self.boundjid.bare)

        if not jid in self.contact_dict:
            self.contact_dict[jid] = User(
                jid, '', '', '', '', str(jid.split('@')[0]))
        print(f'{OKBLUE}Subscribed to {jid}!{ENDC}')

    def get_user_data(self, username):
        # Create the user search IQ
        iq = self.Iq()
        iq.set_from(self.boundjid.full)
        iq.set_to('search.'+self.boundjid.domain)
        iq.set_type('get')
        iq.set_query('jabber:iq:search')

        # Send it and expect a form as an answer
        iq.send(now=True)

        # Create a new form response
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
            value=username
        )

        # USERNAME
        form.add_field(
            var='Username',
            ftype='boolean',
            type='boolean',
            label='Username',
            value=1
        )

        # Create the next IQ, which will contain the form
        search = self.Iq()
        search.set_type('set')
        search.set_to('search.'+self.boundjid.domain)
        search.set_from(self.boundjid.full)

        # Create the search query
        query = ET.Element('{jabber:iq:search}query')
        # Append the form to the query
        query.append(form.xml)
        # Append the query to the IQ
        search.append(query)
        # Send de IQ and get the results
        results = search.send(now=True, block=True)

        res_values = results.findall('.//{jabber:x:data}value')

        amount = 0
        for value in res_values:
            if value.text:
                if '@' in value.text:
                    amount += 1

        if not res_values:
            return False, amount

        return [value.text if value.text else 'N/A' for value in res_values], amount

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

    def presence_online(self, presence):
        new_presence = str(presence['from']).split('/')[0]

        try:
            if self.boundjid.bare != new_presence and new_presence in self.contact_dict:
                self.contact_dict[new_presence].update_data(
                    '', presence['type'])

                # print(
                # f'{BLUE}{new_presence} got online!{ENDC}')
        except:
            pass

    def presence_message(self, show, status):
        self.send_presence(pshow=show, pstatus=status)

    def send_session_message(self, recipient, message):
        self.send_message(
            mto=recipient,
            mbody=message,
            mtype='chat',
            mfrom=self.boundjid.bare)
        if recipient in self.contact_dict:
            self.contact_dict[recipient].clean_unread_messages()

        print(f'{OKGREEN} Message sent!{ENDC}')

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

        # Create the user search IQ
        iq = self.Iq()
        iq.set_from(self.boundjid.full)
        iq.set_to('search.'+self.boundjid.domain)
        iq.set_type('get')
        iq.set_query('jabber:iq:search')

        # Send it and expect a form as an answer
        iq.send(now=True)

        # Create a new form response
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

        # Create the next IQ, which will contain the form
        search = self.Iq()
        search.set_type('set')
        search.set_to('search.'+self.boundjid.domain)
        search.set_from(self.boundjid.full)

        # Create the search query
        query = ET.Element('{jabber:iq:search}query')
        # Append the form to the query
        query.append(form.xml)
        # Append the query to the IQ
        search.append(query)
        # Send de IQ and get the results
        results = search.send(now=True, block=True)

        for i in results.findall('.//{jabber:x:data}value'):
            if i.text:
                print(i.text)

        # Parse the results so it can be used as an XML tree
        # root = ET.fromstring(str(results))
        # Process the XML in a dedicated function
        # self.update_user_dict(root)

        # Finally, return all the list of users
        return self.user_dict

    def update_user_dict(self, xmlObject):
        # Items to be iterated
        items = []

        # Append all the <item> tags
        for child in xmlObject:
            for node in child:
                for item in node:
                    items.append(item)

        # iterate through the tags
        for item in items:
            jid = ''
            email = ''
            name = ''
            username = ''

            # Get all the children of the <item> tag
            childrens = item.getchildren()

            if len(childrens) > 0:

                # Try to get al the fields of the item tag
                for field in childrens:
                    # Check if <field> has children
                    try:
                        child = field.getchildren()[0]
                    except:
                        continue

                    # Get all the different data inside the <field><value> tag
                    if field.attrib['var'] == 'Email':
                        email = child.text if child.text else '---'

                    elif field.attrib['var'] == 'jid':
                        jid = child.text if child.text else '---'

                    elif field.attrib['var'] == 'Name':
                        name = child.text if child.text else '---'

                    elif field.attrib['var'] == 'Username':
                        username = child.text if child.text else '---'

                # Append the jid to the dictionary
                if jid:
                    self.user_dict[jid] = [username, name, email]


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
    def __init__(self, jid, name, show, status, subscription, username):
        self.jid = jid
        self.name = name
        self.show = show
        self.status = status
        self.subscription = subscription
        self.username = username
        self.messages = []

    def update_data(self, status, show):
        self.status = status
        self.show = show

    def get_connection_data(self):
        return [self.username, self.show, self.status]

    def add_message_to_list(self, msg):
        self.messages.append(msg)

    def clean_unread_messages(self):
        self.messages = []

    def get_messages(self):
        return self.messages

    def get_all_data(self):
        return [self.jid, self.name, self.show, self.status, self.subscription, self.username]
