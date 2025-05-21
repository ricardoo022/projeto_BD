##
## =============================================
## ============== Bases de Dados ===============
## ============== LEI  2024/2025 ===============
## =============================================
## =================== Demo ====================
## =============================================
## =============================================
## === Department of Informatics Engineering ===
## =========== University of Coimbra ===========
## =============================================
##
## Authors:
##   João R. Campos <jrcampos@dei.uc.pt>
##   Nuno Antunes <nmsa@dei.uc.pt>
##   University of Coimbra


import flask
import logging
import psycopg2
import time
import random
import datetime
import jwt
from functools import wraps
import bcrypt
from dotenv import load_dotenv
import os
import re

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key') 

app = flask.Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'some_jwt_secret_key'

StatusCodes = {
    'success': 200,
    'api_error': 400,
    'internal_error': 500,
    'unauthorized': 401
}

##########################################################
## DATABASE ACCESS
##########################################################

def db_connection():
    db = psycopg2.connect(
        user='aulaspl',
        password='aulaspl',
        host='127.0.0.1',
        port='5432',
        database='dbproject'
    )

    return db

##########################################################
## AUTHENTICATION HELPERS
##########################################################

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = flask.request.headers.get('Authorization')
        logger.info(f'token: {token}')

        if not token:
            return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Token is missing!', 'results': None})

        return f(*args, **kwargs)
    return decorated


##########################################################
## REUSABLE FUNCTIONS
##########################################################

def validate_date(date_str):
    try:
        date_obj = datetime.datetime.strptime(date_str, '%d-%m-%Y')
        year, month, day = date_obj.year, date_obj.month, date_obj.day

        if year < 1900:
            return False, 'Year must be 1900 or later.'

        if month < 1 or month > 12:
            return False, 'Month must be between 1 and 12.'

        if month in [1, 3, 5, 7, 8, 10, 12] and (day < 1 or day > 31):
            return False, f'Invalid day for month {month}. Must be between 1 and 31.'
        elif month in [4, 6, 9, 11] and (day < 1 or day > 30):
            return False, f'Invalid day for month {month}. Must be between 1 and 30.'
        elif month == 2:
            is_leap_year = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
            if is_leap_year and (day < 1 or day > 29):
                return False, 'Invalid day for February in a leap year. Must be between 1 and 29.'
            elif not is_leap_year and (day < 1 or day > 28):
                return False, 'Invalid day for February in a non-leap year. Must be between 1 and 28.'

        return True, None
    except (ValueError, TypeError):
        return False, 'Invalid date format. Must be DD-MM-YYYY.'


def verify_grade(grade_array):
    conn = db_connection()
    cur = conn.cursor()

    # Verifica IDs duplicados
    student_ids = [grade[0] for grade in grade_array]
    if len(student_ids) != len(set(student_ids)):
        return False, 'Duplicate student IDs are not allowed.'
    
    # Verifica se os IDs dos estudantes existem
    for grade in grade_array:
        statment="Select person_id from student where person_id = %s"
        cur.execute(statment, (grade[0],))
        student = cur.fetchone()
        if not student:
            return False, 'Student not found.'
        if grade[1] < 0 or grade[1] > 20:
            return False, 'Invalid grade. Must be between 0 and 20.'

        statment="Select from student where n_student = %s"
        cur.execute(statment, (grade,))
        student = cur.fetchone()
        if not student:
            return False, 'Student not found.'
        date=validate_date(grade[2])
        if not date:
            return False, 'Invalid date.'

    return True, None

