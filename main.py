import datetime
import random
from random import choice
import mysql.connector
from mysql.connector import errorcode
import PySimpleGUI as gui
from sqlalchemy import create_engine
import pandas as pd
import os
from tabulate import tabulate

tabulate.PRESERVE_WHITESPACE = True

DB_NAME = 'sportsdb'
cnx = mysql.connector.connect(user='root',
                              password='root',
                              host='127.0.0.1')
cursor = cnx.cursor()


def commit_exit():
    cnx.commit()
    cursor.close()
    cnx.close()
    exit(1)


def create_nice_table(data, heads):
    if not data:
        return 'No data'
    return tabulate(data, headers=heads, tablefmt='plain', colalign=('left',))


def clear_keys(window, keys_to_clear):
    for key in keys_to_clear:
        window[key]('')


def create_database(cursor, DB_NAME):
    try:
        cursor.execute('create database {} default character set \"utf8\"'.format(DB_NAME))

    except mysql.connector.Error as err:
        print("Failed to create database {}.".format(err))
        exit(1)


def create_tables(cursor):
    try:
        print("Creating tables...", end=' ')

        cursor.execute('create table arena('
                       'arena_name varchar(45) not null,'
                       'address varchar(45),'
                       'capacity int,'
                       'primary key(arena_name))'
                       )

        cursor.execute('create table Organization('
                       'org_name varchar(45) not null,'
                       'username varchar(45),'
                       'password varchar(45),'
                       'home_arena varchar(45),'
                       'primary key (org_name),'
                       'foreign key (home_arena) references arena(arena_name))'
                       )

        cursor.execute('create table team('
                       'team_name varchar(45) not null,'
                       'org_name varchar(45),'
                       'league_points int,'
                       'league_name varchar(45),'
                       'primary key (team_name),'
                       'foreign key (org_name) references organization(org_name))'
                       )

        cursor.execute('create table referee('
                       'ref_id int not null AUTO_INCREMENT,'
                       'ref_name varchar(45),'
                       'ref_surname varchar(45),'
                       'username varchar(45),'
                       'password varchar(45),'
                       'primary key (ref_id))'
                       )

        cursor.execute('create table admin('
                       'username varchar(45),'
                       'password varchar(45),'
                       'primary key (username))'
                       )

        cursor.execute('create table game('
                       'game_id int not null AUTO_INCREMENT,'
                       'date varchar(45),'
                       'time varchar(45),'
                       'home_team_name varchar(45),'
                       'guest_team_name varchar(45),'
                       'score_home int,'
                       'score_guest int,'
                       'ref_1_id int,'
                       'ref_2_id int,'
                       'arena_name varchar(45),'
                       'league_name varchar(45),'
                       'primary key (game_id),'
                       'foreign key (arena_name) references arena(arena_name),'
                       'foreign key (ref_1_id) references referee(ref_id),'
                       'foreign key (ref_2_id) references referee(ref_id),'
                       'foreign key (home_team_name) references team(team_name),'
                       'foreign key (guest_team_name) references team(team_name))'
                       )

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
            print('Tables already exists.')

        else:
            print(err.msg)

    else:
        print('OK.')


def create_games(league_name):
    cursor.execute('select team_name from team '
                   'where league_name = \"{}\"'.format(league_name))
    teams = [i[0] for i in cursor.fetchall()]

    date = datetime.date(2022, random.randint(1, 3), random.randint(1, 17))

    for home in teams:
        teams_nohome = teams.copy()
        teams_nohome.remove(home)

        for guest in teams_nohome:
            cursor.execute('select distinct arena_name '
                           'from arena join organization on '
                           'organization.home_arena = arena.arena_name join '
                           'team on team.org_name = organization.org_name '
                           'where team_name = \"{}\"'.format(home))
            arena = cursor.fetchall()

            time = str(random.randint(19, 21)) + ':' + str(random.randint(10, 55))

            refid1 = random.randint(0, 10)

            # Random ref id that's not refid1
            refid2 = choice([i for i in range(0, 10) if i not in [refid1]])

            if refid2 == 0:
                refid2 = None

            elif refid1 == 0:
                refid1 = None

            cursor.execute('insert into game'
                           '(date,time,home_team_name,guest_team_name,ref_1_id,ref_2_id,'
                           'arena_name,league_name) values (%s,%s,%s,%s,%s,%s,%s,%s)',
                           (date, time, home, guest, refid1, refid2, arena[0][0], league_name))

            # Makes sure that there is only one game per day
            date += datetime.timedelta(days=1)

    cnx.commit()


