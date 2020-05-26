from enum import Enum
from flask import Flask, make_response, jsonify, request, session
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
GuicheApp.secret_key = "wasp$senile7Wish"

SERVICES = ["service1", "service2"]
COD_VALIDACAO = 102030
TOLERANCIA = 3


class GuicheStates(str, Enum):
    UNREGISTERED = "UNREGISTERED"
    IDLE = "IDLE"
    WAITING = "WAITING"
    SERVICING = "SERVICING"



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


@auth.login_required
@GuicheApp.route('/api/v1.0/services', methods=['GET'])
def get_services():
    global SERVICES

    logger.debug(session["state"])

    return make_json_response({"services": SERVICES}, 200)


@auth.login_required
@GuicheApp.route('/api/v1.0/next', methods=['PUT'])
def put_next():

    inputs = PutNextJsonInputs(request)
    if inputs.validate():
        if request.json["service"] != session["last_service"] or request.json["number"] != session["senha"]:
            logger.debug("{}, {}, {}, {}".format(request.json["service"], session["services"], request.json["number"], session["senha"]))
            return make_json_response({"error": "Conjunto service/number invalido"}, 400)

        if session["state"] == GuicheStates.SERVICING:
            session["state"] = GuicheStates.WAITING
            if session["senha"] is None: session["senha"] = 0
            session["senha"] += 1
            session["last_service"] = session["services"][0]
            return make_json_response({"service": session["services"][0], "number": session["senha"]}, 200)

        elif session["state"] == GuicheStates.IDLE:
            session["state"] = GuicheStates.WAITING
            if session["senha"] is None: session["senha"] = 0
            session["senha"] += 1
            session["last_service"] = session["services"][0]
            return make_json_response({"service": session["services"][0], "number": session["senha"]}, 200)

        else:
            return make_json_response({"error": "Estado incorrecto"}, 400)

    else:
        logger.debug("Validate error: {}".format(inputs.errors))
        return make_json_response({"error": "formato incorrecto"}, 400)


@auth.login_required
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


@auth.login_required
@GuicheApp.route('/api/v1.0/validate', methods=['PUT'])
def put_validate():
    global COD_VALIDACAO

    inputs = PutValidateJsonInputs(request)
    if inputs.validate():
        if session["state"] != GuicheStates.WAITING:
            return make_json_response({"error": "Estado incorrecto"}, 400)

        if request.json["service"] != session["last_service"] or request.json["number"] != session["senha"]:
            return make_json_response({"error": "Informação incorrecta"}, 400)

        elif request.json["val_code"] != COD_VALIDACAO:
            return make_json_response({"valid": False}, 200)
        else:
            session["state"] = GuicheStates.SERVICING
            return make_json_response({"valid": True}, 200)
    else:
        logger.debug("Validate error: {}".format(inputs.errors))
        return make_json_response({"error": "formato incorrecto"}, 400)


@auth.login_required
@GuicheApp.route('/api/v1.0/state', methods=['GET'])
def get_state():
    if session["state"] == GuicheStates.UNREGISTERED:
        return make_json_response({"state": session["state"].value}, 200)
    return make_json_response({"state": session["state"].value, "service": CUR_SERVICE, "number": session["senha"]}, 200)


if __name__ == '__main__':
    GuicheApp.run(debug=True, host="localhost", port=31231)
