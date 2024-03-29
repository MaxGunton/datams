import os
from typing import Tuple
import pandas as pd
from math import floor, log, cos, pi
from sqlalchemy import create_engine

DIRECTORY_LIMIT = 65000

class MissingRequiredDataError(Exception):
    """
    This exception is raised when a request is missing a required data.
    """

    def __init__(self, value=None):
        base_msg = 'Request is missing required data.  '
        self.message = (
            base_msg if value is None
            else base_msg + f"The following items were missing: {value}."
        )
        super().__init__(self.message)


def resolve_filename(filename, directory):
    i = 0
    new_filename = filename
    while new_filename in os.listdir(directory):
        fl = filename.split('.')
        new_filename = (f"{'.'.join(fl[:-1])} ({i}).{fl[-1]}"
                        if len(fl) > 1 else f"{filename} ({i})")
        i += 1
    return new_filename


def is_int_directory(directory):
    try:
        int(directory)
    except TypeError:
        return False
    return True


def check_directory_fullness(root_dir, cdir_idx, cdir_count):
    cdir = f"{root_dir}/{cdir_idx}"
    while cdir_count >= DIRECTORY_LIMIT:
        cdir_idx += 1
        cdir = f"{root_dir}/{cdir_idx}"
        os.makedirs(cdir, exist_ok=True)
        cdir_count = len(os.listdir(cdir))
    return cdir, cdir_idx, cdir_count


def resolve_directory(root_dir):
    int_dirs = [i for i in os.listdir(root_dir)
                if os.path.isdir(f"{root_dir}/{i}") and is_int_directory(i)]
    cdir_idx = max(int_dirs) if int_dirs else 0
    cdir = f"{root_dir}/{cdir_idx}"
    if not int_dirs:
        os.makedirs(cdir, exist_ok=True)
    cdir_count = len(os.listdir(cdir))
    return check_directory_fullness(root_dir, cdir_idx, cdir_count)


def create_upload_directories(path):
    for d in {'pending', 'processed'}:
        try:
            os.makedirs(f"{path}/{d}", exist_ok=True)
        except OSError:
            raise OSError(f"Failed to create directory `{path}/{d}` required for "
                          f"uploading.  ")


def create_info_directory(path: str):
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        raise OSError(f"Failed to create directory `{path}` required for datams info "
                      f"files")


def validate_discovery_directory(path):
    if not os.path.exists(path):
        raise NotADirectoryError(f"Discovery directory, at `{path}` does not exist.")
    elif os.path.isfile(path):
        raise FileExistsError(f"Discovery directory, `{path}` must reference existing "
                              f"directory instead of a file.  ")
    return


def generate_database_url(dialect, driver, username, password, host, port, database):
    return f"{dialect}+{driver}://{username}:{password}@{host}:{port}/{database}"


def connect_and_return_engine(app_config):
    url = generate_database_url(**app_config['DATABASE'])
    return create_engine(url)


def result_to_df(result):
    return pd.DataFrame(result, columns=result.keys())


def map_properties(moorings: pd.DataFrame) -> Tuple[Tuple[float, float], float]:
    m = moorings.copy().loc[:, ['latitude', 'longitude']].dropna()
    if m.empty:
        return (0.0, 0.0), 2.0

    mw = 500  # map width in pixels
    lats, lons = list(m['latitude']), list(m['longitude'])
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    h = (max_lat - min_lat) * 110825.28 * 1.1
    w = (max_lon - min_lon) * 87782.4 * 1.1

    lat, lon = (max_lat+min_lat) / 2, (max_lon+min_lon) / 2
    md = max(h, w)
    zoom = (
        14 if md == 0
        else min(14, floor(log(156543.03392 * mw * cos(lat * pi / 180) / md, 2)))
    )
    return (lat, lon), zoom


def mooring_add_equipment_html(mooring: pd.DataFrame,
                               equipment: pd.DataFrame) -> pd.DataFrame:
    """
    Requires both equipment and Moorings have already computed their html strings
    and that mooring has a column eq_ids

    """
    def combine_html(r: pd.Series) -> str:
        html = r['html']
        html += "<h2>Equipment</h2><ul>"
        if r['eq_ids'] is not None:
            eids = [int(i) for i in r['eq_ids'].split(',')]
            for i in list(equipment.loc[equipment['id'].isin(eids), 'html']):
                html += i
        return html + '</ul>'

    if mooring.empty:
        return mooring
    mooring['html'] = mooring.apply(combine_html, axis=1)
    return mooring


def mooring_files_add_section(m_files: pd.DataFrame, moorings:pd.DataFrame):
    """
    mfiles needs column mooring_id and moorings needs columns id and name
    """
    if moorings.empty:
        m_files['section'] = None
        return m_files

    sections = {
        i: f"{moorings.loc[moorings['id'] == i, 'name'].iloc[0]} Files"
        for i in list(moorings['id'].unique())
    }
    df = pd.DataFrame({
        **{i: [None]*len(sections) for i in m_files.columns},
        **{'section': list(sections.values())}
    })
    m_files['section'] = m_files['mooring_id'].apply(lambda x: f"{sections[x]}")
    m_files = pd.concat([m_files, df])
    return m_files