def import_data():
    print('Importing data')
    path = os.path.abspath(os.path.curdir)
    engine = create_engine('mysql+mysqlconnector://root:root@127.0.0.1/{}'.format(DB_NAME))

    # Import Referee data to a DataFrame
    referee_data = pd.read_csv(path + r'\referee.csv',
                               index_col=False,
                               delimiter=';',
                               )

    # Adds the DataFrame to the Referee table
    referee_data.to_sql('referee', con=engine, if_exists='append', chunksize=1000, index=False)

    # Repeat previous for all the other tables
    org_data = pd.read_csv(path + r'\organization.csv',
                           index_col=False,
                           delimiter=';',
                           )

    arena_data = pd.read_csv(path + r'\arena.csv',
                             index_col=False,
                             delimiter=';',
                             )

    team_data = pd.read_csv(path + r'\team.csv',
                            index_col=False,
                            delimiter=';',
                            )

    admin_data = pd.read_csv(path + r'\admin.csv',
                             index_col=False,
                             delimiter=';',
                             )

    arena_data.to_sql('arena', con=engine, if_exists='append', chunksize=1000, index=False)
    org_data.to_sql('organization', con=engine, if_exists='append', chunksize=1000, index=False)
    team_data.to_sql('team', con=engine, if_exists='append', chunksize=1000, index=False)
    admin_data.to_sql('admin', con=engine, if_exists='append', chunksize=1000, index=False)

    # Create games and add to db
    create_games('Division 1')
    create_games('Division 2')
    create_games('Division 3')


def create_views():
    print('Creating views... ', end='')
    try:
        cursor.execute('create view org_view_games as '
                       'select * from game'
                       )

        cursor.execute('create view org_view_teams as '
                       'select * from team '
                       )

    except mysql.connector.Error as err:
        print(err.msg)

    else:
        print('OK.')


def connect_to_database(cursor, DB_NAME):
    try:
        cursor.execute('use {}'.format(DB_NAME))

    except mysql.connector.Error as e:
        print('Database {} does not exist.'.format(DB_NAME))

        if e.errno == errorcode.ER_BAD_DB_ERROR:  # If database does not exist
            create_database(cursor, DB_NAME)
            cnx.database = DB_NAME  # Set the connection to our database
            create_tables(cursor)
            import_data()
            create_views()

        else:
            print(e)


def choose_user_window():
    layout = [
        [gui.Radio('Admin', group_id='radio1', key='radio_admin')],
        [gui.Radio('Organization', group_id='radio1', key='radio_org')],
        [gui.Radio('Referee', group_id='radio1', key='radio_ref')],
        [gui.Radio('League tables', group_id='radio1', key='radio_tab')],
        [gui.Button('Choose', size=30, key='btn_choose')]
    ]

    window = gui.Window('Choose user', layout)

    while True:
        event, values = window.read()

        # See if user wants to quit or window was closed
        if event == gui.WINDOW_CLOSED:
            commit_exit()

        elif values['radio_admin']:
            usr = 'Admin'
            break

        elif values['radio_org']:
            usr = 'Organization'
            break

        elif values['radio_ref']:
            usr = 'Referee'
            break

        elif values['radio_tab']:
            usr = 'Table'
            break

    window.close()
    return usr


def check_password(user_type, username, password, cursor):
    cursor.execute('select username from {} '
                   'where username = \"{}\" and '
                   'password = \"{}\"'.format(user_type, username, password)
                   )

    data = cursor.fetchall()

    if not data:
        return False
    elif data[0][0] == username:
        return True


def login_window(user_type, cursor):
    layout = [
        [gui.Text('Username')],
        [gui.Input(key='input_username', size=30)],
        [gui.Text('Password')],
        [gui.Input(key='input_password', size=30)],
        [gui.Text(size=(30, 1), key='txt')],
        [gui.Button('Login', size=10)]
    ]

    window = gui.Window('Login {}'.format(user_type), layout)

    while True:
        event, values = window.read()
        # See if user wants to quit or window was closed
        if event == gui.WINDOW_CLOSED:
            commit_exit()

        # If both input fields are not filled in
        elif values['input_username'] == '' or values['input_password'] == '':
            window['txt'].update('You must fill in both fields')

        elif event == 'Login':
            username = values['input_username']
            password = values['input_password']

            bol = check_password(user_type, username, password, cursor)

            if bol is True:
                break

            else:
                window['txt'].update('Wrong username or password.')

    window.close()
    return username, password


