from flask_inputs import Inputs
from flask_inputs.validators import JsonSchema


def put_register_valid_schema():
    return {'type': 'object',
            'properties': {
                'services': {'type': 'array',
                             'items': {
                                 'type': 'string'
                             }}
            },
            "required": ["services"]}


class PutRegisterJsonInputs(Inputs):
    json = [JsonSchema(schema=put_register_valid_schema())]


def put_next_valid_schema():
    return {'type': 'object',
            'properties': {
                'service': {'type': ['integer', 'null']},
                'number': {'type': ['integer', 'null']},
            },
            "required": ["service", "number"]}


class PutNextJsonInputs(Inputs):
    json = [JsonSchema(schema=put_next_valid_schema())]


def put_service_valid_schema():
    return {'type': 'object',
            'properties': {
                'service': {'type': 'integer'},
                'number': {'type': 'integer'},
                'new_service': {'type': 'integer'},
                'new_number': {'type': 'integer'},
                'new_val_code': {'type': 'integer'},
            },
            "required": ["service", "number", 'new_service', 'new_number', 'new_val_code']}


class PutServiceJsonInputs(Inputs):
    json = [JsonSchema(schema=put_service_valid_schema())]


def put_validate_valid_schema():
    return {'type': 'object',
            'properties': {
                'service': {'type': 'integer'},
                'number': {'type': 'integer'},
                'val_code': {'type': 'integer'}
            },
            "required": ["service", "number", "val_code"]}


class PutValidateJsonInputs(Inputs):
    json = [JsonSchema(schema=put_validate_valid_schema())]
