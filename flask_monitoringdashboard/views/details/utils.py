import pkg_resources
from flask import url_for, request
from flask_monitoringdashboard.database.function_calls import get_date_of_first_request

from flask_monitoringdashboard.database.endpoint import get_monitor_rule
from flask_wtf import FlaskForm
from werkzeug.routing import BuildError
from wtforms import SelectMultipleField, SubmitField
from flask_monitoringdashboard import config

BUBBLE_SIZE_RATIO = 1250


def get_endpoint_details(endpoint):
    """ Return details about an endpoint"""
    return {
        'endpoint': endpoint,
        'rule': get_monitor_rule(endpoint),
        'url': get_url(endpoint),
    }


def get_details():
    """ Return details about the deployment """
    return {
        'link': config.link,
        'dashboard-version': pkg_resources.require("Flask-MonitoringDashboard")[0].version,
        'config-version': config.version,
        'first-request': get_date_of_first_request()
    }


def formatter(ms):
    """
    formats the ms into seconds and ms
    :param ms: the number of ms
    :return: a string representing the same amount, but now represented in seconds and ms.
    """
    sec = int(ms) // 1000
    ms = int(ms) % 1000
    if sec == 0:
        return '{0}ms'.format(ms)
    return '{0}.{1}s'.format(sec, ms)


def get_url(end):
    """
    Returns the URL if possible.
    URL's that require additional arguments, like /static/<file> cannot be retrieved.
    :param end: the endpoint for the url.
    :return: the url_for(end) or None,
    """
    try:
        return url_for(end)
    except BuildError:
        return None
