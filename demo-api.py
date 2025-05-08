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

SECRET_KEY = 'xxx'

app = flask.Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'some_jwt_secret_key'

StatusCodes = {
    'success': 200,
    'api_error': 400,
    'internal_error': 500,
    'unauthorized': 401
}


##########################################################
## DEMO ENDPOINTS
## (the endpoints get_all_departments and add_departments serve only as examples!)
##########################################################



##########################################################
## DEMO ENDPOINTS END
##########################################################







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

@app.route('/tables', methods=['POST'])
# def create_table():


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

def post_a_person():
    data = flask.request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    district = data.get('district')
    address = data.get('address')
    birth_date = data.get('birth_date')

    if not username or not email or not password or not district or not address or not birth_date:
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
    
    try:
        birth_date_obj = datetime.datetime.strptime(birth_date, '%d-%m-%Y')
        year, month, day = birth_date_obj.year, birth_date_obj.month, birth_date_obj.day

        if year < 1900:
            return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Year must be 1900 or later.', 'results': None})

        if month < 1 or month > 12:
            return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Month must be between 1 and 12.', 'results': None})

        if month in [1, 3, 5, 7, 8, 10, 12] and (day < 1 or day > 31):
            return flask.jsonify({'status': StatusCodes['api_error'], 'errors': f'Invalid day for month {month}. Must be between 1 and 31.', 'results': None})
        elif month in [4, 6, 9, 11] and (day < 1 or day > 30):
            return flask.jsonify({'status': StatusCodes['api_error'], 'errors': f'Invalid day for month {month}. Must be between 1 and 30.', 'results': None})
        elif month == 2:
            is_leap_year = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
            if is_leap_year and (day < 1 or day > 29):
                return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Invalid day for February in a leap year. Must be between 1 and 29.', 'results': None})
            elif not is_leap_year and (day < 1 or day > 28):
                return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Invalid day for February in a non-leap year. Must be between 1 and 28.', 'results': None})

    except (ValueError, TypeError):
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Invalid birth date format. Must be DD-MM-YYYY.', 'results': None})

    conn = db_connection()
    cur = conn.cursor()

    person_statement = '''
    INSERT INTO Person (username, address, district, email, password, birth_date) 
    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
    '''
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    person_values = (data['username'], data['address'], data['district'], data['email'], hashed_password, data['birth_date'])

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
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)  # Token expira em 1 hora
    }
    resultAuthToken = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

    response = {'status': StatusCodes['success'], 'errors': None, 'results': resultAuthToken}
    conn.close()
    return flask.jsonify(response)

@app.route('/dbproj/register/student', methods=['POST'])
@token_required
def register_student():
    logger.info('POST /dbproj/register/student')

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

        student_statement = '''
        INSERT INTO student (n_student, ammount, mensal_debt, person_id)
        VALUES (%s, %s, %s, %s)
        '''
        student_values = (n_student, 0.0, 0.0, person_id)

        cur.execute(student_statement, student_values)
        conn.commit()
        response = {'status': StatusCodes['success'], 'errors': None, 'results': 'Inserted student'}

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
def register_staff():
    data = flask.request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Username, email, and password are required', 'results': None})
    
    resultUserId = random.randint(1, 200) # TODO

    response = {'status': StatusCodes['success'], 'errors': None, 'results': resultUserId}
    return flask.jsonify(response)

@app.route('/dbproj/register/instructor', methods=['POST'])
@token_required
def register_instructor():
    data = flask.request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Username, email, and password are required', 'results': None})
    
    resultUserId = random.randint(1, 200) # TODO

    response = {'status': StatusCodes['success'], 'errors': None, 'results': resultUserId}
    return flask.jsonify(response)

@app.route('/dbproj/enroll_degree/<degree_id>', methods=['POST'])
@token_required
def enroll_degree(degree_id):
    data = flask.request.get_json()
    student_id = data.get('student_id')
    date = data.get('date')

    if not student_id or not date:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Student ID and date are required', 'results': None})
    
    response = {'status': StatusCodes['success'], 'errors': None}
    return flask.jsonify(response)

@app.route('/dbproj/enroll_activity/<activity_id>', methods=['POST'])
@token_required
def enroll_activity(activity_id):
    response = {'status': StatusCodes['success'], 'errors': None}
    return flask.jsonify(response)

@app.route('/dbproj/enroll_course_edition/<course_edition_id>', methods=['POST'])
@token_required
def enroll_course_edition(course_edition_id):
    data = flask.request.get_json()
    classes = data.get('classes', [])

    if not classes:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'At least one class ID is required', 'results': None})
    
    response = {'status': StatusCodes['success'], 'errors': None}
    return flask.jsonify(response)

@app.route('/dbproj/submit_grades/<course_edition_id>', methods=['POST'])
@token_required
def submit_grades(course_edition_id):
    data = flask.request.get_json()
    period = data.get('period')
    grades = data.get('grades', [])

    if not period or not grades:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Evaluation period and grades are required', 'results': None})
    
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

    resultDegreeDetails = [ # TODO
        {
            'course_id': random.randint(1, 200),
            'course_name': "some coure",
            'course_edition_id': random.randint(1, 200),
            'course_edition_year': 2023,
            'capacity': 30,
            'enrolled_count': 27,
            'approved_count': 20,
            'coordinator_id': random.randint(1, 200),
            'instructors': [random.randint(1, 200), random.randint(1, 200)]
        }
    ]

    response = {'status': StatusCodes['success'], 'errors': None, 'results': resultDegreeDetails}
    return flask.jsonify(response)

@app.route('/dbproj/top3', methods=['GET'])
@token_required
def top3_students():

    resultTop3 = [ # TODO
        {
            'student_name': "John Doe",
            'average_grade': 15.1,
            'grades': [
                {
                    'course_edition_id': random.randint(1, 200),
                    'course_edition_name': "some course",
                    'grade': 15.1,
                    'date': datetime.datetime(2024, 5, 12)
                }
            ],
            'activities': [random.randint(1, 200), random.randint(1, 200)]
        },
        {
            'student_name': "Jane Doe",
            'average_grade': 16.3,
            'grades': [
                {
                    'course_edition_id': random.randint(1, 200),
                    'course_edition_name': "another course",
                    'grade': 15.1,
                    'date': datetime.datetime(2023, 5, 11)
                }
            ],
            'activities': [random.randint(1, 200)]
        }
    ]

    response = {'status': StatusCodes['success'], 'errors': None, 'results': resultTop3}
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
