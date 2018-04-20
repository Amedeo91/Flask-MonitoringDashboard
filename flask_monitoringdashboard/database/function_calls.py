"""
Contains all functions that access any functionCall-object
"""

import datetime
import time

from sqlalchemy import func, desc, asc, distinct

from flask_monitoringdashboard import config
from flask_monitoringdashboard.core.group_by import get_group_by
from flask_monitoringdashboard.database import session_scope, FunctionCall


def get_requests_per_day(endpoint, list_of_days):
    """
    :param endpoint: name of the endpoint
    :param list_of_days: a list with datetime.date objects
    :return: A list of the amount of requests per day for a specific endpoint.
    If no requests is made on that day, a value of 0 is returned.
    """
    result_list = []
    with session_scope() as db_session:
        for day in list_of_days:
            result = db_session.query(FunctionCall.execution_time).\
                filter(FunctionCall.endpoint == endpoint).\
                filter(func.strftime('%Y-%m-%d', FunctionCall.time) == day.strftime('%Y-%m-%d')).count()
            result_list.append(result)
    return result_list


def add_function_call(time, endpoint, ip):
    """ Add a measurement to the database. """
    with session_scope() as db_session:
        call = FunctionCall(endpoint=endpoint, execution_time=time, version=config.version,
                            time=datetime.datetime.now(), group_by=get_group_by(), ip=ip)
        db_session.add(call)


def get_times():
    """ Return all entries of measurements with the average and total number of execution times. The results are 
    grouped by their endpoint. """
    with session_scope() as db_session:
        result = db_session.query(FunctionCall.endpoint,
                                  func.count(FunctionCall.execution_time).label('count'),
                                  func.avg(FunctionCall.execution_time).label('average')
                                  ).group_by(FunctionCall.endpoint).order_by(desc('count')).all()
        db_session.expunge_all()
        return result


def get_hits(endpoint, date_from=datetime.datetime.utcfromtimestamp(0)):
    """ Return the number of hits for a specific endpoint within a certain time interval.
    If date_from is not specified, all results are counted
    :param endpoint: name of the endpoint
    :param date_from: A datetime-object
    """
    with session_scope() as db_session:
        result = db_session.query(func.count(FunctionCall.execution_time).label('count')). \
            filter(FunctionCall.endpoint == endpoint).filter(FunctionCall.time > date_from). \
            group_by(FunctionCall.endpoint).first()
        db_session.expunge_all()
        if result:
            return result[0]
        return 0


def get_median(endpoint, date_from=datetime.datetime.utcfromtimestamp(0)):
    """ Return the median for a specific endpoint within a certain time interval.
    If date_from is not specified, all results are counted
    :param endpoint: name of the endpoint
    :param date_from: A datetime-object
    """
    with session_scope() as db_session:
        result = db_session.query(FunctionCall.execution_time). \
            filter(FunctionCall.endpoint == endpoint).filter(FunctionCall.time > date_from). \
            order_by(FunctionCall.execution_time).all()
        result_list = [r[0] for r in result]
        return median_value(result_list)


def median_value(result_list):
    """ Takes the median value from a list.
    Note that the given result_list must be sorted"""
    count = len(result_list)
    if count == 0:
        return 0
    if count % 2 == 1:
        return result_list[count // 2]
    else:
        return (result_list[count // 2 - 1] + result_list[count // 2]) / 2


def get_data_between(time_from, time_to=None):
    """
        Returns all data in the FunctionCall table, for the export data option.
        This function returns all data after the time_from date.
    """
    with session_scope() as db_session:
        result = db_session.query(FunctionCall).filter(FunctionCall.time >= time_from)
        if time_to:
            result = result.filter(FunctionCall.time < time_to)
        result = result.all()
        db_session.expunge_all()
        return result


def get_data():
    """
    Equivalent function to get_data_from, but returns all data.
    :return: all data from the database in the Endpoint-table.
    """
    return get_data_between(datetime.date(1970, 1, 1), datetime.datetime.utcnow())


def get_data_per_version(version):
    """ Returns all data in the FunctionCall table, grouped by their version. """
    with session_scope() as db_session:
        result = db_session.query(FunctionCall.execution_time, FunctionCall.version). \
            filter(FunctionCall.version == version).all()
        db_session.expunge_all()
        return result


def get_hits_per_version(version):
    """ Returns the hits per endpoint per version """
    with session_scope() as db_session:
        result = db_session.query(FunctionCall.endpoint,
                                  FunctionCall.version,
                                  func.count(FunctionCall.endpoint).label('count')). \
            filter(FunctionCall.version == version). \
            group_by(FunctionCall.endpoint).all()
        db_session.expunge_all()
        return result


def get_versions(end=None, limit=None):
    with session_scope() as db_session:
        query = db_session.query(distinct(FunctionCall.version)).\
            filter((FunctionCall.endpoint == end) | (end is None)).\
            order_by(asc(FunctionCall.time))
        if limit:
            query = query.limit(limit)
        result = query.all()
        db_session.expunge_all()
    return [row[0] for row in result]


def get_data_per_endpoint(end):
    with session_scope() as db_session:
        result = db_session.query(FunctionCall.execution_time, FunctionCall.endpoint). \
            filter(FunctionCall.endpoint == end).all()
        db_session.expunge_all()
        return result


def get_endpoints():
    """ Returns the name of all endpoints from the database """
    with session_scope() as db_session:
        result = db_session.query(FunctionCall.endpoint).distinct().all()
        db_session.expunge_all()
        return [r[0] for r in result]  # unpack tuple result


def get_endpoints_with_count():
    with session_scope() as db_session:
        result = db_session.query(FunctionCall.endpoint,
                                  func.count(FunctionCall.endpoint).label('cnt')). \
            group_by(FunctionCall.endpoint).order_by(asc('cnt')).all()
        db_session.expunge_all()
        return result


def get_date_of_first_request():
    """ return the date (as unix timestamp) of the first request """
    with session_scope() as db_session:
        result = db_session.query(FunctionCall.time).first()
        if result:
            return int(time.mktime(result[0].timetuple()))
        return -1
