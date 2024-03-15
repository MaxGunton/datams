import os
import datetime as dt
import click
import re
from pathlib import Path
import pandas as pd
from tqdm import tqdm

from sqlalchemy import select, update, delete, insert
from datams.utils import (APP_CONFIG, INFO_DIRECTORY, PROCESSED_DIRECTORY,
                          DISCOVERY_DIRECTORY, ALLOWED_CHARACTERS)
from datams.db.core import query_df, query_all
from datams.db.tables import File, User, wipe_db, initialize_db
from werkzeug.security import generate_password_hash
# from psycopg2.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError

# .errors.UniqueViolation
TQDM_WIDTH = 41


@click.command('wipe-db')
def wipe_db_command():
    """Clear all the existing data and tables."""
    click.echo('\nWARNING: This command WILL DELETE ALL DATA from the database!  It is '
               'highly recommended that you BACKUP the DATABASE before continuing.  \n')
    r = input('\nThis action will remove all database tables and all stored '
              'values!  Do you want to continue? Y or [N]: ')
    if r.lower() == 'y':
        wipe_db(APP_CONFIG)
        click.echo('\nDatabase wiped.')
    else:
        click.echo('\nWipe operation aborted.')


@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    click.echo('\nWARNING: This command WILL DELETE ALL DATA from the database!  It is '
               'highly recommended that you BACKUP the DATABASE before continuing.  \n')
    r = input('\nThis action will reset the database tables removing any and '
              'all stored values!  Do you want to continue? Y or [N]: ')
    if r.lower() == 'y':
        initialize_db(APP_CONFIG)
        click.echo('\nInitialized the database.')
    else:
        click.echo('\nInitialization aborted.')


