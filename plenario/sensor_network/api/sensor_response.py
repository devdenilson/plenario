import json

from flask import make_response, request

from plenario.api.common import unknown_object_json_handler


def make_error(msg, status_code):
    resp = {
        'meta': {
        },
        'error': msg,
    }

    resp['meta']['query'] = request.args
    resp = make_response(
        json.dumps(resp, default=unknown_object_json_handler),
        status_code
    )
    resp.headers['Content-Type'] = 'application/json'
    return resp


def bad_request(msg):
    return make_error(msg, 400)


def internal_error(context_msg, exception):
    msg = context_msg + '\nDebug:\n' + repr(exception)
    return make_error(msg, 500)


def json_response_base(validator, data, query=''):
    meta = {
        'message': '',
        'total': len(data)
    }

    if validator:
        try:
            meta['message'] = validator.warnings
        except AttributeError:
            meta['message'] = None
        meta['query'] = query

    return {
        'meta': meta,
        'data': data
    }