def post_a_person():
    data = flask.request.get_json()
    username = data.get('username')
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    district = data.get('district')
    address = data.get('address')
    birth_date = data.get('birth_date')

    if not username or not email or not password or not district or not address or not birth_date or not name:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Username, email district, address, n_student , birth_date and password are required', 'results': None})
    
    if not username or len(username) < 3:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Invalid username. Must be at least 3 characters long.', 'results': None})

    if not email or '@' not in email or '.' not in email.split('@')[-1]:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Invalid email format.', 'results': None})

    if not password or len(password) < 6:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Password must be at least 6 characters long.', 'results': None})

    if not district or len(district) < 5:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Invalid district. Must be at least 3 characters long.', 'results': None})

    if not address or len(address) < 5:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Invalid address. Must be at least 5 characters long.', 'results': None})

    is_valid, error_message = validate_date(birth_date)
    if not is_valid:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': error_message, 'results': None})

    conn = db_connection()
    cur = conn.cursor()

    person_statement = '''
    INSERT INTO Person (username, address, district, email, password, birth_date,name) 
    VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
    '''
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    person_values = (data['username'], data['address'], data['district'], data['email'], hashed_password, data['birth_date'], data['name'])

    try:
        cur.execute(person_statement, person_values)
        person_id = cur.fetchone()[0]
        conn.commit()
        return person_id
    except (Exception, psycopg2.DatabaseError) as error:
        conn.rollback()
        raise error
    finally:
        if conn is not None:
            conn.close()

def get_user_id(token):
    
    try:
        if token.startswith("Bearer "):
            token = token.split(" ")[1] 
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = decoded_token.get('id')
    except jwt.ExpiredSignatureError:
        return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Token has expired', 'results': None}), 401
    except jwt.InvalidTokenError as e:
        return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Invalid token', 'results': None}), 401

    return user_id

def is_admin(token):
    user_id = get_user_id(token)

    conn = db_connection()
    cur = conn.cursor()

    try:
        cur.execute('SELECT staff_person_id FROM admin WHERE staff_person_id = %s', (user_id,))
        if not cur.fetchone():
            return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Only admins can use this query', 'results': None}), 401
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'Error checking admin status: {error}')
        return flask.jsonify({'status': StatusCodes['internal_error'], 'errors': str(error), 'results': None}), 500
    finally:
        if conn is not None:
            conn.close()

    return user_id
 

def is_student(token):
    user_id = get_user_id(token)

    conn = db_connection()
    cur = conn.cursor()

    try:
        cur.execute('SELECT person_id FROM student WHERE person_id = %s', (user_id,))
        if not cur.fetchone():
            return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Only student can use this query', 'results': None}), 401
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'Error checking student status: {error}')
        return flask.jsonify({'status': StatusCodes['internal_error'], 'errors': str(error), 'results': None}), 500
    finally:
        if conn is not None:
            conn.close()

    return user_id


def is_coordinator(token):
    user_id = get_user_id(token)

    conn = db_connection()
    cur = conn.cursor()

    try:
        cur.execute('SELECT cordenad FROM professor WHERE staff_person_id = %s', (user_id,))
        if not cur.fetchone() or cur.fetchone()[0] == False:
            return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Only admins can use this query', 'results': None}), 401
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'Error checking admin status: {error}')
        return flask.jsonify({'status': StatusCodes['internal_error'], 'errors': str(error), 'results': None}), 500
    finally:
        if conn is not None:
            conn.close()

    return user_id


##########################################################
## ENDPOINTS
##########################################################

@app.route('/dbproj/user', methods=['PUT'])
def login_user():
    data = flask.request.get_json()
    username = data.get('username')
    password = data.get('password')
    conn = db_connection()
    cur = conn.cursor()
    if not username or not password:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Username and password are required', 'results': None})
    
    statement='SELECT id, password FROM person WHERE username=%s'
    cur.execute(statement, (username,))
    user = cur.fetchone() #fetchone vai retornar o resultado da query, a pass

    if not user:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Invalid username or password', 'results': None})

    # encriptar a pass
    user_id, stored_hash = user

    # compara a pass ja encriptada com a devolvida na query     
    if not bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Invalid username or password', 'results': None})

    # Gerar o token JWT
    payload = {
        'id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=30)  # 1 mês de validade
    }
    resultAuthToken = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

    response = {'status': StatusCodes['success'], 'errors': None, 'results': resultAuthToken}
    conn.close()
    return flask.jsonify(response)

