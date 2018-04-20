"""
Contains all functions that access a single endpoint
"""
import datetime

from sqlalchemy import func, text, asc, distinct
from sqlalchemy.orm.exc import NoResultFound

from flask_monitoringdashboard import config
from flask_monitoringdashboard.database import session_scope, FunctionCall, MonitorRule


def get_line_results(endpoint):
    """
    Returns simple statistics, such as average, minimum, maximum and count from a given endpoint
    :param endpoint: the name of the endpoint
    :return: simple statistics, as described above
    """
    with session_scope() as db_session:
        query = text("""SELECT
                datetime(CAST(strftime('%s', time)/3600 AS INT)*3600, 'unixepoch') AS newTime, 
                avg(execution_time) AS avg,
                min(execution_time) AS min,
                max(execution_time) AS max,
                count(execution_time) AS count
            FROM functioncalls 
            WHERE endpoint=:val GROUP BY newTime""")
        result = db_session.execute(query, {'val': endpoint})
        data = result.fetchall()
        return data


def get_num_requests(endpoint, start_date, end_date):
    """ Returns a list with all dates on which an endpoint is accessed.
        :param endpoint: if None, the result is the sum of all endpoints
        :param start_date: datetime.date object
        :param end_date: datetime.date object
    """
    with session_scope() as db_session:
        query = db_session.query(func.strftime('%Y-%m-%d %H:00:00', FunctionCall.time).label('newTime'),
                                 func.count(FunctionCall.execution_time).label('count'))
        if endpoint:
            query = query.filter(FunctionCall.endpoint == endpoint)
        result = query.filter(FunctionCall.time >= datetime.datetime.combine(start_date, datetime.time(0, 0, 0, 0))). \
            filter(FunctionCall.time <= datetime.datetime.combine(end_date, datetime.time(23, 59, 59))).\
            group_by('newTime').all()
        db_session.expunge_all()
        return result


def get_num_users(endpoint):
    """
    :param endpoint: filter on this endpoint
    :return: The number of distinct users that have requested this endpoint
    """
    with session_scope() as db_session:
        result = db_session.query(func.count(distinct(FunctionCall.group_by))).\
            filter(FunctionCall.endpoint == endpoint).first()
        if result:
            return result[0]
        return 0


def get_num_ips(endpoint):
    """
    :param endpoint: filter on this endpoint
    :return: The number of distinct users that have requested this endpoint
    """
    with session_scope() as db_session:
        result = db_session.query(func.count(distinct(FunctionCall.ip))).\
            filter(FunctionCall.endpoint == endpoint).first()
        if result:
            return result[0]
        return 0


def get_num_versions(endpoint):
    """
    :param endpoint: filter on this endpoint
    :return: The number of distinct versions that are used for this endpoint
    """
    with session_scope() as db_session:
        result = db_session.query(func.count(distinct(FunctionCall.version))).\
            filter(FunctionCall.endpoint == endpoint).first()
        if result:
            return result[0]
        return 0


def get_endpoint_column(endpoint, column):
    """ Returns a list of entries from column in which the endpoint is involved. """
    with session_scope() as db_session:
        result = db_session.query(column,
                                  func.min(FunctionCall.time).label('startedUsingOn')). \
            filter(FunctionCall.endpoint == endpoint). \
            group_by(column).order_by(asc('startedUsingOn')).all()
        db_session.expunge_all()
        return result


def get_endpoint_column_user_sorted(endpoint, column, limit=100):
    """ Returns a list of entries from column in which the endpoint is involved. """
    with session_scope() as db_session:
        result = db_session.query(column). \
            filter(FunctionCall.endpoint == endpoint). \
            group_by(column).order_by(asc(column)).limit(limit).all()
        db_session.expunge_all()
        return result


def get_endpoint_results(endpoint, column):
    """ Returns a list of entries with measurements in which the endpoint is involved.
    The entries are grouped by their version and the given column. """
    with session_scope() as db_session:
        result = db_session.query(FunctionCall.version,
                                  column,
                                  func.count(FunctionCall.execution_time).label('count'),
                                  func.avg(FunctionCall.execution_time).label('average')
                                  ).filter(FunctionCall.endpoint == endpoint). \
            group_by(FunctionCall.version, column).all()
        db_session.expunge_all()
        return result


def get_monitor_rule(endpoint):
    """ Get the MonitorRule from a given endpoint. If no value is found, a new value 
    is added to the database and the function is called again (recursively). """
    try:
        with session_scope() as db_session:
            result = db_session.query(MonitorRule). \
                filter(MonitorRule.endpoint == endpoint).one()
            # for using the result when the session is closed, use expunge
            db_session.expunge(result)
            return result
    except NoResultFound:
        with session_scope() as db_session:
            db_session.add(
                MonitorRule(endpoint=endpoint, version_added=config.version, time_added=datetime.datetime.now()))

        # return new added row
        return get_monitor_rule(endpoint)


def update_monitor_rule(endpoint, value):
    """ Update the value of a specific monitor rule. """
    with session_scope() as db_session:
        db_session.query(MonitorRule).filter(MonitorRule.endpoint == endpoint). \
            update({MonitorRule.monitor: value})


def get_all_measurement(endpoint):
    """Return all entries with measurements from a given endpoint. Used for creating a histogram. """
    with session_scope() as db_session:
        result = db_session.query(FunctionCall).filter(FunctionCall.endpoint == endpoint).all()
        db_session.expunge_all()
        return result


def get_all_measurement_per_column(endpoint, column, value):
    """Return all entries with measurements from a given endpoint for which the column has a specific value.
    Used for creating a box plot. """
    with session_scope() as db_session:
        result = db_session.query(FunctionCall).filter(FunctionCall.endpoint == endpoint, column == value).all()
        db_session.expunge_all()
        return result


def get_last_accessed_times(endpoint):
    """ Returns a list of all endpoints and their last accessed time. """
    with session_scope() as db_session:
        result = db_session.query(MonitorRule.last_accessed).filter(MonitorRule.endpoint == endpoint).first()
        db_session.expunge_all()
        if result:
            return result[0]
        return None


def update_last_accessed(endpoint, value):
    """ Updates the timestamp of last access of the endpoint. """
    with session_scope() as db_session:
        db_session.query(MonitorRule).filter(MonitorRule.endpoint == endpoint). \
            update({MonitorRule.last_accessed: value})