def update_admin_window(window, cursor):
    cursor.execute('select org_name from organization')
    orgs = create_nice_table(cursor.fetchall(), ['Org. name'])

    cursor.execute('select arena_name, address from arena')
    arenas = create_nice_table(cursor.fetchall(), ['Arena name', 'Address'])

    cursor.execute('select avg(capacity) from arena')
    avg_arena_cap = cursor.fetchone()

    arenas += '\n\nAverage arena capcaity is: ' + str(avg_arena_cap[0])

    cursor.execute('select ref_id, concat(ref_name,\" \",ref_surname) from referee')
    refs = create_nice_table(cursor.fetchall(), ['ID', 'Ref. name'])

    window['txa_org'](orgs)
    window['txa_ref'](refs)
    window['txa_arena'](arenas)


def admin_window(user_type, cursor):
    cursor.execute('select org_name from organization')
    orgs = create_nice_table(cursor.fetchall(), ['Org. name'])

    cursor.execute('select arena_name, address from arena')
    arenas = create_nice_table(cursor.fetchall(), ['Arena name', 'Address'])

    cursor.execute('select avg(capacity) from arena')
    avg_arena_cap = cursor.fetchone()

    arenas += '\n\nAverage arena capcaity is: ' + str(avg_arena_cap[0])

    cursor.execute('select ref_id, concat(ref_name,\" \",ref_surname) from referee')
    refs = create_nice_table(cursor.fetchall(), ['ID', 'Ref. name'])

    add_org = [
        [gui.Text('Organization name')],
        [gui.Input(key='input_org_name', size=30)],
        [gui.Text('Username')],
        [gui.Input(key='input_org_username', size=30)],
        [gui.Text('Password')],
        [gui.Input(key='input_org_password', size=30)],
        [gui.Text('Home arena')],
        [gui.Input(key='input_org_home_arena', size=30)],
        [gui.Button('Add org', key='btn_add_org')]
    ]

    add_ref = [
        [gui.Text('Referee name')],
        [gui.Input(key='input_ref_name', size=30)],
        [gui.Text('Referee surname')],
        [gui.Input(key='input_ref_surname', size=30)],
        [gui.Text('Username')],
        [gui.Input(key='input_ref_username', size=30)],
        [gui.Text('Password')],
        [gui.Input(key='input_ref_password', size=30)],
        [gui.Button('Add ref', key='btn_add_ref')]
    ]

    add_arena = [
        [gui.Text('Arena name')],
        [gui.Input(key='input_arena_name', size=30)],
        [gui.Text('Address')],
        [gui.Input(key='input_arena_address', size=30)],
        [gui.Text('Capacity')],
        [gui.Input(key='input_arena_capacity', size=30)],
        [gui.Button('Add arena', key='btn_add_arena')]
    ]

    layout = [
        [gui.Column(add_org), gui.VSeparator(), gui.Column(add_ref), gui.VSeparator(),
         gui.Multiline(orgs, size=(25, 15), key='txa_org'),
         gui.Multiline(refs, size=(25, 15), key='txa_ref')],
        [gui.Text('-' * 224)],
        [gui.Column(add_arena), gui.VSeparator(), gui.Multiline(arenas, size=(54, 15), key='txa_arena')]
    ]

    window = gui.Window('{} view'.format(user_type), layout)

    while True:
        event, values = window.read()
        # See if user wants to quit or window was closed
        if event == gui.WINDOW_CLOSED:
            commit_exit()

        elif event == 'btn_add_arena' and not values['input_arena_name'] == '':
            print('Added arena', values['input_arena_name'])

            cursor.execute('insert into arena '
                           '(arena_name, address, capacity) '
                           'values (%s,%s,%s)', (values['input_arena_name'],
                                                 values['input_arena_address'],
                                                 values['input_arena_capacity'])
                           )

            clear_keys(window, ['input_arena_name', 'input_arena_capacity', 'input_arena_address'])

        elif event == 'btn_add_ref' and not values['input_ref_name'] == '':
            print('Added ref', values['input_ref_name'])

            cursor.execute('insert into referee '
                           '(ref_name, ref_surname, username, password) '
                           'values (%s,%s,%s,%s)', (values['input_ref_name'],
                                                    values['input_ref_surname'],
                                                    values['input_ref_username'],
                                                    values['input_ref_password'])
                           )

            clear_keys(window, ['input_ref_name', 'input_ref_surname', 'input_ref_password', 'input_ref_username'])

        elif event == 'btn_add_org' and not values['input_org_name'] == '':
            # Check if arena exists
            cursor.execute('select exists(select * from arena '
                           'where arena_name = \"{}\")'.format(values['input_org_home_arena'])
                           )

            if cursor.fetchall() == 0:
                values['input_org_home_arena']('Arena does not exist!')
            else:
                print('Added org', values['input_org_name'])

                cursor.execute('insert into organization '
                               '(org_name, username,password,home_arena) '
                               'values (%s,%s,%s,%s)', (values['input_org_name'],
                                                        values['input_org_username'],
                                                        values['input_org_password'],
                                                        values['input_org_home_arena'])
                               )

                clear_keys(window, ['input_org_name', 'input_org_username', 'input_org_home_arena', 'input_org_password'])

        update_admin_window(window, cursor)