@app.route('/dbproj/register/student', methods=['POST'])
@token_required
def register_student():
    logger.info('POST /dbproj/register/student')
    
    token = flask.request.headers.get('Authorization')

    admin_id = is_admin(token)
    if not isinstance(admin_id, int):
        return admin_id
    
    data = flask.request.get_json()
    n_student = data.get('n_student')

    conn = db_connection()
    cur = conn.cursor()

    logger.debug(f'POST /dbproj/register/student - payload: {data}')

    if not n_student:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Student number is required', 'results': None})
    
    if not n_student or not str(n_student).isdigit() or len(str(n_student)) != 10:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Invalid student number. Must be a numeric value with exactly 10 digits.', 'results': None})

    try:
        person_id = post_a_person()
        if person_id is None:
            return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Invalid person data', 'results': None})

        student_statement = '''
        INSERT INTO student (n_student, ammount, mensal_debt, person_id)
        VALUES (%s, %s, %s, %s)
        '''
        student_values = (n_student, 0.0, 0.0, person_id)

        cur.execute(student_statement, student_values)
        conn.commit()
        response = {'status': StatusCodes['success'], 'errors': None, 'results': 'Student registered successfully with ID: ' + str(person_id) + ' and student number: ' + str(n_student)}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'POST /register/student - error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}
        conn.rollback()

    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)

@app.route('/dbproj/register/staff', methods=['POST'])
@token_required
def register_staff_admin():
    logger.info('POST /dbproj/register/staff')

    token = flask.request.headers.get('Authorization')


    
    data = flask.request.get_json()
    n_staff = data.get('n_staff')

    conn = db_connection()
    cur = conn.cursor()

    logger.debug(f'POST /dbproj/register/staff - payload: {data}')

    if not n_staff:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Staff number is required', 'results': None})
    
    if not n_staff or not str(n_staff).isdigit() or len(str(n_staff)) != 10:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Invalid staff number. Must be a numeric value with exactly 10 digits.', 'results': None})

    try:
        person_id = post_a_person()

        staff_statement = '''
        INSERT INTO staff (n_staff, person_id)
        VALUES (%s, %s)
        '''
        staff_values = (n_staff, person_id)

        cur.execute(staff_statement, staff_values)

        admin_statement = '''
        INSERT INTO admin (staff_person_id)
        VALUES (%s)
        '''
        cur.execute(admin_statement, (person_id,))

        conn.commit()
        response = {'status': StatusCodes['success'], 'errors': None, 'results': 'Inserted staff with ID: ' + str(person_id) + ' and staff number: ' + str(n_staff)}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'POST /register/staff - error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}
        conn.rollback()

    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)

@app.route('/dbproj/register/instructor', methods=['POST'])
@token_required
def register_instructor():
    logger.info('POST /dbproj/register/instructor')

    token = flask.request.headers.get('Authorization')

    admin_id = is_admin(token)
    if not isinstance(admin_id, int):
        return admin_id
    
    conn = db_connection()
    cur = conn.cursor()
    
    data = flask.request.get_json()
    n_staff = data.get('n_staff')
    cordenator = data.get('cordenator')
    assistent = data.get('assistent')

    logger.debug(f'POST /dbproj/register/instructor - payload: {data}')

    if not n_staff or not cordenator is not None or not assistent is not None:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Staff number, cordenator and assistent are required', 'results': None})
    
    if not n_staff or not str(n_staff).isdigit() or len(str(n_staff)) != 10:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Invalid Staff number. Must be a numeric value with exactly 10 digits.', 'results': None})
    
    if not isinstance(cordenator, bool) or not isinstance(assistent, bool):
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'cordenator and assistent must be boolean values (true or false)', 'results': None})
    
    try:
        person_id = post_a_person()

        instructor_statement = '''
        INSERT INTO staff (n_staff, person_id)
        VALUES (%s, %s)
        '''
        instructor_values = (n_staff, person_id)

        cur = conn.cursor()
        cur.execute(instructor_statement, instructor_values)

        professor_statement = '''
        INSERT INTO professor (cordenad, asistente, staff_person_id)
        VALUES (%s, %s, %s)
        '''
        professor_values = (cordenator, assistent, person_id)
        cur.execute(professor_statement, professor_values)

        conn.commit()
        if cordenator:
            response = {'status': StatusCodes['success'], 'errors': None, 'results': 'Inserted instructor with ID: ' + str(person_id) + ' that is a cordenator'}
        else:
            response = {'status': StatusCodes['success'], 'errors': None, 'results': 'Inserted instructor with ID: ' + str(person_id) + ' that is an assistent'}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'POST /register/instructor - error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}
        conn.rollback()

    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)


