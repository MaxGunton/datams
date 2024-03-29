from typing import Dict
import flask
from werkzeug.utils import secure_filename
from datams.utils import (fileobj_to_jpgbytes, datetimestr_to_timestamp,
                          current_timestamp, PROCESSED_DIRECTORY, ALLOWED_CHARACTERS)

from datams.db.utils import MissingRequiredDataError
from datams.db.queries.select import select_mooring_equipment_id, next_deployment_id
# TODO: Preform the checks here to make sure all the values are good before
#       bugging the database particularly with inserts, updates, and deletes

"""
All methods in this method should fail gracefully ultimately returning a error message
to the user that they had a poorly formatted request.

The difference between an insert and an update is update can have just some of the 
required fields.  
"""


def parse_request(request, table, rtype):
    if table == 'Contact':
        values = extract_contact_fields(request, rtype=rtype)
    elif table == 'Deployment':
        values = extract_deployment_fields(request, rtype=rtype)
    elif table == 'Equipment':
        values = extract_equipment_fields(request, rtype=rtype)
    elif table == 'File':
        values = extract_file_fields(request, rtype=rtype)
    elif table == 'Mooring':
        values = extract_mooring_fields(request, rtype=rtype)
    elif table == 'Organization':
        values = extract_organization_fields(request, rtype=rtype)
    elif table == 'User':
        values = extract_user_fields(request, rtype=rtype)
    else:
        raise NotImplementedError(table)
    return values


def get_form_field(request, key, dtype):
    value = request.form.get(key)
    return None if value == '' else dtype(value)


def get_form_fields(request: flask.Request, strict, required: Dict[str, callable]):
    required = {} if required is None else required
    if strict and not set(required.keys()).issubset(request.form.keys()):
        missing = set(required.keys()).difference(request.form.keys())
        raise MissingRequiredDataError(missing)
    return {v[0]: get_form_field(request, k, v[1]) for k, v in required.items()
            if k in request.form.keys()}


def get_files_field(request, key, dtype):
    return dtype(request.files.get(key))


def get_files_fields(request: flask.Request, strict, required: Dict[str, callable]):
    # does the request contain everything it needs
    required = {} if required is None else required
    if strict and not set(required.keys()).issubset([k for k in request.files.keys()]):
        missing = set(required.keys()).difference(request.form.keys())
        raise MissingRequiredDataError(missing)
    # can we cast it to the required type
    return {v[0]: get_files_field(request, k, v[1]) for k, v in required.items()
            if k in request.files.keys()}


def get_fields(request, strict, form_fields=None, file_fields=None):
    # TODO: Catch any issues here with the input
    v1 = get_form_fields(request, strict, form_fields)
    v2 = get_files_fields(request, strict, file_fields)
    return {**v1, **v2}


def fetch_associations(request, associations):
    return {f"{a}_ids": [int(request.form.get(k))
                         for k in request.form.keys()
                         if k.startswith(a)]
            for a in associations}


def uploaded_filepath(value: str):
    return [f"{PROCESSED_DIRECTORY}/{secure_filename(f)}" for f in value.split(',')]


def extract_user_fields(request, rtype):
    strict = True
    if rtype == 'auth':
        form_fields = {
            'email': ('email', str),
            'password': ('password', str)
        }
        values = get_fields(request, strict, form_fields)
        values['email'] = values['email'].lower()
    elif rtype == 'password_reset':
        form_fields = {
            'current_password': ('current_password', str),
            'new_password': ('new_password', str),
            'confirmed_new_password': ('confirmed_new_password', str),
            'username': ('username', str),
        }
        values = get_fields(request, strict, form_fields)
        values['view'] = 'user.by_username'
        if len(values['new_password']) < 6:
            raise ValueError('New password must be at least 6 characters.  ')
        if values['new_password'] != values['confirmed_new_password']:
            raise ValueError('New password entries do not match.  ')
        if values['new_password'] == values['current_password']:
            raise ValueError('New password should differ from current password.  ')
    else:
        values = None
    return values


def extract_contact_fields(request, rtype):
    form_fields = {
        'organization_id': ('organization_id', int),
        'position': ('position', str),
        'first_name': ('first_name', str),
        'last_name': ('last_name', str),
        'email': ('email', str),
        'phone': ('phone', str),
        'comments': ('comments', str),
    }
    file_fields = {
        'avatar': ('avatar', fileobj_to_jpgbytes)
    }
    # to_verify = ['first_name', 'last_name']
    values = (get_fields(request, False, form_fields, file_fields) if rtype == 'edit'
              else get_fields(request, True, form_fields, file_fields))
    # for i in to_verify:
    #     if i in values.keys() and not set(values[i]).issubset(ALLOWED_CHARACTERS):
    #         raise RuntimeError(f"{i} contains restricted characters.  Allowed "
    #                            f"characters include alpha numeric characters, "
    #                            f"underscore, and dash.  ")
    return values


