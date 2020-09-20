import os
import time
import logging
import getpass
import threading
import base64
import datetime
import mimetypes
from sleekxmpp import ClientXMPP
from sleekxmpp.exceptions import IqError, IqTimeout
from xml.etree import cElementTree as ET
from sleekxmpp.plugins.xep_0004.stanza.field import FormField, FieldOption
from sleekxmpp.plugins.xep_0004.stanza.form import Form
from sleekxmpp.plugins.xep_0047.stream import IBBytestream
from consts import OKGREEN, OKBLUE, WARNING, FAIL, ENDC, BLUE, RED


DIRNAME = os.path.dirname(__file__)

class Client(ClientXMPP):

    def __init__(self, jid, password):

        ClientXMPP.__init__(self, jid, password)
        self.auto_authorize = True
        self.auto_subscribe = True
        self.contact_dict = {}
        self.user_dict = {}
        self.file_received = ''

        # self.add_event_handler('session_start', self.session_start)
        self.add_event_handler('message', self.received_message)
        self.add_event_handler('disconnected', self.got_disconnected)
        self.add_event_handler('failed_auth', self.on_failed_auth)
        self.add_event_handler('presence_subscribed',
                               self.new_presence_subscribed)
        self.add_event_handler("got_offline", self.presence_offline)
        self.add_event_handler("got_online", self.presence_online)
        self.add_event_handler('changed_status', self.wait_for_presences)

        # FILE TRANSFER
        self.add_event_handler('si_request', self.on_si_request)
        self.add_event_handler('ibb_stream_start', self.on_stream_start)
        self.add_event_handler("ibb_stream_data", self.stream_data)
        self.add_event_handler("ibb_stream_end", self.stream_closed)

        self.register_plugin('xep_0030')
        self.register_plugin('xep_0004')
        self.register_plugin('xep_0066')
        self.register_plugin('xep_0077')
        self.register_plugin('xep_0050')
        self.register_plugin('xep_0047')
        self.register_plugin('xep_0231')
        self.register_plugin('xep_0045')
        self.register_plugin('xep_0095')  # Offer and accept a file transfer
        self.register_plugin('xep_0096')  # Request file transfer intermediate
        self.register_plugin('xep_0047')  # Bytestreams

        self['xep_0077'].force_registration = True

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

    # Create a new user dict
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

                        show = 'available'
                        status = ''
                        if pres['show']:
                            show = pres['show']
                        if pres['status']:
                            status = pres['status']

                        # Check if the user is in the dict, else add it
                        if not jid in self.contact_dict:
                            self.contact_dict[jid] = User(
                                jid, name, show, status, sub, username, res)
                        else:
                            self.contact_dict[jid].update_data(
                                status, show, res)

                # User is not connected, still add him to the dict
                else:
                    if not jid in self.contact_dict:
                        self.contact_dict[jid] = User(
                            jid, name, 'unavailable', '', sub, username, '')

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

    # Act upon a received message
    def received_message(self, msg):

        sender = str(msg['from'])
        jid = sender.split('/')[0]
        username = jid.split('@')[0]
        if msg['type'] in ('chat', 'normal'):
            print(f'New message from {jid}')

            if not jid in self.contact_dict:
                self.contact_dict[jid] = User(
                    jid, '', '', '', '', username)

            self.contact_dict[jid].add_message_to_list(msg['body'])

    def request_si(self, user_jid, file_path):

        # Get some  data from the file
        file_name = file_path.split('/')[-1]
        file_size = os.path.getsize(file_path)        
        unix_date = os.path.getmtime(file_path)
        file_date = datetime.datetime.utcfromtimestamp(unix_date).strftime('%Y-%m-%dT%H:%M:%SZ')
        file_mime_type = 'not defined'

        try:
            file_mime_type = str(mimetypes.MimeTypes().guess_type(file_path)[0])
        except:
            pass

        data = None
        # Read the contents of the file and encode it to b64
        with open(file_path, 'rb') as file:
            data = base64.b64encode(file.read()).decode('utf-8')

        # Set the data of the request
        dest = self.contact_dict[user_jid].get_full_jid()
        req = self.plugin['xep_0096'].request_file_transfer(
            jid=dest,
            name=file_name,
            size=file_size,
            mime_type=file_mime_type,
            sid='ibb_file_transfer',
            desc='Envío un archivo con descripción',
            date=file_date
        )

        # Wait for the other user to accept the file transfer
        print(f'{BLUE}Offering a file transfer to the user.{ENDC}')
        time.sleep(2)

        # Open the ibb stream transfer
        stream = self.plugin['xep_0047'].open_stream(
            jid=dest, sid='ibb_file_transfer', ifrom=self.boundjid.full)
          
        # Wait for the other client to get notified about this
        time.sleep(2)

        # Send him all of the encoded data
        stream.sendall(data)

        # Wait for him to process al of it
        time.sleep(2)

        # Finally, close the ibb stream
        stream.close()

    def on_si_request(self, iq):

        # Get sender from the iq
        sender = iq.get_from().user

        # Now, si (where we can get file type)
        payload = iq.get_payload()[0]
        file_type = payload.get('mime-type')
        file_id = payload.get('id')

        # Get file object from payload
        file = payload.getchildren()[0]
        # From this, get name, size and date
        file_name = file.get('name')
        file_size = file.get('size')
        file_date = file.get('date')

        # Check if file has a description
        try:
            desc = file.getchildren()[0]
            desc = desc.text
        except:
            desc = None

        print(f'{RED}================| FILE REQUEST RECEIVED |================{ENDC}')
        print(f'''
        {RED}{sender} is going to send you a file: {ENDC}
            - type: {file_type}
            - name: {file_name}
            - size: {file_size}
            - date: {file_date}
        ''')
        if desc:
            print(f'\t\tDescription: {desc}')
          
        # Create empty file
        dir_path = os.path.join(DIRNAME, 'received_files')
        self.file_received = file_name
        with open(os.path.join(dir_path, file_name), 'w') as fp:
            pass

        # Accept the file requested
        self.plugin['xep_0095'].accept(jid=iq.get_from().full, sid=file_id)

    # Let the user know the file is about to start downloading
    def on_stream_start(self, stream):
        print(f'{BLUE}Started streaming and downloading the file...{ENDC}')

    # Append the recieved data to the file
    def stream_data(self, stream):
        b64_data = stream['data']
        dir_path = os.path.join(DIRNAME, f'received_files/{self.file_received}')

        with open(dir_path, 'ab+') as new_file:
            new_file.write(base64.decodebytes(b64_data))

    # Print messages when file transfer finished
    def stream_closed(self, stream):
        print('{OKGREEN}File transfer completed!{ENDC}')
        print('Stream closed: %s from %s' % (stream.sid, stream.peer_jid))

    # Act when logged out/disconnected
    def got_disconnected(self, event):
        print(f'{OKBLUE}Logged out from the current session{ENDC}')

    # Act when authentication fails
    def on_failed_auth(self, event):
        print(f'{FAIL}Credentials are not correct.{ENDC}')
        self.disconnect()

    # Add a user from his jid
    def add_user(self, jid):
        self.send_presence_subscription(pto=jid,
                                        ptype='subscribe',
                                        pfrom=self.boundjid.bare)

        if not jid in self.contact_dict:
            self.contact_dict[jid] = User(
                jid, '', '', '', '', str(jid.split('@')[0]))
        print(f'{OKBLUE}Subscribed to {jid}!{ENDC}')

    # Search for a user by his username
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

    # Act when a new presence subscribes to you
    def new_presence_subscribed(self, presence):
        print('PRESENCE SUBSCRIBED!')
        print(presence)

    # Delete account from server
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

    # Act when a contact gets offline
    def presence_offline(self, presence):
        new_presence = str(presence['from']).split('/')[0]
        if self.boundjid.bare != new_presence and new_presence in self.contact_dict:
            self.contact_dict[new_presence].update_data(
                '', presence['type'], '')

    # Act when a contact gets online
    def presence_online(self, presence):
        new_presence = str(presence['from']).split('/')[0]
        resource = str(presence['from']).split('/')[1]

        try:
            if self.boundjid.bare != new_presence and new_presence in self.contact_dict:
                self.contact_dict[new_presence].update_data(
                    '', presence['type'], resource)

                # print(
                # f'{BLUE}{new_presence} got online!{ENDC}')
        except:
            pass

    # Send a presence message with its show and status
    def presence_message(self, show, status):
        self.send_presence(pshow=show, pstatus=status)

    # Send a message to someone directly
    def send_session_message(self, recipient, message):
        self.send_message(
            mto=recipient,
            mbody=message,
            mtype='chat',
            mfrom=self.boundjid.bare)
        if recipient in self.contact_dict:
            self.contact_dict[recipient].clean_unread_messages()

        print(f'{OKGREEN} Message sent!{ENDC}')

    # Join an existing room
    def join_room(self, room, nick):
        self.plugin['xep_0045'].joinMUC(
            room,
            nick,
            pstatus='Hello world!',
            pfrom=self.boundjid.full,
            wait=True)

    # Create a new room with its name and nick
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

    # Leave a room
    def leave_room(self, room, nick):
        self.plugin['xep_0045'].leaveMUC(room, nick)

    # Send a message to a room
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

    # Get all online users
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

        # Parse the results so it can be used as an XML tree
        root = ET.fromstring(str(results))
        # Process the XML in a dedicated function
        self.update_user_dict(root)

        # Finally, return all the list of users
        return self.user_dict

    # Update user dictionary (from search)
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
    def __init__(self, jid, name, show, status, subscription, username, resource=None):
        self.jid = jid
        self.name = name
        self.show = show
        self.status = status
        self.subscription = subscription
        self.username = username
        self.resource = resource
        self.messages = []

    def update_data(self, status, show, resource=None):
        self.status = status
        self.show = show
        self.resource = resource

    def get_connection_data(self):
        return [self.username, self.show, self.status, self.subscription]

    def add_message_to_list(self, msg):
        self.messages.append(msg)

    def clean_unread_messages(self):
        self.messages = []

    def get_messages(self):
        return self.messages

    def get_full_jid(self):
        return f'{self.jid}/{self.resource}'

    def get_all_data(self):
        return [self.jid, self.name, self.show, self.status, self.subscription, self.username]