# Mulitline window with the games that the referee has
def update_ref_window_ref_games(cursor, ref_id):
    cursor.execute('select game_id, date, time, home_team_name,'
                   'guest_team_name, concat(score_home,\"-\",score_guest),'
                   'concat(coalesce(ref_1_id,"Nan"),\" & \",coalesce(ref_2_id,"NaN")),'
                   'arena_name, league_name '
                   'from game where ref_1_id = \"{}\" or ref_2_id = \"{}\"'.format(ref_id, ref_id))

    return create_nice_table(cursor.fetchall(), ['ID',
                                                 'Date',
                                                 'Time',
                                                 'Home',
                                                 'Guest',
                                                 'Score',
                                                 'Referees',
                                                 'Arena',
                                                 'League']
                             )


# Mulitline window with the games that do not have one or more referee(s)
def update_ref_window_games(cursor, ref_id, league_name):
    cursor.execute('select game_id, date, time, home_team_name,'
                   'guest_team_name, concat(score_home,\"-\",score_guest),'
                   'concat(coalesce(ref_1_id,"Nan"),\" & \",coalesce(ref_2_id,"NaN")),'
                   'arena_name, league_name '
                   'from game where (ref_1_id is null or ref_2_id is null) and '
                   '(league_name = \"{}\" and '
                   '(ref_1_id != {} or ref_2_id != {}))'.format(league_name, ref_id, ref_id)
                   )

    return create_nice_table(cursor.fetchall(), ['ID',
                                                 'Date',
                                                 'Time',
                                                 'Home',
                                                 'Guest',
                                                 'Score',
                                                 'Referees',
                                                 'Arena',
                                                 'League']
                             )


def ref_window(user_type, cursor, ref_id):
    cursor.execute('select distinct league_name from team')
    cmb_league_values = [i[0] for i in cursor.fetchall()]

    ref_games = update_ref_window_ref_games(cursor, ref_id)

    one = [
        [gui.Text('Leagues'), gui.Combo(cmb_league_values, key='cmb_league'), gui.Button('Select')],
        [gui.Text('Games without 2 refs in selected league: ')],
        [gui.Multiline('Select a league', size=(95, 20), key='txa_empty_games')],
        [gui.Text('Add yourself to game(id): '), gui.Input(key='input_add', size=20), gui.Button('Add')]
    ]

    two = [
        [gui.Text('Remove yourself from game(id): '), gui.Input(key='input_remove', size=20), gui.Button('Remove')],
        [gui.Text('Your games: ')],
        [gui.Multiline(ref_games, size=(95, 20), key='txa_games')]
    ]

    layout = [
        [gui.Column(one), gui.VSeparator(), gui.Column(two)]
    ]

    window = gui.Window('{} view'.format(user_type), layout)

    while True:
        event, values = window.read()
        # See if user wants to quit or window was closed
        if event == gui.WINDOW_CLOSED:
            commit_exit()

        elif event == 'Select':

            if not values['cmb_league'] == '':
                league_name = values['cmb_league']
                games = update_ref_window_games(cursor, ref_id, league_name)

                window['txa_empty_games'](games)

        elif event == 'Add' and not values['input_add'] == '':
            cursor.execute('update game '
                           'set ref_1_id = if(ref_1_id is null and ref_2_id is not null,{},ref_1_id), '
                           'ref_2_id = if(ref_1_id is not null and ref_2_id is null ,{},ref_2_id) '
                           'where game_id = {}'.format(ref_id, ref_id, values['input_add'])
                           )

            league_name = values['cmb_league']
            games = update_ref_window_games(cursor, ref_id, league_name)
            window['txa_empty_games'](games)

            ref_games = update_ref_window_ref_games(cursor, ref_id)

            window['txa_games'](ref_games)
            window['input_add']('')

        elif event == 'Remove' and not values['input_remove'] == '':
            cursor.execute('update game '
                           'set ref_1_id = if(ref_1_id = {},null,ref_1_id),'
                           'ref_2_id = if(ref_2_id = {},null,ref_2_id) '
                           'where game_id = {} '.format(ref_id, ref_id, values['input_remove'])
                           )

            league_name = values['cmb_league']
            games = update_ref_window_games(cursor, ref_id, league_name)
            window['txa_empty_games'](games)

            ref_games = update_ref_window_ref_games(cursor, ref_id)

            window['txa_games'](ref_games)
            window['input_remove']('')


