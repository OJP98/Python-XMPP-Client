import logging
from getpass import getpass
from argparse import ArgumentParser
import sleekxmpp
from sleekxmpp.exceptions import IqError, IqTimeout


class RegisterBot(sleekxmpp.ClientXMPP):

    def __init__(self, jid, password):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)

        self.add_event_handler("session_start", self.start, threaded=False)
        self.add_event_handler("register", self.register, threaded=False)

    def start(self, event):

        self.send_presence()
        self.get_roster()

        self.disconnect()

    def register(self, iq):

        resp = self.Iq()
        resp['type'] = 'set'
        resp['id'] = 'unreg1'
        # resp['register']['username'] = self.boundjid.user
        # resp['register']['password'] = self.password
        resp['register']['remove'] = True

        # print(resp.values)

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
    # Setup the command line arguments.
    parser = ArgumentParser()

    # Output verbosity options.
    parser.add_argument("-q", "--quiet", help="set logging to ERROR",
                        action="store_const", dest="loglevel",
                        const=logging.ERROR, default=logging.INFO)
    parser.add_argument("-d", "--debug", help="set logging to DEBUG",
                        action="store_const", dest="loglevel",
                        const=logging.DEBUG, default=logging.INFO)

    # JID and password options.
    parser.add_argument("-j", "--jid", dest="jid",
                        help="JID to use")
    parser.add_argument("-p", "--password", dest="password",
                        help="password to use")

    args = parser.parse_args()

    # Setup logging.
    logging.basicConfig(level=args.loglevel,
                        format='%(levelname)-8s %(message)s')

    if args.jid is None:
        args.jid = input("Username: ")
    if args.password is None:
        args.password = getpass("Password: ")

    xmpp = RegisterBot(args.jid, args.password)
    xmpp.register_plugin('xep_0030')  # Service Discovery
    xmpp.register_plugin('xep_0004')  # Data forms
    xmpp.register_plugin('xep_0066')  # Out-of-band Data
    xmpp.register_plugin('xep_0077')  # In-band Registration

    # Some servers don't advertise support for inband registration, even
    # though they allow it. If this applies to your server, use:
    xmpp['xep_0077'].force_registration = True

    # Connect to the XMPP server and start processing XMPP stanzas.
    if xmpp.connect():
        xmpp.process(block=True)
        print("Done")
    else:
        print("Unable to connect.")
