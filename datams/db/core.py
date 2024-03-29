import pandas as pd
from flask import current_app, g
from sqlalchemy.orm import Session
from datams.utils import APP_CONFIG
from datams.db.utils import (connect_and_return_engine, create_upload_directories,
                             create_info_directory, validate_discovery_directory)
from datams.db.tables import sync_table_models


def query(statement):
    """
    get query results unaltered
    """
    engine = get_engine()
    with Session(engine) as session:
        result = session.execute(statement)
    return result


def query_first(statement):
    """
    get first result of query or None if no results
    """
    engine = get_engine()
    with Session(engine) as session:
        result = session.execute(statement).first()
    return result if result is None else result[0]


def query_df(statement):
    """
    return query results as a dataframe empty dataframe if None
    """
    engine = get_engine()
    with Session(engine) as session:
        result = session.execute(statement)
        df = pd.DataFrame(result, columns=result.keys())
    return df


def query_all(statements: list) -> None:
    engine = get_engine()
    with Session(engine) as session:
        for statement in statements:
            session.execute(statement)
        session.commit()
    return


def query_first_df(statement):
    """
    return query results as a series empty series if None
    """
    df = query_df(statement)
    if df.empty:
        return pd.Series(index=df.columns)
    return df.iloc[0]


def get_engine(app=None):
    try:
        if app is None:
            if 'engine' not in g:
                g.engine = current_app.extensions['sqlalchemy_engine']
            return g.engine
        else:
            return app.extensions['sqlalchemy_engine']
    except RuntimeError:
        return connect_and_return_engine(APP_CONFIG)


def database_init_app(app):
    # create the upload directories
    create_upload_directories(app.config['DATA_FILES']['upload_directory'])

    # create the info directory
    create_info_directory(app.config['INFO_DIRECTORY'])

    # validate the discovery directory
    validate_discovery_directory(app.config['DATA_FILES']['discovery_directory'])

    # create the engine to the database
    app.extensions['sqlalchemy_engine'] = connect_and_return_engine(APP_CONFIG)

    # ensure that the sqlalchemy orm models match the database
    # sync_table_models(APP_CONFIG)

    # TODO: app.teardown_appcontext(close_engine)?
