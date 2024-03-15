DOCKER README
=============

---
***ATTN:***

- This version of datams application has come with a primmed database.  Care was taken to ensure the
quality and accuracy of the data; however, some data may be missing or outdated.  As such, all data
should be verified before use.  Below is some metadata that are known to have inaccurate data:

  - UTC Offsets for Moorings (These all need to be determined and set)

---


## Starting Containers

1. Install docker-engine, docker and docker-compose from the [Docker Website](https://www.docker.com)
2. Fill out the `.env` file with the appropriate values for the environmental variables
3. From the root of the datams repository (i.e the one containing docker-compose.yaml) run the following:

---
***NOTE:***

When pulling from the GitHub repository files may have Windows style line-endings.  Docker doesn't like 
these, and it will cause the following `docker compose` command to fail in a very subtle way.  This can
be remedy by ensuring the files in the docker directory use LF (Unix style) rather than CRLF (Windows 
style) line endings

---

***On Linux:***
  ```bash
  $ docker compose --env-file ./docker/.env -f docker-compose.yaml up
  ```

***On Windoz:***
  ```bash
  $ docker-compose --env-file ./docker/.env -f docker-compose.yaml up
  ```

---
**NOTE:**

After this step the containers should all be up and running with the database populated; however, 
there are a couple steps still required to finalize the setup.

  > a. a cron job to periodically back-up database should be set-up
  > b. Users will need to be created
  > c. The paths to file resources within the database will need to be resolved

---
## Periodic Database Backup
1. Ensure that cron is installed and running this can be checked by running:

  ```bash
  $ crontab -e
  ```

2. If it is not installed it can be installed on linux as follows:
  ```
  $ sudo apt update ; sudo apt install cron
  ```


3. If cron is installed and running add the following line execute the following:
  ```bash
  $ crontab -e
  ```
  & add the following line to the bottom of the file.
  ```
  0 0 * * FRI (docker exec postgres /bin/bash -c '/scripts/postgres_dump.sh') 2>&1 | logger -t PG_DUMP
  ```
  
  Alternatively you can execute the following script from within this directory and it will add the above line to your crontab
  file:

---
***NOTE:***

This script will retain all the current tasks within cron unaltered; however it will drop the comments (so you should back-up of the crontab file before running this script if you do not wish to lose any comments):

---

  ```bash
  $ chmod 750 add_postgres_dump_to_host_crontab.sh
  $ ./add_postgres_dump_to_host_crontab.sh
  ```

  Both methods will set the cron to create a dump of the database every Friday at midnight.  
  You can verify this was added correctly if you are able to locate the following line:
  

## Setting up Users and Resolving Files
The easiest way to preform these final two steps is to first enter the container and run a shell.  

1. Enter the container and run bash shell
  ```bash
  $ docker exec -it datams /bin/bash
  ```
2. Create users
  ```bash
  # ex. creating an admin user JohnJoe
  $ datams-create-user --admin JohnJoe

  # ex. creating a regular user TimTom
  $ datams-create-user TimTom
  ```
  And follow the prompts.  

3. Resolve the files
  ```bash
  $ datams-resolve-files
  ```
That's it everything should be set-up and running now.  Keep reading for more details of the datams CLI commands.  


## `CLI Commands`
Once the application has been set-up (including `postgresql` which must also be running) you'll be able to run the following
datams commands:
  - `datams-create-user`    *create new user*
  - `datams-delete-user`    *delete existing user*
  - `datams-resolve-files`  *resolve the filenames*
  - `datams-init-db`        *initialize the database (i.e. remove all data, but provide the 
                             tables/structure of database)*
  - `datams-wipe-db`        *wipe the database (i.e. remove all data and tables/structure from the
                             database)*

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