@app.route('/dbproj/enroll_degree/<degree_id>', methods=['POST'])
@token_required
def enroll_degree(degree_id):

    token = flask.request.headers.get('Authorization')

    admin_id = is_admin(token)
    if not isinstance(admin_id, int):
        return admin_id
    
    data = flask.request.get_json()
    student_id = data.get('student_id')
    date = data.get('date')

    conn = db_connection()
    cur = conn.cursor()

    if not student_id or not date:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Student ID and date are required', 'results': None})
    
    is_valid, error_message = validate_date(date)
    if not is_valid:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': error_message, 'results': None})
    
    try:
        cur.execute('SELECT person_id FROM student WHERE n_student = %s', (student_id,))
        student = cur.fetchone()
        if not student:
            return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Student not found', 'results': None})
        student_person_id = student[0]

        cur.execute('SELECT id FROM degree WHERE id = %s', (degree_id,))
        if not cur.fetchone():
            return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Degree not found', 'results': None})
        
        statement= '''INSERT INTO enrollement (enroll_date, student_person_id, degree_id) VALUES (%s, %s, %s)'''
        values = (date, student_person_id, degree_id)
        cur.execute(statement, values)
        
        conn.commit()
        response = {'status': StatusCodes['success'], 'results': f'Student {student_id} enrolled in degree {degree_id}'}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'POST /enroll_degree - error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}
        conn.rollback()

    finally:
        if conn is not None:
            conn.close()
    
    return flask.jsonify(response)

@app.route('/dbproj/enroll_activity/<activity_id>', methods=['POST'])
@token_required
def enroll_activity(activity_id):
    response = {'status': StatusCodes['success'], 'errors': None}
    return flask.jsonify(response)

@app.route('/dbproj/enroll_course_edition/<course_edition_id>', methods=['POST'])
@token_required
def enroll_course_edition(course_edition_id):
    logger.info(f'POST /dbproj/enroll_course_edition/{course_edition_id}')
    
    token = flask.request.headers.get('Authorization')

    student_id = is_student(token)
    if not isinstance(student_id, int):
        return student_id   

    data = flask.request.get_json()
    classes = data.get('classes', [])

    if not classes:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'At least one class ID is required', 'results': None})

    conn = db_connection()
    cur = conn.cursor()

    try:

        logger.debug(f'Student ID: {student_id}, Classes: {classes}')

        for class_id in classes:
            # Verificar se a turma pertence à edição do curso
            cur.execute('''
                SELECT capacity, edition_id
                FROM class_time_table
                WHERE id = %s
            ''', (class_id,))
            class_info = cur.fetchone()

            if not class_info:
                return flask.jsonify({'status': StatusCodes['api_error'], 'errors': f'Class ID {class_id} does not exist', 'results': None})

            capacity, edition_id = class_info

            if edition_id != int(course_edition_id):
                return flask.jsonify({'status': StatusCodes['api_error'], 'errors': f'Class ID {class_id} does not belong to course edition {course_edition_id}', 'results': None})

            # Verificar se há capacidade disponível
            cur.execute('''
                SELECT COUNT(*) 
                FROM enrolment_class 
                WHERE class_time_table_id = %s
            ''', (class_id,))
            enrolled_count = cur.fetchone()[0]

            if enrolled_count >= int(capacity):
                return flask.jsonify({'status': StatusCodes['api_error'], 'errors': f'Class ID {class_id} is full', 'results': None})

            # Inserir na tabela enrolment_class
            cur.execute('''
                INSERT INTO enrolment_class (entry, student_person_id, class_time_table_id)
                VALUES (%s, %s, %s)
            ''', (True, student_id, class_id))

        conn.commit()
        response = {'status': StatusCodes['success'], 'errors': None, 'results': f'Successfully enrolled in classes: {classes}'}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'POST /enroll_course_edition - error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}
        conn.rollback()

    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)

