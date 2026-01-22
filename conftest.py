import pytest

@pytest.fixture(scope='session')
def db_settings():
    return {
        'host': 'your_db_host',
        'port': 'your_db_port',
        'user': 'your_db_user',
        'password': 'your_db_password',
        'database': 'your_db_name'
    }