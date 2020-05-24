from enum import Enum, auto
import requests as re
from time import sleep


SLEEP_S = .1


SERVER = "http://localhost:31231"

def u(url):
    return SERVER + "/" + url


class ValidateException(Exception):
    pass

class StateException(Exception):
    pass


class CS(Enum):
    UNREGISTERED    = auto()
    IDLE            = auto()
    WAITING         = auto()
    SERVICING       = auto()


STATE = CS.UNREGISTERED
TOKEN = None
SERVICE = None
NUMBER = None
KNOWN_SERVICES = None



######################
## Request wrappers ##
######################

def register(services=None):
    '''Register a counter into the server DB'''
    ENDPT = 'register'

    if STATE != CS.UNREGISTERED:
        raise StateException()

    req = re.put(u(ENDPT), json=services)
    req.raise_for_status()


    TOKEN = req.json()['token']

    return TOKEN


def services():
    '''Ask the server for available services'''
    ENDPT = 'services'

    req = re.get(u(ENDPT))
    req.raise_for_status()

    KNOWN_SERVICES = req.json()

    return KNOWN_SERVICES


def next():
    '''Ask the server to issue us another number'''
    ENDPT = 'next'

    if state == CS.UNREGISTERED:
        raise StateException()

    req = re.put(u(ENDPT), json={'service': SERVICE, 'number': NUMBER})
    req.raise_for_status()

    # Server wants us to idle
    if req.status_code == 204:
        STATE = CS.IDLE
        return

    resp = req.json()
    SERVICE = resp['service']
    NUMBER = resp['number']
    STATE = CS.WAITING

    return (SERVICE, NUMBER)

def service(new_service, new_number, new_val_code):
    '''Ask the server to let us service a client who showed up out of order'''
    ENDPT = 'service'

    if state == CS.UNREGISTERED:
        raise StateException()

    req = re.put(u(ENDPT), json={'service': SERVICE, 'number': NUMBER, \
        'NEW_SERVICE': new_service, 'NEW_NUMBER': new_number, 'NEW_VAL_CODE': new_val_code})
    req.raise_for_status()

    valid = req.json()['valid']
    if not valid:
        raise ValidateException('Invalid code {} for {}'.format(new_val_code, (new_service, new_number)))

    SERVICE = new_service
    NUMBER = new_number
    STATE = CS.SERVICING


def idle():
    '''Ask the server to let us idle'''
    ENDPT = 'idle'

    if state == CS.UNREGISTERED:
        raise StateException()

    req = re.put(u(ENDPT))
    req.raise_for_status()

    STATE = CS.IDLE


def validate(val_code):
    '''Ask the server if a client's validation code matches our service,number pair, and begin servicing if yes'''
    ENDPT = 'validate'

    if state != CS.WAITING:
        raise StateException()

    req = re.put(u(ENDPT), json={'service': SERVICE, 'number': NUMBER, 'val_code': val_code})
    req.raise_for_status()

    valid = req.json()['valid']
    if not valid:
        raise ValidateException('Invalid code {} for {}'.format(new_val_code, (new_service, new_number)))

    STATE = CS.SERVICING


def state():
    '''Ask the server what it thinks our state is'''
    ENDPT = 'state'

    if state == CS.UNREGISTERED:
        raise StateException()

    req = re.get(u(ENDPT))
    req.raise_for_status()

    return req.json()



######################
##    Main loop     ##
######################

def setup():
    register()

def main():
    #setup()
    while True:
        #doStuff()
        sleep(SLEEP_S)
    #finalize()

if __name__ == '__main__':
    main()