@app.route('/dbproj/submit_grades/<course_edition_id>', methods=['POST'])
@token_required
def submit_grades(course_edition_id):
    token = flask.request.headers.get('Authorization')

    coordinator_id = is_coordinator(token)
    if not isinstance(coordinator_id, int):
        return coordinator_id


    data = flask.request.get_json()
    period = data.get('period')
    grades = data.get('grades', [])

    if not period or not grades:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Evaluation period and grades are required', 'results': None})
        
    is_valid, error_message = verify_grade(grades)
    if not is_valid:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': error_message, 'results': None})


    conn = db_connection()
    cur = conn.cursor()
    for grade in grades:
        student_id=grade[0]
        value=grade[1]
        date=grade[2]
        cur.execute('''insert into grade (student_person_id,period__id,date_of_degree,grade,edition_id)
        select %s,
        (select period_.id from period where name=%s and edition_id=%s),
        %s,
        %s,
        %s''',(student_id,period,course_edition_id,date,value,course_edition_id))
        
    
    
    response = {'status': StatusCodes['success'], 'errors': None}
    return flask.jsonify(response)

@app.route('/dbproj/student_details/<student_id>', methods=['GET'])
@token_required
def student_details(student_id):

    resultStudentDetails = [ # TODO
        {
            'course_edition_id': random.randint(1, 200),
            'course_name': "some course",
            'course_edition_year': 2024,
            'grade': 12
        },
        {
            'course_edition_id': random.randint(1, 200),
            'course_name': "another course",
            'course_edition_year': 2025,
            'grade': 17
        }
    ]

    response = {'status': StatusCodes['success'], 'errors': None, 'results': resultStudentDetails}
    return flask.jsonify(response)

@app.route('/dbproj/degree_details/<degree_id>', methods=['GET'])
@token_required
def degree_details(degree_id):

    token = flask.request.headers.get('Authorization')

    admin_id = is_admin(token)
    if not isinstance(admin_id, int):
        return admin_id

    conn = db_connection()
    cur = conn.cursor()

    try:
        cur.execute('''
        SELECT 
            c.id_course, 
            c.name, 
            e.id, 
            e.year_, 
            e.enroled_count, 
            e.capacity,
            
            (
            SELECT array_agg(p.id)
            FROM person p
            JOIN staff s ON p.id = s.person_id
            JOIN professor pro ON s.person_id = pro.staff_person_id
            JOIN professor_edition pe ON pro.staff_person_id = pe.professor_staff_person_id
            WHERE pro.asistente = true
            AND pe.edition_id = e.id
            ) AS assistants,
            (
            SELECT array_agg(p.id)
            FROM person p
            JOIN staff s ON p.id = s.person_id
            JOIN professor pro ON s.person_id = pro.staff_person_id
            JOIN professor_edition pe ON pro.staff_person_id = pe.professor_staff_person_id
            WHERE pro.cordenad = true
            AND pe.edition_id = e.id
            ) AS coordinator
            
        FROM degree d
        JOIN degree_course dc ON d.id = dc.degree_id
        JOIN course c ON c.id_course = dc.course_id_course
        JOIN course_edition ce ON c.id_course = ce.course_id_course
        JOIN edition e ON ce.edition_id = e.id
        WHERE d.id = %s
        ORDER BY c.id_course
        ''', (degree_id,))

        results = cur.fetchall()
        result_degree_details = []
        
        for row in results:
            course_id, course_name, edition_id, edition_year, enrolled_count, capacity, instructors, coordinator = row
            
            course_record = {
                'course_id': course_id,
                'course_name': course_name,
                'course_edition_id': edition_id,
                'course_edition_year': edition_year,
                'enrolled_count': enrolled_count,
                'capacity': capacity,
                'coordinator_id': coordinator,
                'instructors': instructors,
            }
            
            result_degree_details.append(course_record)

        response = {'status': StatusCodes['success'], 'errors': None, 'results': result_degree_details}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'GET /dbproj/degree_details - error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error), 'results': None}
        conn.rollback()

    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)