def org_window(user_type, cursor, org_name):
    cursor.execute('select team_name,league_name from org_view_teams '
                   'where org_name = \"{}\"'.format(org_name)
                   )

    teams = create_nice_table(cursor.fetchall(), ['Name', 'League'])

    cursor.execute('select home_arena from organization '
                   'where org_name = \"{}\"'.format(org_name))

    home_arena = cursor.fetchall()

    cursor.execute('select game_id, date, time, home_team_name,'
                   'guest_team_name, concat(score_home,\"-\",score_guest),'
                   'concat(coalesce(ref_1_id,"NaN"),\" & \",coalesce(ref_2_id,"NaN")),'
                   'arena_name, league_name '
                   'from org_view_games '
                   'where (score_home is null or score_guest is null) and '
                   'arena_name = \"{}\"'.format(home_arena[0][0])
                   )

    games = create_nice_table(cursor.fetchall(), ['ID',
                                                  'Date',
                                                  'Time',
                                                  'Home',
                                                  'Guest',
                                                  'Score',
                                                  'Referees',
                                                  'Arena',
                                                  'League']
                              )

    one = [
        [gui.Text(org_name, size=15, font=("Helvetica", 20))],
        [gui.Text('Team name')],
        [gui.Input(key='input_team_name', size=30)],
        [gui.Text('League name')],
        [gui.Input(key='input_team_league', size=30)],
        [gui.Button('Add team', size=10)]
    ]

    two = [
        [gui.Text('Game id')],
        [gui.Input(key='input_game_id', size=30)],
        [gui.Text('Score home')],
        [gui.Input(key='input_game_score_home', size=30)],
        [gui.Text('Score guest')],
        [gui.Input(key='input_game_score_guest', size=30)],
        [gui.Button('Report game', size=10)]
    ]

    layout = [
        [gui.Column(one), gui.VSeparator(), gui.Multiline(teams, size=(30, 10), key='txa_teams')],
        [gui.Text('-' * 160)],
        [gui.Column(two), gui.VSeparator(), gui.Multiline(games, size=(95, 10), key='txa_games')]
    ]

    window = gui.Window('{} view'.format(user_type), layout)

    while True:
        event, values = window.read()
        # See if user wants to quit or window was closed
        if event == gui.WINDOW_CLOSED:
            commit_exit()

        elif event == 'Report game' and not values['input_game_score_home'] == '' \
                and not values['input_game_score_guest'] == '':
            score_h = values['input_game_score_home']
            score_g = values['input_game_score_guest']
            game_id = values['input_game_id']

            cursor.execute('update org_view_games '
                           'set score_home = {},'
                           'score_guest = {} '
                           'where game_id = {}'.format(score_h,
                                                       score_g,
                                                       game_id)
                           )

            cursor.execute('select game_id, date, time, home_team_name,'
                           'guest_team_name, concat(score_home,\"-\",score_guest),'
                           'concat(coalesce(ref_1_id,"Nan"),\" & \",coalesce(ref_2_id,"NaN")),'
                           'arena_name, league_name '
                           'from org_view_games '
                           'where (score_home is null or score_guest is null) and '
                           'arena_name = \"{}\"'.format(home_arena[0][0])
                           )

            games = create_nice_table(cursor.fetchall(), ['ID',
                                                          'Date',
                                                          'Time',
                                                          'Home',
                                                          'Guest',
                                                          'Score',
                                                          'Referees',
                                                          'Arena',
                                                          'League']
                                      )

            window['txa_games'](games)
            window['input_game_id']('')
            window['input_game_score_home']('')
            window['input_game_score_guest']('')

            # Add right amount of points to team
            cursor.execute('select home_team_name, guest_team_name '
                           'from game '
                           'where game_id = {}'.format(game_id)
                           )

            home_guest = cursor.fetchall()

            if score_h == score_g:  # tie
                cursor.execute('update org_view_teams '
                               'set league_points = league_points + 1 '
                               'where team_name = \"{}\"'.format(home_guest[0][0]))

                cursor.execute('update org_view_teams '
                               'set league_points = league_points + 1 '
                               'where team_name = \"{}\"'.format(home_guest[0][1]))

            elif score_h > score_g:  # home win
                cursor.execute('update org_view_teams '
                               'set league_points = league_points + 3 '
                               'where team_name = \"{}\"'.format(home_guest[0][0]))

            else:  # guest win
                cursor.execute('update org_view_teams '
                               'set league_points = league_points + 3 '
                               'where team_name = \"{}\"'.format(home_guest[0][1]))

        elif event == 'Add team' and not values['input_team_name'] == '':
            cursor.execute('insert into org_view_teams (team_name,org_name,league_points,league_name) '
                           'values (%s,%s,%s,%s)', (values['input_team_name'],
                                                    org_name,
                                                    0,
                                                    values['input_team_league']
                                                    )
                           )

            cursor.execute('select team_name,league_name from org_view_teams '
                           'where org_name = \"{}\"'.format(org_name)
                           )

            teams = create_nice_table(cursor.fetchall(), ['Name', 'League'])

            window['txa_teams'](teams)
            window['input_team_name']('')
            window['input_team_league']('')


