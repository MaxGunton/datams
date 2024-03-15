# datams

## Installation (Ubuntu OS)

---
*NOTE:*
- Replace `ubuntu` username with your actual username in the directions below

---

### 1. Install the dependancies
  ```bash
  $ sudo add-apt-repository ppa:deadsnakes/ppa
  $ sudo apt update
  $ sudo apt install software-properties-common
  $ sudo apt install python3.10 python3.10-distutils python3.10-dev python3.10-venv python3-pip
  $ sudo apt install libpq-dev build-essential
  $ sudo apt install libgl1-mesa-glx
  $ sudo apt install postgresql
  $ sudo apt install redis
  $ sudo apt install nginx
  ```

### 2. Install and setup scripts for virtual environment
  ```bash
  $ python3.10 -m pip install --upgrade pip
  $ python3.10 -m pip install virtualenvwrapper
  $ export PATH="/home/ubuntu/.local/bin:$PATH"
  $ export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3.10
  ```

### 3. Pull the source code from the repository
  ```bash
  $ git clone git@github.com:MaxGunton/datams.git  # get source code from git
  $ sudo mv datams /usr/local/src
  $ export WORKON_HOME=/usr/local/src/datams/.venv
  $ mkdir -p $WORKON_HOME
  ```
   

### 4. Run the virtualenvwrapper scripts
  ```bash
  $ source /home/ubuntu/.local/bin/virtualenvwrapper.sh
  ```

***If this is not the correct location then it can be found using***
  ```bash
  $ pip show -f virtualenvwrapper
  ```

---
*NOTE:*

- These export commands (and the virtualenvwrapper script) can be added to .bashrc (so they will run upon shell startup)

---

### 5. Make the virtual environment and install the required dependancies including our package
  ```bash
  $ mkvirtualenv -p python3.10 datams
  $ pip install -r /usr/local/src/datams/requirements.txt
  ```

### 6. Create the new database
  ```bash
  $ sudo -u postgres createdb datams
  ```

### 7. Log into postgres database as postgres user and create datams user and grant them priviledges on the new database
  ```bash
  $ sudo -u postgres psql
  $ postgres=# CREATE USER datams WITH encrypted PASSWORD '<password>';  # remember this password
  $ postgres=# GRANT ALL PRIVILEGES ON DATABASE datams TO datams;
  $ postgres=# exit;
  ```

### 8. Add passwords to the configuration file
  ```bash
  $ python -c 'import secrets; print(secrets.token_hex())'  # remember this key
  $ nano /usr/local/src/datams/datams/config.yml  # replace dummy passwords with real ones
  ```

### 9. Set up nginx with our web app
  ```bash
  $ sudo mv /usr/local/src/datams/installation/datams /etc/nginx/sites-available/  # move our site config
  $ sudo chown root:root /etc/nginx/sites-available/datams
  $ sudo chmod 644 /etc/nginx/sites-available/datams
  $ sudo ln -s /etc/nginx/sites-available/datams /etc/nginx/sites-enabled/
  $ sudo rm /etc/nginx/sites-enabled/default
  $ sudo nano /etc/nginx/nginx.conf 
  ```

  > Within the `nginx.conf` file:
  > 1. change line `user www-data;` to `user ubuntu;`
  > 2. add the following to http section: 
  >    ```client_max_body_size 4M;```
    


### 10. Set up gunicorn service to run under supervision of systemd (change user dictated by gunicorn.service to you're username)
  ```bash
  $ sudo mv /usr/local/src/datams/installation/gunicorn.service /etc/systemd/system/
  $ sudo chown root:root /etc/systemd/system/gunicorn.service
  $ sudo chmod 644 /etc/systemd/system/gunicorn.service
  ```

### 11. Set up celery service to run under supervision of systemd (change user dictated by celery.service to you're username)
  ```bash
  $ sudo mv /usr/local/src/datams/installation/celery.service /etc/systemd/system/
  $ sudo chown root:root /etc/systemd/system/celery.service
  $ sudo chmod 644 /etc/systemd/system/celery.service
  ```

### 12. Restart the systemd daemon to reflect the changes
  ```bash
  $ sudo systemctl daemon-reload
  ```

### 13. Initialize the database
  ```bash
  $ flask --app /usr/local/src/datams/ init-db
  ```

### 14. Prime the database with initial values
  - TODO: Come up with strategy for this