# TODO: Create a file that has the details of the files that will remain unchanged,
#       be updated, or deleted
@click.command('resolve-files')
def resolve_files_command():
    """
    Attempts to resolve all `path` values in the File table.  This is accomplished by
    first checking if the `path` value represents an existing file.  If it does then
    that entry is left unmodified in the database, if not the path is truncated to the
    basename (i.e. filename).  After this first pass of the File table which truncated
    any non existent `path` values to their basenames, any rows where the `path` value
    is not unique are dropped.  The remaining basenames are then iterated through in an
    attempt to find a *unique* match within the upload and discovery directories.  If
    successful the respective path value within the File table is modified to match the
    full path of the matched file otherwise the entry is dropped from the database.
    """

    # 1. build the map of what files are present
    fmap = {}
    to_pop = []
    allfiles = []
    for f in tqdm(Path(PROCESSED_DIRECTORY).rglob('*'),
                  desc='traversing processed files directory'.ljust(TQDM_WIDTH)):
        if f.is_file():
            path = os.path.realpath(str(f))
            filename = os.path.basename(path)
            allfiles.append((path, filename))
            if filename in fmap.keys():
                # is duplicate basename therefore we'll drop it after
                to_pop.append(filename)
            else:
                fmap[filename] = path
    for f in tqdm(Path(DISCOVERY_DIRECTORY).rglob('*'),
                  desc='traversing discovery directory tree'.ljust(TQDM_WIDTH)):
        if f.is_file():
            path = os.path.realpath(str(f))
            filename = os.path.basename(path)
            allfiles.append((path, filename))
            if filename in fmap.keys():
                # is duplicate basename therefore we'll drop it after
                to_pop.append(filename)
            else:
                fmap[filename] = path
    for k in set(to_pop):
        fmap.pop(k)  # drop all the duplicate keys

    num_discoveries = len(allfiles)
    # ignored = sorted([
    #     (path, file, 'IGNORED') for path, file in allfiles if file not in fmap.keys()
    # ])
    # with open(f"{INFO_DIRECTORY}/ignored_discoveries.csv",
    #           'wt') as out_fp:
    #     out_fp.write("status,path,file,\n")
    #     for path, file, status in ignored:
    #         out_fp.write(f"{status},{path},{file},\n")

    click.echo(
        f"\n{num_discoveries} files found in `processed uploads` and "
        f"`discovery` directories.  ")
    click.secho(
        f"{num_discoveries - len(fmap)} have non-unique basenames and will "
        f"be ignored.  ", fg='yellow'
    )
    click.secho(
        f"\n{len(fmap)} will be used in candidate pool to resolve paths.  ",
        fg='bright_blue'
    )

    # 2. get all the files from database
    df = query_df(select(File.id, File.path))
    df_orig = df.copy()
    all_ids = list(df['id'])
    num_total = df.shape[0]
    click.secho(f"{num_total} entries found in `File` table.", fg='bright_blue')

    df['orig_path'] = df.loc[:, 'path']
    df['exists'] = df['path'].apply(lambda x: os.path.exists(x))
    df['filename'] = df['path'].apply(lambda x: os.path.basename(x))

    # 3. get indexes of good entries (these are good because their paths exist)
    df_good = pd.DataFrame(columns=['id'])
    df_good['id'] = df.loc[df['exists'], 'id']
    num_unchanged = df_good.shape[0]
    click.secho(f"\n{num_unchanged} entries in `File` table with existing paths.",
                fg='bright_cyan', bold=True)
    num_to_resolve = num_total - num_unchanged
    click.secho(f"{num_to_resolve} entries in `File` table require resolution.",
                fg='yellow')

    # 4. get indexes and filenames of ones to be checked
    duplicate_ids = list(df.loc[df.loc[~df['exists'], :].duplicated(subset=['filename'],
                                                                    keep=False), 'id'])
    df = df.loc[~df['exists'],
                ['id', 'filename', 'orig_path']].drop_duplicates(subset=['filename'])
    click.secho(f"{num_to_resolve - df.shape[0]} entries in `File` table have "
                f"non-unique filenames and thus can't be resolved.", fg='red')

    # 5. get the new path or None if can't resolve
    df['path'] = df['filename'].apply(lambda x: fmap.get(x))
    num_to_resolve = df.shape[0]

    # 6. drop the entries that are None/na
    df_rename = df.dropna()
    num_resolvable = df_rename.shape[0]
    click.secho(f"{num_resolvable} of {num_to_resolve} remaining entries in `File` "
                f"table can successfully be resolved.", fg='green')

    # 7. get the indexes that should be dropped
    to_drop = (
        set(all_ids)
        .difference(list(df_good['id']))
        .difference(list(df_rename['id']))
    )
    to_update_paths = df_rename.loc[:, ['orig_path', 'path']]
    todrop_df = df_orig.loc[df_orig['id'].isin(to_drop), ['id', 'path']]

    outfile = f"{INFO_DIRECTORY}/drf_proposed_changes.txt"
    date, time = tuple(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S').split(' '))
    # TODO: Consider making this into a csv rather than txt file
    with open(outfile, 'wt') as out_fp:
        main_header = (f"{'/'*100}\n\n"
                       f"DATE: {date}, TIME: {time}\n\n"
                       f"{'v'*100}\n\n")
        out_fp.write(main_header)

        drops_header = f"START DROPS\n{'='*11}\n\n"
        out_fp.write(drops_header)
        for idx, row in todrop_df.iterrows():
            reason = ("non-unique basename" if row['id'] in duplicate_ids
                      else "no match found")
            out_fp.write(f"DROP {row['path']}    : [{reason}]\n")

        renames_header = f"{'-'*100}\n\nSTART RENAMES\n{'=' * 13}\n\n"
        out_fp.write(renames_header)
        for _, r in to_update_paths.iterrows():
            out_fp.write(f"RENAME {r['orig_path']} > {r['path']}\n")

    # with open(f"{INFO_DIRECTORY}/candidates.csv", 'wt') as out_fp:
    #     out_fp.write(f"filenames,\n")
    #     for k in fmap.keys():
    #         out_fp.write(f"{k},\n")

    # with open(f"{INFO_DIRECTORY}/drops.csv", 'wt') as out_fp:
    #     out_fp.write(f"why_drop,path,filename\n")
    #     for idx, row in todrop_df.iterrows():
    #         reason = ("non-unique basename" if row['id'] in duplicate_ids
    #                   else "no match found")
    #         out_fp.write(f"{reason},{row['path']},{os.path.basename(row['path'])}\n")

    num_to_drop = len(to_drop)
    click.secho('\n\nWARNING: It is highly recommended that you BACKUP the DATABASE '
                'before continuing.  \n', bold=True, fg='red')
    click.secho(f"Proposed Changes to `File` Table\n{'='*32}\n", bold=True)
    click.secho("    Valid Entries".rjust(26) + " => " + f"{num_unchanged}".rjust(10) +
                " [remain unchanged]", fg='bright_cyan', bold=True)
    click.secho("    Resolvable Entries".rjust(26) + " => " +
                f"{num_resolvable}".rjust(10) + " [update to `path`]",
                fg='green', bold=True)
    click.secho("    Not Resolvable Entries".rjust(26) + " => " +
                f"{num_to_drop}".rjust(10) + " [drop from table]",
                fg='red', bold=True)

    r = input(f"\nThis action will preform the changes stated above to the `File` "
              f"table in the database!  Specific details surrounding these changes "
              f"can be found at `{outfile}`.  It is suggested you review these prior "
              f"to proceeding.  Do you want to continue? Y or [N]: ")

    if r.lower() == 'y':
        # 1. create the two queries:
        #       drop the indexes that couldn't be resolved
        #       update the paths of the ones that could
        query_all(
            [delete(File).where(File.id.in_(to_drop))] +
            [update(File).values(path=row['path']).where(File.id == row['id'])
             for idx, row in
             tqdm(df_rename.iterrows(),
                  desc='formatting database deletions and updates'.ljust(TQDM_WIDTH))]
        )

        # 2. generate the touch files
        def touch_file(p: str):
            if p.startswith(os.path.realpath(DISCOVERY_DIRECTORY)):
                with open(f"{p}.touch", 'at') as fp:
                    pass

        tqdm.pandas(desc="Creating .touch files for resolved files.".ljust(TQDM_WIDTH))
        df_rename['path'].progress_apply(touch_file)

        with open(outfile, 'rt') as in_fp:
            file_contents = in_fp.read()

        outfile = f"{INFO_DIRECTORY}/drf_applied_changes.txt"
        with open(outfile, 'at') as out_fp:
            out_fp.write(file_contents)
        click.echo(f"\nFilenames resolved.  See `{outfile}` details.  ")
    else:
        click.echo('\nFilename resolution aborted.')


@click.command('create-user')
@click.argument('username', nargs=1)
@click.option('--email', prompt=True)
@click.option('--admin', is_flag=True, show_default=True, default=False,
              help="Set to create admin user")
@click.password_option()
def create_user_command(username: str, email: str, admin: bool, password: str):
    # 1. check that username only uses ALLOWED_CHARACTERS
    if not set(username).issubset(ALLOWED_CHARACTERS):
        restricted_chars = set(username).difference(ALLOWED_CHARACTERS)
        msg = (f"\n\nFailed to create user: `{username}`\n    "
               f"It contains the following restricted characters: "
               f"{list(restricted_chars)}.\n    "
               f"Only letters, numbers, dashes and underscores are allowed.  \n")
        print(msg)
        return

    # 2. check that email matches the regular expression of an email form
    if not re.match('^\S+@\S+\.\S+$', email):
        msg = (f"\n\nFailed to create user: `{username}`:\n    Email address: "
               f"`{email}` is invalid.  \n")
        print(msg)
        return

    # 3. check that password is at least 6 characters
    if len(password) < 6:
        msg = (f"\n\nFailed to create user: `{username}`:\n    Password must be at "
               f"least 6 characters.  \n")
        print(msg)
        return

    role = 0 if admin else 1
    email = email.lower()
    password = generate_password_hash(password)
    stmt = insert(User).values(
        username=username, email=email, password=password, role=role, password_expired=1
    )
    try:
        query_all([stmt])
    except IntegrityError:
        msg = f"\n\nFailed to create user: `{username}`:  \n"
        df1 = query_df(select(User.id).where(User.username == username))
        df2 = query_df(select(User.id).where(User.email == email))
        if df1.shape[0] > 0:
            msg += f"    Username: `{username}` is already taken.  \n"
        if df2.shape[0] > 0:
            msg += f"    Email: `{email}` is already taken.  \n"
        print(msg)
        return

    print(f"\nSuccessfully created user: `{username}`")


@click.command('delete-user')
@click.argument('username', nargs=1)
def delete_user_command(username: str):
    df = query_df(select(User.id).where(User.username == username))
    if df.shape[0] == 0:
        print(f"\nNo user found with username: `{username}`")
        return
    else:
        stmt = delete(User).where(User.username == username)
        try:
            query_all([stmt])
        except IntegrityError as error:
            print(error)
            return
        print(f"\nSuccessfully deleted user: `{username}`")