def extract_deployment_fields(request: flask.Request, rtype):
    form_fields = {
        'region': ('region', str),
        'country_id': ('country_id', int),
        'comments': ('comments', str),
    }
    # to_verify = ['region']
    if rtype == 'edit':
        strict = False
        associations = ['contact']
        values = {
            **fetch_associations(request, associations),
            **get_fields(request, strict, form_fields),
            'organization_ids': [int(request.form.get(r))
                                 for r in request.form.keys()
                                 if r.startswith('organization_id')]
        }
    else:
        strict = True
        values = {
            **get_fields(request, strict, form_fields),
            'id': next_deployment_id(),
            'organization_ids': [int(request.form.get(r))
                                 for r in request.form.keys()
                                 if r.startswith('organization_id')]
        }
    # for i in to_verify:
    #     if i in values.keys() and not set(values[i]).issubset(ALLOWED_CHARACTERS):
    #         raise RuntimeError(f"{i} contains restricted characters.  Allowed "
    #                            f"characters include alpha numeric characters, "
    #                            f"underscore, and dash.  ")
    return values


def extract_equipment_fields(request, rtype):
    form_fields = {
        'serial_number': ('serial_number', str),
        'item': ('item', str),
        'make': ('make', str),
        'model': ('model', str),
        'organization_id': ('organization_id', int),
        'status': ('status', str),
        'comments': ('comments', str)
    }
    to_verify = ['serial_number', 'item']
    values = (get_fields(request, False, form_fields) if rtype == 'edit'
              else get_fields(request, True, form_fields))
    for i in to_verify:
        if i in values.keys() and ',' in values[i]:
            raise RuntimeError(f"{i} contains comma which is a restricted character "
                               f"and can't be used.  ")
    return values


def extract_file_fields(request, rtype):
    if rtype == 'process':
        form_fields = {
            'ftype': ('ftype', str),
            'indexes': ('indexes', eval),
            'uploads_id': ('uploads_id', str),
            'description': ('description', str),
            'comments': ('comments', str),
            'level': ('level', str),
        }
        # strict = False if rtype == 'edit' else True
        strict = True
        values = get_fields(request, strict, form_fields)
        values['uploaded'] = current_timestamp()
        values['organization_id'] = None
        values['deployment_id'] = None
        values['mooring_equipment_id'] = None
        level = values.pop('level')
        if level == 'organization':
            values['organization_id'] = get_form_field(request, 'organization_id', int)
        elif level == 'deployment':
            values['deployment_id'] = get_form_field(request, 'deployment_id', int)
        elif level == 'mooring_equipment':
            mid = get_form_field(request, f"mooring_id", int)
            eid = get_form_field(request, f"equipment_id", int)
            values['mooring_equipment_id'] = select_mooring_equipment_id(mid, eid)
        else:  # unowned
            pass
    elif rtype == 'delete':
        form_fields = {
            'ftype': ('ftype', str),
            'indexes': ('indexes', eval),
            'uploads_id': ('uploads_id', str),
        }
        values = get_fields(request, True, form_fields)
    elif rtype == 'restore':
        form_fields = {
            'indexes': ('indexes', eval),
            'uploads_id': ('uploads_id', str),
        }
        values = get_fields(request, True, form_fields)
    else:
        values = None
    return values


def extract_mooring_fields(request, rtype):
    form_fields = {
        'deployment_id': ('deployment_id', int),
        'deployed': ('deployed', datetimestr_to_timestamp),
        'recovered': ('recovered', datetimestr_to_timestamp),
        'timezone': ('timezone', float),
        'latitude': ('latitude', float),
        'longitude': ('longitude', float),
        'seafloor_depth': ('seafloor_depth', float),
        'line_length': ('line_length', float),
        'comments': ('comments', str)
    }
    if rtype == 'edit':
        strict = False
        associations = ['equipment']
        values = {**fetch_associations(request, associations),
                  **get_fields(request, strict, form_fields)}
    else:
        strict = True
        values = get_fields(request, strict, form_fields)
    return values


def extract_organization_fields(request, rtype):
    form_fields = {
        'name': ('name', str),
        'abbreviation': ('abbreviation', str),
        'country_id': ('country_id', int),
        'comments': ('comments', str)
    }
    to_verify = ['abbreviation']
    if rtype == 'edit':
        associations = ['contact', 'deployment', 'equipment']
        values = {**fetch_associations(request, associations),
                  **get_fields(request, False, form_fields)}
    else:
        values = get_fields(request, True, form_fields)
    for i in to_verify:
        if i in values.keys() and not set(values[i]).issubset(ALLOWED_CHARACTERS):
            raise RuntimeError(f"{i} contains restricted characters.  Allowed "
                               f"characters include alpha numeric characters, "
                               f"underscore, and dash.  ")
    return values



