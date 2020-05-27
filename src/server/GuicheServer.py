from enum import Enum
from flask import Flask, make_response, jsonify, request, session
from flask_httpauth import HTTPTokenAuth
from JsonValidate import PutNextJsonInputs, PutRegisterJsonInputs, PutServiceJsonInputs, PutValidateJsonInputs
from logzero import logger
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from random import randint
from uuid import uuid4
from datetime import datetime

# TODO
# Converter de flask para Quart
# Base de dados
# Gestão de status das senhas
#
# pedido register:
#   - registar em multiplos serviços
#
# pedido next:
#   - verificar condições para status 204
#   - verificar timeout
#
# pedido service:
#   - verificar timeout
#
#


GuicheApp = Flask(__name__)

GuicheApp.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///FilaDeEspera.db'
db = SQLAlchemy(GuicheApp)
GuicheApp.secret_key = "wasp$senile7Wish"

SERVICES = ["service1", "service2"]
COD_VALIDACAO = 102030
TOLERANCIA = 3
TIMEOUT_SEC = 60

N_DIGITS_VAL_CODE = 5

def make_json_response(dict_obj, status):
    return make_response(jsonify(dict_obj), status)

def getRandDigits(n):
    return randint(10**(n-1), 10**(n) - 1)

######################
##    DB models     ##
######################

class Ticket(db.Model):
    number = db.Column(db.Integer, primary_key=True)
    service = db.Column(db.Integer, primary_key=True)
    val_code = db.Column(db.Integer, nullable=False)
    cid = db.Column(db.String(36), nullable=False)
    hid = db.Column(db.String(20))
    date_called = db.Column(db.DateTime)


db.create_all()
######################
##     DB manip     ##
######################


def mk_ticket(service, cid, hid):
    '''Makes a new ticket.
    service: numerical service code
    cid: counter id
    hid: (client) hardware id
    '''
    ## Get our max number and commit
    try:
        num = db.session.query(func.max(Ticket.number)).filter_by(service=service).first()[0]

        if num is None: num = 0
        num += 1
        val_code = getRandDigits(N_DIGITS_VAL_CODE)
        ticket = Ticket(number=num, service=service, val_code=val_code, cid=cid, hid=hid)
        db.session.add(ticket)


        db.session.commit()
        logger.debug("Making new ticket for service {} (number {}, validation code {}, hardware id {})".format(service, num, val_code, hid))
        return (num, val_code)
    except:
        db.session.rollback()
        raise

def call_ticket(service, number):
    '''Calls a ticket (sets up date_called'''
    ticket = Ticket.query.filter_by(service=service, number=number).first()
    t = datetime.now()
    logger.debug("Calling {} at {}".format((service,number), t))
    ticket.date_called = t
    db.session.commit()

def get_ticket_timedelta(service, number):
    '''Returns number of seconds elapsed since ticket was called,
    or -1 if ticket doesn't exist
    '''
    ticket = Ticket.query.filter_by(service=service, number=number).first()
    if not ticket: return -1

    return (datetime.now()-ticket.date_called).seconds


def val_ticket(service, number, cid, val_code):
    '''Validates a ticket against a validation code.
    service: numerical service code
    number: ticket number
    cid: requesting counter id
    val_code: code to validate against

    returns a tuple (STATUS_JSON, RESP_CODE)
    '''
    # cid might be UUID and not str
    cid = str(cid)

    ticket = Ticket.query.filter_by(service=service, number=number).first()


    if not ticket:
        return ({"error": "no such ticket"}, 404)
    elif ticket.cid != cid:
        return ({"error": "ticket not assigned to this counter"}, 400)
    elif (datetime.now()-ticket.date_called).seconds > TIMEOUT_SEC:
        return ({"error": "ticket timed out"}, 403)
    valid = val_code == ticket.val_code

    return ({"valid": valid}, 200)




######################
##  Counter logic   ##
######################

class GuicheStates(str, Enum):
    UNREGISTERED = "UNREGISTERED"
    IDLE = "IDLE"
    WAITING = "WAITING"
    SERVICING = "SERVICING"


@GuicheApp.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@GuicheApp.route('/api/v1.0/register', methods=['PUT'])
def put_register():
    global SERVICES

    logger.debug("Guiche has state: {}".format("state" in session))
    inputs = PutRegisterJsonInputs(request)
    if inputs.validate():
        if "state" not in session:
            if len(request.json["services"]):
                if not any(ser not in SERVICES for ser in request.json["services"]):
                    session["state"] = GuicheStates.IDLE
                    logger.debug("Guiche state:" + session["state"].value)
                    session["services"] = request.json["services"]
                    session["senha"] = None
                    session["last_service"] = None
                    session["cid"] = uuid4()
                    return make_json_response({"success": "success"}, 200)
                else:
                    logger.debug(request.json["services"] + "Serviço invalido")
                    return make_json_response({"error": "Serviço invalido"}, 400)
            else:
                return make_json_response({"error": "Deve se registar em pelo menos um serviço"}, 409)
        return make_json_response({"error": "Estado incorrecto"}, 400)
    else:
        logger.debug("Validate error: {}".format(inputs.errors))
        return make_json_response({"error": "formato incorrecto"}, 400)


