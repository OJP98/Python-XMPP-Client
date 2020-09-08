from bcolors import OKGREEN, OKBLUE, WARNING, FAIL
from scripts.register import RegisterBot
from scripts.unregister import Registration, UnregisterBot
import sleekxmpp


def Register(username=None, password=None):
    if not username or not password:
        return False
    else:
        xmpp = RegisterBot(username, password)
        xmpp.register_plugin('xep_0030')  # Service Discovery
        xmpp.register_plugin('xep_0004')  # Data forms
        xmpp.register_plugin('xep_0066')  # Out-of-band Data
        xmpp.register_plugin('xep_0077')  # In-band Registration
        xmpp['xep_0077'].force_registration = True

        if xmpp.connect():
            xmpp.process(block=True)
            print("Done")
        else:
            print("Unable to connect.")
        return True


def Unregister(username='testing2@redes2020.xyz', password='testing2'):
    query = Registration()
    query.setRemove(True)
    query.setUsername(username)
    print(query.values)
    return True
    # xmpp = UnregisterBot(username, password)
    # xmpp.register_plugin('xep_0030')  # Service Discovery
    # xmpp.register_plugin('xep_0004')  # Data forms
    # xmpp.register_plugin('xep_0066')  # Out-of-band Data
    # xmpp.register_plugin('xep_0077')  # In-band Registration
    # xmpp['xep_0077'].force_registration = True

    # if xmpp.connect():
    #     xmpp.process(block=True)
    #     print("Done")
    # else:
    #     print("Unable to connect.")
    # return True
