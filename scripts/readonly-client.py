import sleekxmpp
import getpass


class ReadOnlyBot(sleekxmpp.ClientXMPP):
    def __init__(self, jid, password):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)

        self.add_event_handler('session_start', self.start)
        self.add_event_handler('message', self.received_message)

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


if __name__ == '__main__':
    username = input('Username: ')
    password = getpass.getpass('Password: ')

    xmpp = ReadOnlyBot(username, password)
    xmpp.register_plugin('xep_0030')  # Service Discovery
    xmpp.register_plugin('xep_0004')  # Data Forms
    xmpp.register_plugin('xep_0060')  # PubSub
    xmpp.register_plugin('xep_0199')  # XMPP Ping

    xmpp.connect()
    xmpp.process(block=True)