def tables_window(user_type):
    cursor.execute('select distinct league_name from team')
    cmb_league_values = [i[0] for i in cursor.fetchall()]

    cursor.execute('select concat(ref_name," ",ref_surname) as name, count(ref_id) as ref_id_count '
                   'from referee join game on game.ref_1_id = referee.ref_id '
                   'or game.ref_2_id = referee.ref_id '
                   'group by name '
                   'order by ref_id_count desc '
                   'limit 1'
                   )

    ref_nr_1 = cursor.fetchall()

    layout = [
        [gui.Text('Leagues'), gui.Combo(cmb_league_values, key='cmb_league'), gui.Button('Select')],
        [gui.Text('Table for selected league:')],
        [gui.Multiline('', size=(40, 15), key='txa_table')],
        [gui.Text('Referee with the most games in all leagues:')],
        [gui.Text(str(ref_nr_1[0][0]) + ' with ' + str(ref_nr_1[0][1]) + ' games.')]
    ]

    window = gui.Window('{} view'.format(user_type), layout)

    while True:
        event, values = window.read()
        # See if user wants to quit or window was closed
        if event == gui.WINDOW_CLOSED:
            commit_exit()

        elif event == 'Select':
            if not values['cmb_league'] == '':
                league_name = values['cmb_league']

                cursor.execute('select team_name, league_points '
                               'from team '
                               'where league_name = \"{}\" '
                               'order by league_points desc'.format(league_name))

                table = create_nice_table(cursor.fetchall(), ['Team', 'Points'])

                cursor.execute('select max(league_points) - min(league_points) '
                               'from team '
                               'where league_name = \"{}\"'.format(league_name))
                diff = cursor.fetchall()

                window['txa_table'](table + '\n\nDifference in points between first and last: ' + str(diff[0][0]))


def main():
    connect_to_database(cursor, DB_NAME)

    # ref_window('Referee', cursor, 1)

    user_type = choose_user_window()

    if user_type == 'Table':
        tables_window(user_type)

    username, password = login_window(user_type, cursor)

    if user_type == 'Admin':
        admin_window(user_type, cursor)

    elif user_type == 'Referee':
        # ref_id = 1
        cursor.execute('select ref_id from referee '
                       'where username = \"{}\" and password = \"{}\"'.format(username, password)
                       )
        ref_id = cursor.fetchall()
        ref_window(user_type, cursor, int(ref_id[0][0]))

    elif user_type == 'Organization':
        # org_name = 'Växjö IBK'
        cursor.execute('select org_name from organization '
                       'where username = \"{}\" and password = \"{}\"'.format(username, password)
                       )
        org_name = cursor.fetchall()

        org_window(user_type, cursor, org_name[0][0])


if __name__ == '__main__':
    main()
