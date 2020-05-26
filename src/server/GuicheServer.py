from enum import Enum
from flask import Flask, make_response, jsonify, request
from flask_httpauth import HTTPTokenAuth
from JsonValidate import PutNextJsonInputs, PutRegisterJsonInputs, PutServiceJsonInputs, PutValidateJsonInputs
from logzero import logger
from Models import db

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
db.init_app(GuicheApp)
auth = HTTPTokenAuth(scheme='Bearer')

TOKENS = {
    "secret-token-1": "sadhasgdjgasjd",
}

SERVICES = ["service1", "service2"]
SENHA = None
CUR_SERVICES = None
LAST_SERVICE = None
COD_VALIDACAO = 102030
TOLERANCIA = 3


class GuicheStates(Enum):
    UNREGISTERED = "UNREGISTERED"
    IDLE = "IDLE"
    WAITING = "WAITING"
    SERVICING = "SERVICING"


GUICHE_STATE = GuicheStates.UNREGISTERED


@auth.verify_token
def verify_token(token):
    if token in TOKENS:
        return TOKENS[token]


@GuicheApp.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


def make_json_response(dict_obj, status):
    return make_response(jsonify(dict_obj), status)


@GuicheApp.route('/api/v1.0/register', methods=['PUT'])
def put_register():
    global GUICHE_STATE
    global SERVICES
    global CUR_SERVICES
    global TOKENS

    logger.debug("Guiche state:" + GUICHE_STATE.value)
    inputs = PutRegisterJsonInputs(request)
    if inputs.validate():
        if GUICHE_STATE == GuicheStates.UNREGISTERED:
            if len(request.json["services"]):
                if not any(ser not in SERVICES for ser in request.json["services"]):
                    GUICHE_STATE = GuicheStates.IDLE
                    logger.debug("Guiche state:" + GUICHE_STATE.value)
                    CUR_SERVICES = request.json["services"]
                    return make_json_response({"token": TOKENS["secret-token-1"]}, 200)
                else:
                    logger.debug(request.json["services"] + "Serviço invalido")
                    return make_json_response({"error": "Serviço invalido"}, 400)
            else:
                return make_json_response({"error": "Deve se registar em pelo menos um serviço"}, 409)
        return make_json_response({"error": "Estado incorrecto"}, 400)
    else:
        logger.debug("Validate error: {}".format(inputs.errors))
        return make_json_response({"error": "formato incorrecto"}, 400)


@auth.login_required
@GuicheApp.route('/api/v1.0/services', methods=['GET'])
def get_services():
    global SERVICES
    global GUICHE_STATE

    logger.debug(GUICHE_STATE)

    return make_json_response({"services": SERVICES}, 200)


@auth.login_required
@GuicheApp.route('/api/v1.0/next', methods=['PUT'])
def put_next():
    global GUICHE_STATE
    global SENHA
    global CUR_SERVICES
    global LAST_SERVICE

    inputs = PutNextJsonInputs(request)
    if inputs.validate():
        if request.json["service"] != LAST_SERVICE or request.json["number"] != SENHA:
            logger.debug("{}, {}, {}, {}".format(request.json["service"], CUR_SERVICES, request.json["number"], SENHA))
            return make_json_response({"error": "Conjunto service/number invalido"}, 400)

        if GUICHE_STATE == GuicheStates.SERVICING:
            GUICHE_STATE = GuicheStates.WAITING
            if SENHA is None: SENHA = 0
            SENHA += 1
            LAST_SERVICE = CUR_SERVICES[0]
            return make_json_response({"service": CUR_SERVICES[0], "number": SENHA}, 200)

        elif GUICHE_STATE == GuicheStates.IDLE:
            GUICHE_STATE = GuicheStates.WAITING
            if SENHA is None: SENHA = 0
            SENHA += 1
            LAST_SERVICE = CUR_SERVICES[0]
            return make_json_response({"service": CUR_SERVICES[0], "number": SENHA}, 200)

        else:
            return make_json_response({"error": "Estado incorrecto"}, 400)

    else:
        logger.debug("Validate error: {}".format(inputs.errors))
        return make_json_response({"error": "formato incorrecto"}, 400)


@auth.login_required
@GuicheApp.route('/api/v1.0/service', methods=['PUT'])
def put_service():
    global GUICHE_STATE
    global SENHA
    global COD_VALIDACAO
    global SERVICES
    global TOLERANCIA
    global CUR_SERVICES
    global LAST_SERVICE

    inputs = PutServiceJsonInputs(request)
    if inputs.validate():
        if request.json["service"] != LAST_SERVICE or request.json["number"] != SENHA:
            return make_json_response({"error": "Pedido invalido"}, 400)
        elif request.json["new_service"] not in SERVICES:
            return make_json_response({"error": "Serviço desconhecido"}, 400)
        elif SENHA < request.json["new_number"]:
            return make_json_response({"error": "new_number deve ser inferior à senha actual"}, 403)
        elif SENHA - request.json["new_number"] > TOLERANCIA:
            return make_json_response({"error": "tolerancia ultrapassada"}, 403)
        elif request.json["new_val_code"] != COD_VALIDACAO:
            return make_json_response({"valid": False}, 200)
        else:
            SENHA = request.json["new_number"]
            LAST_SERVICE = request.json["new_service"]
            GUICHE_STATE = GuicheStates.SERVICING
            return make_json_response({"valid": True}, 200)
    else:
        return make_json_response({"error": "formato incorrecto"}, 400)


@auth.login_required
@GuicheApp.route('/api/v1.0/validate', methods=['PUT'])
def put_validate():
    global GUICHE_STATE
    global SENHA
    global COD_VALIDACAO
    global CUR_SERVICES
    global LAST_SERVICE

    inputs = PutValidateJsonInputs(request)
    if inputs.validate():
        if GUICHE_STATE != GuicheStates.WAITING:
            return make_json_response({"error": "Estado incorrecto"}, 400)

        if request.json["service"] != LAST_SERVICE or request.json["number"] != SENHA:
            return make_json_response({"error": "Informação incorrecta"}, 400)

        elif request.json["val_code"] != COD_VALIDACAO:
            return make_json_response({"valid": False}, 200)
        else:
            GUICHE_STATE = GuicheStates.SERVICING
            return make_json_response({"valid": True}, 200)
    else:
        logger.debug("Validate error: {}".format(inputs.errors))
        return make_json_response({"error": "formato incorrecto"}, 400)


@auth.login_required
@GuicheApp.route('/api/v1.0/state', methods=['GET'])
def get_state():
    global GUICHE_STATE
    global SENHA
    global CUR_SERVICES

    if GUICHE_STATE == GuicheStates.UNREGISTERED:
        return make_json_response({"state": GUICHE_STATE.value}, 200)
    return make_json_response({"state": GUICHE_STATE.value, "service": CUR_SERVICE, "number": SENHA}, 200)


if __name__ == '__main__':
    GuicheApp.run(debug=True, host="localhost", port=31231)
