import pytest
from django.conf import settings


@pytest.fixture(scope='session')
def django_db_modify_db_settings(tmp_path_factory):
	settings.DATABASES['default']['TEST']['NAME'] = str(tmp_path_factory.mktemp('database') / 'test.sqlite3')