@GuicheApp.route('/api/v1.0/services', methods=['GET'])
def get_services():
    global SERVICES

    logger.debug(session["state"])

    return make_json_response({"services": SERVICES}, 200)


@GuicheApp.route('/api/v1.0/next', methods=['PUT'])
def put_next():

    inputs = PutNextJsonInputs(request)
    if inputs.validate():
        # Sanity check
        if request.json["service"] != session["last_service"] or request.json["number"] != session["senha"]:
            logger.debug("{}, {}, {}, {}".format(request.json["service"], session["services"], request.json["number"], session["senha"]))
            return make_json_response({"error": "Conjunto service/number invalido"}, 400)

        if session["state"] == GuicheStates.SERVICING or session["state"] == GuicheStates.IDLE or session["state"] == GuicheStates.WAITING:

            # Have we timed out yet?
            if session["state"] == GuicheStates.WAITING:
                delta = get_ticket_timedelta(session["last_service"], session["senha"])
                if delta <= TIMEOUT_SEC:
                    return make_json_response({"error": "Ticket was issued {}s ago; cannot reissue for {}s"
                            .format(delta, TIMEOUT_SEC-delta)}, 400)

            session["senha"], _ = mk_ticket(0, str(session['cid']), None)
            call_ticket(0, session["senha"])
            session["last_service"] = 0
            session["state"] = GuicheStates.WAITING
            return make_json_response({"service": 0, "number": session["senha"]}, 200)

        # Bad State
        else:
            return make_json_response({"error": "Estado incorrecto"}, 400)

    else:
        logger.debug("Validate error: {}".format(inputs.errors))
        return make_json_response({"error": "formato incorrecto"}, 400)


@GuicheApp.route('/api/v1.0/service', methods=['PUT'])
def put_service():
    global COD_VALIDACAO
    global SERVICES
    global TOLERANCIA

    inputs = PutServiceJsonInputs(request)
    if inputs.validate():
        if request.json["service"] != session["last_service"] or request.json["number"] != session["senha"]:
            return make_json_response({"error": "Pedido invalido"}, 400)
        elif request.json["new_service"] not in SERVICES:
            return make_json_response({"error": "Serviço desconhecido"}, 400)
        elif session["senha"] < request.json["new_number"]:
            return make_json_response({"error": "new_number deve ser inferior à senha actual"}, 403)
        elif session["senha"] - request.json["new_number"] > TOLERANCIA:
            return make_json_response({"error": "tolerancia ultrapassada"}, 403)
        elif request.json["new_val_code"] != COD_VALIDACAO:
            return make_json_response({"valid": False}, 200)
        else:
            session["senha"] = request.json["new_number"]
            session["last_service"] = request.json["new_service"]
            session["state"] = GuicheStates.SERVICING
            return make_json_response({"valid": True}, 200)
    else:
        return make_json_response({"error": "formato incorrecto"}, 400)


@GuicheApp.route('/api/v1.0/validate', methods=['PUT'])
def put_validate():
    global COD_VALIDACAO

    inputs = PutValidateJsonInputs(request)
    if inputs.validate():
        if session["state"] != GuicheStates.WAITING:
            return make_json_response({"error": "Estado incorrecto"}, 400)

        if request.json["service"] != session["last_service"] or request.json["number"] != session["senha"]:
            return make_json_response({"error": "Informação incorrecta"}, 400)

        msg, code = val_ticket(request.json["service"], request.json["number"], session["cid"], request.json["val_code"])

        if code == 200 and msg["valid"]:
            logger.debug("Ticket {} validates against {}"
                .format((request.json["service"], request.json["number"]), request.json["val_code"]))
            session["state"] = GuicheStates.SERVICING

        return make_json_response(msg, code)
    else:
        logger.debug("Validate error: {}".format(inputs.errors))
        return make_json_response({"error": "formato incorrecto"}, 400)


@GuicheApp.route('/api/v1.0/state', methods=['GET'])
def get_state():
    if session["state"] == GuicheStates.UNREGISTERED:
        return make_json_response({"state": session["state"].value}, 200)
    return make_json_response({"state": session["state"].value, "service": CUR_SERVICE, "number": session["senha"]}, 200)


if __name__ == '__main__':
    GuicheApp.run(debug=True, host="localhost", port=31231)
