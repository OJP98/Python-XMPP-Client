import sleekxmpp
import getpass


class ReadOnlyBot(sleekxmpp.ClientXMPP):
    def __init__(self, jid, password):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)

        # self.auto_authorize = True
        # self.auto_subscribe = True
        self.add_event_handler('session_start', self.start)
        self.add_event_handler('message', self.received_message)
        self.add_event_handler("presence_subscribe",
                               self.new_presence_subscribe)

    def start(self, event):
        self.send_presence()
        self.get_roster()

    def received_message(self, msg):

        print('IVE RECEIVED SOMETHING')
        print(msg)

        if msg['type'] in ('chat', 'normal'):
            print("Thanks for sending\n%(body)s" % msg)
            # msg.reply("Thanks for sending\n%(body)s" % msg).send()
            self.disconnect(wait=True)

    def new_presence_subscribe(self, presence):
        print(presence)
        self.send_presence_subscription(pto='jua17315@redes2020.xyz',
                                        pfrom='testing2@redes2020.xyz',
                                        ptype='subscribed')


if __name__ == '__main__':
    # username = input('Username: ')
    # password = getpass.getpass('Password: ')
    username = 'testing2@redes2020.xyz'
    password = 'testing2'

    xmpp = ReadOnlyBot(username, password)
    xmpp.register_plugin('xep_0030')  # Service Discovery
    xmpp.register_plugin('xep_0004')  # Data Forms
    xmpp.register_plugin('xep_0060')  # PubSub
    xmpp.register_plugin('xep_0199')  # XMPP Ping

    xmpp.connect()
    xmpp.process(block=True)
