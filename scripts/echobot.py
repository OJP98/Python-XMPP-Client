import time
import logging
import getpass
from sleekxmpp import ClientXMPP
from sleekxmpp.exceptions import IqError, IqTimeout


class Client(ClientXMPP):

    def __init__(self, jid, password):
        ClientXMPP.__init__(self, jid, password)

        # self.auto_authorize = True
        # self.auto_subscribe = True
        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("message", self.message)
        self.add_event_handler("disconnected", self.got_disconnected)
        self.add_event_handler("failed_auth", self.on_failed_auth)
        self.add_event_handler("presence_subscribed",
                               self.new_presence_subscribed)
        # self.add_event_handler("changed_status", self.wait_for_presences)

        # self.received = set()
        # self.presences_received = threading.Event()

    def session_start(self, event):

        print('AUTHENTICATION SUCCESS')

        try:
            self.get_roster()
        except IqError as err:
            print('Error: %s' % err.iq['error']['condition'])
        except IqTimeout:
            print('Error: Request timed out')
            self.disconnect()

        self.send_presence()

        self.add_user('')

        # time.sleep(10)
        # self.disconnect()

    def message(self, msg):
        if msg['type'] in ('chat', 'normal'):
            print('New message: ', msg)
            msg.reply("Thanks for sending\n%(body)s" % msg).send()

    def got_disconnected(self, event):
        print('BYE BYE!')

    def on_failed_auth(self, event):
        print('CREDENTIALS ARE NOT CORRECT')
        self.disconnect()

    def add_user(self, username):
        self.send_presence_subscription(pto='sebdev@redes2020.xyz',
                                        ptype='subscribe',
                                        pfrom='jua17315@redes2020.xyz')
        # self.disconnect()

    def new_presence_subscribed(self, presence):
        print('PRESENCE SUBSCRIBED!')
        print(presence)

    def unregister_account(self):
        resp = self.Iq()
        resp['type'] = 'set'
        resp['from'] = self.boundjid.full
        resp['register']['remove'] = True

        try:
            resp.send(now=True)
            logging.info("Account unregistered for %s!" % self.boundjid)
        except IqError as e:
            logging.error("Could not unregister account: %s" %
                          e.iq['error']['text'])
            self.disconnect()
        except IqTimeout:
            logging.error("No response from server.")
            self.disconnect()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)-8s %(message)s')

    # password = getpass.getpass('Password: ')
    xmpp = Client('jua17315@redes2020.xyz', 'jua17315')
    if xmpp.connect():
        xmpp.process(block=True)
    else:
        print('Unable to connect.')
