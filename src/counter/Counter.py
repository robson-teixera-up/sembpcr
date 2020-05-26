from enum import Enum, auto
import requests
from time import sleep

from requests.exceptions import HTTPError
from logzero import logger


SLEEP_S = .1


SERVER = "http://localhost:31231/api/v1.0"
def u(url):
    return SERVER + "/" + url


class ValidateException(Exception):
    pass

class StateException(Exception):
    pass


class CS(Enum):
    UNREGISTERED    = "UNREGISTERED"
    IDLE            = "IDLE"
    WAITING         = "WAITING"
    SERVICING       = "SERVICING"


RE = None
STATE = CS.UNREGISTERED
TOKEN = None
SERVICE = None
NUMBER = None
KNOWN_SERVICES = None



######################
##  Low level I/O   ##
######################

def signal(color, timesec):
    if color not in ["red", "green"]:
        raise ValueError("Can only signal red or green LEDs")
    pass



######################
## Request wrappers ##
######################

def register(services=None):
    '''Register a counter into the server DB'''
    global STATE, TOKEN, RE
    ENDPT = 'register'

    if STATE != CS.UNREGISTERED:
        raise StateException()

    if RE is not None:
        logger.warn("Will register, but session object is already initialized")

    RE = requests.Session()

    req = RE.put(u(ENDPT), json={'services': services})
    req.raise_for_status()


    STATE = CS.IDLE

    logger.info("Registered with services {}".format(services))
    return TOKEN


def services():
    '''Ask the server for available services'''
    global KNOWN_SERVICES
    ENDPT = 'services'

    req = RE.get(u(ENDPT))
    req.raise_for_status()

    KNOWN_SERVICES = req.json()

    logger.info("Asked about services. Available services are: {}".format(KNOWN_SERVICES))
    return KNOWN_SERVICES


def next():
    '''Ask the server to issue us another number'''
    global STATE, SERVICE, NUMBER
    ENDPT = 'next'

    if STATE == CS.UNREGISTERED:
        raise StateException()

    req = RE.put(u(ENDPT), json={'service': SERVICE, 'number': NUMBER})
    req.raise_for_status()

    # Server wants us to idle
    if req.status_code == 204:
        STATE = CS.IDLE
        return

    resp = req.json()
    SERVICE = resp['service']
    NUMBER = resp['number']
    STATE = CS.WAITING

    logger.info("Now waiting for ticket {} in service {}".format(NUMBER, SERVICE))
    return (SERVICE, NUMBER)

def service(new_service, new_number, new_val_code):
    '''Ask the server to let us service a client who showed up out of order'''
    global STATE, SERVICE, NUMBER
    ENDPT = 'service'

    if STATE == CS.UNREGISTERED:
        raise StateException()

    req = RE.put(u(ENDPT), json={'service': SERVICE, 'number': NUMBER, \
        'NEW_SERVICE': new_service, 'NEW_NUMBER': new_number, 'NEW_VAL_CODE': new_val_code})
    req.raise_for_status()

    valid = req.json()['valid']
    if not valid:
        raise ValidateException('Invalid code {} for {}'.format(new_val_code, (new_service, new_number)))

    SERVICE = new_service
    NUMBER = new_number
    STATE = CS.SERVICING

    logger.info("Now waiting for out-of-order ticket {} in service {}".format(NUMBER, SERVICE))


def idle():
    '''Ask the server to let us idle'''
    global STATE
    ENDPT = 'idle'

    if STATE == CS.UNREGISTERED:
        raise StateException()

    req = RE.put(u(ENDPT))
    req.raise_for_status()

    logger.info("Successfully asked to idle")
    STATE = CS.IDLE


def validate(val_code):
    '''Ask the server if a client's validation code matches our service,number pair, and begin servicing if yes'''
    global STATE
    ENDPT = 'validate'

    if STATE != CS.WAITING:
        raise StateException()

    req = RE.put(u(ENDPT), json={'service': SERVICE, 'number': NUMBER, 'val_code': val_code})
    req.raise_for_status()

    valid = req.json()['valid']
    if not valid:
        raise ValidateException('Invalid code {} for {}'.format(val_code, (SERVICE, NUMBER)))

    logger.info("Code {} validates for ticket {} in service {}".format(val_code, NUMBER, SERVICE))
    STATE = CS.SERVICING


def askstate():
    '''Ask the server what it thinks our state is'''
    global state
    ENDPT = 'state'

    if STATE == CS.UNREGISTERED:
        raise StateException()

    req = RE.get(u(ENDPT))
    req.raise_for_status()

    serv_state = req.json()

    logger.info("Server thinks our state is {}".format(serv_state))
    return serv_state



######################
##    Main loop     ##
######################

def handleInputKeyboard():
    if STATE == CS.UNREGISTERED:
        print("Register into service:")
    elif STATE == CS.IDLE or STATE == CS.SERVICING:
        print("Press enter to request next number.")
    elif STATE == CS.WAITING:
        print("Enter validation code:")

    cmd = input()

    try:
        if STATE == CS.UNREGISTERED:
            register(services=[cmd])
        elif STATE == CS.IDLE:
            next()
        elif STATE == CS.WAITING:
            validate(int(cmd))
        elif STATE == CS.SERVICING:
            next()
    except HTTPError as e:
        logger.error("HTTP Error: {}".format(e.response.json()))
    except ValidateException as e:
        logger.error(e)

    logger.info("Now in state {}".format(STATE))

def setup():
    register()

handleInput = handleInputKeyboard
def main():
    try:
        register(services=["service1"])
    except HTTPError as e:
        logger.error("HTTP Error: {}".format(e.response.json()))
    while True:
        try:
            #doStuff()
            sleep(SLEEP_S)
        except KeyboardInterrupt:
            handleInput()
    #finalize()

if __name__ == '__main__':
    main()