@app.route('/dbproj/top3', methods=['GET'])
@token_required
def top3_students():
    logger.info('GET /dbproj/top3')
    
    token = flask.request.headers.get('Authorization')

    admin_id = is_admin(token)
    if not isinstance(admin_id, int):
        return admin_id

    conn = db_connection()
    cur = conn.cursor()

    try:
        cur.execute('''
        SELECT 
            p.name AS student_name, 
            gd.average AS average,
            (
            SELECT (g.grade ,g.date_of_grade, e.name, e.id)
                FROM grade g
                JOIN period_ p2 ON g.period__id = p2.id
                JOIN edition e ON p2.edition_id = e.id
                JOIN course_edition ce ON e.id = ce.edition_id
                JOIN course c ON c.id_course = ce.course_id_course
                WHERE g.student_person_id = s.person_id
            ) AS grades_info,
            (
                SELECT ea.name
                FROM student_extracurriclar_activities sea
                JOIN extracurriclar_activities ea ON ea.id_activities = sea.extracurriclar_activities_id_activities
                WHERE sea.student_person_id = s.person_id
            ) AS extracurricular_activities
            
        FROM student s
        JOIN person p ON p.id = s.person_id
        JOIN grades_degree gd ON gd.student_person_id = s.person_id

        ORDER BY gd.average DESC LIMIT 3
        ''')
        
        results = cur.fetchall()
        result_top3 = []
        
        for row in results:
            student_name, average_grade, grades_tuple, activities = row
            
            grades = []
            if grades_tuple is not None:
                
                try:
                    tuple_string = str(grades_tuple)
                    tuple_string = tuple_string.strip('()')
                    
                    parts = tuple_string.split(',')

                    grade_value = int(parts[0])
                    grade_date = parts[1].strip()
                    course_name = parts[2].strip('"')
                    edition_id = int(parts[3].strip())
                    
                    grades.append({
                        'course_edition_id': edition_id,
                        'course_edition_name': course_name,
                        'grade': grade_value,
                        'date': grade_date
                    })
                except Exception as e:
                    print(f"Error parsing tuple: {tuple_string}, Error: {str(e)}")

            student_record = {
                'student_name': student_name,
                'average_grade': float(average_grade),
                'grades': grades,
                'activities': [activities] if activities else []
            }
                       
            result_top3.append(student_record)

        response = {'status': StatusCodes['success'], 'errors': None, 'results': result_top3}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'GET /dbproj/top3 - error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error), 'results': None}
        conn.rollback()

    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)

@app.route('/dbproj/top_by_district', methods=['GET'])
@token_required
def top_by_district():

    resultTopByDistrict = [ # TODO
        {
            'student_id': random.randint(1, 200),
            'district': "Coimbra",
            'average_grade': 15.2
        },
        {
            'student_id': random.randint(1, 200),
            'district': "Coimbra",
            'average_grade': 13.6
        }
    ]

    response = {'status': StatusCodes['success'], 'errors': None, 'results': resultTopByDistrict}
    return flask.jsonify(response)

@app.route('/dbproj/report', methods=['GET'])
@token_required
def monthly_report():

    resultReport = [ # TODO
        {
            'month': "month_0",
            'course_edition_id': random.randint(1, 200),
            'course_edition_name': "Some course",
            'approved': 20,
            'evaluated': 23
        },
        {
            'month': "month_1",
            'course_edition_id': random.randint(1, 200),
            'course_edition_name': "Another course",
            'approved': 200,
            'evaluated': 123
        }
    ]

    response = {'status': StatusCodes['success'], 'errors': None, 'results': resultReport}
    return flask.jsonify(response)

@app.route('/dbproj/delete_details/<student_id>', methods=['DELETE'])
@token_required
def delete_student(student_id):
    response = {'status': StatusCodes['success'], 'errors': None}

    conn = db_connection()
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM student WHERE n_student = %s', (student_id,))
        conn.commit()
        response = {'status': StatusCodes['success'], 'errors': None, 'results': 'Student deleted successfully'}
    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'DELETE /delete_details/{student_id} - error: {error}')
    return flask.jsonify(response)


if __name__ == '__main__':
    # set up logging
    logging.basicConfig(filename='log_file.log')
    logger = logging.getLogger('logger')
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter('%(asctime)s [%(levelname)s]:  %(message)s', '%H:%M:%S')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    host = '127.0.0.1'
    port = 8080
    app.run(host=host, debug=True, threaded=True, port=port)
    logger.info(f'API stubs online: http://{host}:{port}')