### 15. Change the priviledges on the web-app source (to protect private keys etc.) and create required directories
  ```bash
  $ sudo chmod -R o-rwx /usr/local/src/datams/
  $ sudo mkdir -p /var/lib/datams/uploads/submitted
  $ sudo mkdir -p /var/lib/datams/uploads/pending
  $ sudo chmod -R 770 /var/lib/datams
  ```

### 16. start services and check their status to ensure they started correctly
  ```bash
  $ sudo systemctl enable celery
  $ sudo systemctl start celery
  $ sudo systemctl status celery
  $ sudo systemctl enable gunicorn
  $ sudo systemctl start gunicorn
  $ sudo systemctl status gunicorn
  $ sudo systemctl restart nginx
  ```

### 17. Other steps
- ***SET UP BACKUP OF POSTGRES (SEE ./docker/README.md)***
- ***TODO: SET UP NGINX WITH ENCRYPTED CONNECTION (i.e. HTTPS/SSL)***


## COMMANDS

### Starting `datams`
The following commands are used to start the application.  Assuming that redis and postgres are already running locally
on ports 6379 and 5432 respectively (although the host and ports can be changed in the `datams/config.yaml` file).  
  ```bash
  $ celery --app make_celery worker --loglevel=DEBUG --pool=solo  # start celery workers; `--pool=solo` option for Windoz
  $ celery --app make_celery beat                                 # scheduler to trigger celery periodic tasks
  $ flask --app datams run --debug                                # development server (for debugging)
  ```

When using `datams` in production, the server should be launched as follows:
  ```bash
  $ gunicorn --bind 127.0.0.1:8000 wsgi:app
  ```
This can then be put reverse proxied using nginx.  

## `CLI Commands`
Once the application has been set-up (including `postgresql` which must also be running) you'll be able to run the following
datams commands:
  - `datams-create-user`    *create new user*
  - `datams-delete-user`    *delete existing user*
  - `datams-resolve-files`  *resolve the filenames*
  - `datams-init-db`        *initialize the database (i.e. remove all data, but provide the tables/structure of database)*
  - `datams-wipe-db`        *wipe the database (i.e. remove all data and tables/structure from the database)*

### `datams-create-user`
```bash
Usage: datams-create-user [OPTIONS] USERNAME

Options:
  --email TEXT
  --admin          Set to create admin user
  --password TEXT
  --help           Show this message and exit.
```
This command is used to create a new user.  Include the --admin option if you want the user to have admin
priviledges (currently the only difference between a regular user and an admin is in the ability to 
manage users).  

**You'll need to provide the password to the person for whom you've created the account.**  They'll need it for 
their initial login at which point they will be forced to change it.

---
**NOTE:**

- the username and email must be unique from all existing users.
- username can only contain letters, numbers, underscores, and dashes.  
- the length of the password must be >= 6 characters
- it is not advised to enter a password directly as it will be stored in plain text within the .bash_history.  
Instead, simply omit it and you will automatically be prompt for it.  

---
Examples:

- Ex 1. Create a regular user John.Smith with email John.Smith@csiro.au

   ```bash
   $ datams-create-user JohnSmith
   Email: John.Smith@csiro.au
   Password:
   Repeat for confirmation:

   Successfully created user: `John.Smith`
   ```
- Ex 2. Create admin user louiszoo with email lz212@hotmail.com

   ```bash
   $ datams-create-user --admin louiszoo
   Email: lz212@hotmail.com
   Password:
   Repeat for confirmation:

   Successfully created user: `louiszoo`
   ```

### `datams-delete-user`
```bash
Usage: datams-delete-user [OPTIONS] USERNAME

Options:
  --help  Show this message and exit.
```
Deletes an existing user account.  The only argument this command takes is the username of an existing user.  

- Ex. Delete user louiszoo
   ```bash
   $ datams-delete-user louiszoo

   Successfully deleted user: `louiszoo`
   ```

### `datams-resolve-files`
```bash
Usage: datams-resolve-files [OPTIONS]

  Attempts to find all the file resources it can within the upload or
  discovery directories.  Anything it can't find is dropped from the database.

Options:
  --help  Show this message and exit.
```
This command iterates through all the path values within the File table of the database, first checking if the
path exists.  If the path exists then the entry is left as is, otherwise the path is truncated to its basename
(i.e. just the filename).  After preforming the truncation any duplicates basenames are dropped from the 
database (as these cannot be uniquely matched).  The remaining basenames are then iterated through in an attempt
to find a **unique** match within the upload and discovery directories.  If successful the respective path value
within the File table is modified to match the full path of the matched file otherwise the entry is dropped from
the database.  

The reason for this command is because the initial database data was development on a system with a varying 
directory layout; as such, the sole intention of this command is to save manual re-entry of as many file 
resources as possible.  

---
**NOTE:**

- This command only needs to be run a single time after setting up the containers and ensuring the volumes are 
  mounted correctly.  
- There is no risk of this operation deleting any existing files; however, entries for files that can't be 
  resolved will be deleted from the database.
- This command potentially traverses through a lot of files and can take a minute or two to complete.  

---
- Ex.
   ```bash
   $ datams-resolve-filenames

   WARNING: This action will remove database entries for file resources it is unable to uniquely resolve.  This script will 
   first check if the path to the file resource exists.  If not it searches through the uploads and discovery directories 
   looking for a single exact basename match. If none or multiple matches are found it is dropped!  Do you want to continue? Y or [N]:y

   Filenames resolved.  
   ```

### `datams-init-db`
```bash
Usage: datams-init-db [OPTIONS]

  Clear the existing data and create new tables.

Options:
  --help  Show this message and exit.
```
Clear the existing database and reinitialize with newly created tables/structure.

- Ex.
   ```bash
   $ datams-init-db
 
   WARNING: This action will reset the database tables removing any and all stored values!  Do you want to continue? Y or [N]: y
 
   Initialized the database.
   ```

### `datams-wipe-db`
```bash
Usage: datams-wipe-db [OPTIONS]

  Clear all the existing data and tables.

Options:
  --help  Show this message and exit.
```
Clear the existing database removing all tables/structure.  

- Ex.
   ```bash
   $ datams-wipe-db
 
   WARNING: This action will remove all database tables and all stored values!  Do you want to continue? Y or [N]: y
 
   Database wiped.
   ```


## TODO
   - update the moorings to have the correct utc_offsets
   - allow spaces in organization names
   
### Essential Requirements
   - ensure all services will sucessfully start if one or all fail.  
   - ensure that database, logs, and any other essential information is persistant and protected
   
   - make decisions on how to deal with deletions from the database; that is should they cascade,
   leave orphaned entries in other tables or only allowed if they aren't referenced elsewhere.
***The following may have been completed:***
   > - have failed transactions rollback by executing them all in a block instead of separately
   > - Fix the error involving letter case of uploads filenames (could force lowercase).
   
### Non-essential Requirements
   - figure out mail server and set-up with flask-mail using postfix and Dovecot?
   - add email password reset feature using flask-login by implementing @login_manager.request_loader
   - implement more logging within webapp
   - add functionality to add/remove files from within organization, deployment, and mooring edit views.  
   - create a set of unit tests and system tests
   - user/admin function (reset_password/forgot_password)
   - admin functions within webapp (remove_user, add_user, change_user_priviledges)
   - ssl certificate for nginx (and add details to config)
   - add constraint that comma's aren't allowed some strings or choose a special deliminator to use instead
   - sort menu lists before sending to templates so that they are in the correct order
   - avoid showing none/na by using .fillna('') on dataframe before sending to templates
   - make the general sections of the edit templates simply use a prefilled version of the add templates, but for the file.edit template make sure to remove the option to drop files.  
   - format page templates for better layout and presentation of data
   - have the file.details template show a preview of the file and ensure that the file doesn't automatically download
   - within the database a set tables which would allow admin to rollback database to any specific time
   - implement client side form validation where possible and have things like latitude and longitude round
   - make additional background task called update_cache which only changes the relevant rows instead of recomputing the entire dataframe
   - When editing or unlinking prompt user with a confirmation message before commiting any changes, also prompt user with message when navigating away
   - when editing processed files have the current values prefilled if possible
   - Generate banner title in the views.py
   - Create a component for buttons (i.e. add, delete, edit) could be a single component that is given options, and send that to banner template with title (i.e. Do away with the banner button stuff and create a component that can be added to the banner view same for title)
   - replace forms so they are implemented using WTF-Flask
   - use Flask-Upload to handle file uploads?
   - look into using an implementation of the merkle tree for the stored file uploads to ensure data-consistency
   - Add typing hints where they are missing
   - create themed pages for displaying http codes (i.e. 404, 300)
   - implment viewer priviledges by creating custom decorating similar to the @login_required decorated
     that checks if user.role < 2.  Also should disable or hide the buttons to access these areas from this type of user
   - table to log user actions to see how system is being used
   - create an npm? environment for the web development kits used (datatables, bootstrap5, ...)
