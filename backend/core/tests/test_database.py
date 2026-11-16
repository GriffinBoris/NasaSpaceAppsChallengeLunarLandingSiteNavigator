from contextlib import ExitStack

import pytest
from django.db.utils import ConnectionHandler

from core.settings.base import DATABASES


@pytest.mark.django_db(transaction=True)
def test_progress_writes_can_finish_while_results_are_being_read(tmp_path):
	configuration = {
		**DATABASES['default'],
		'NAME': tmp_path / 'concurrent.sqlite3',
		'OPTIONS': {**DATABASES['default']['OPTIONS'], 'timeout': 0.1},
	}
	reader = ConnectionHandler({'default': configuration})['default']
	writer = ConnectionHandler({'default': configuration})['default']

	with ExitStack() as resources:
		resources.callback(reader.close)
		resources.callback(writer.close)

		with reader.cursor() as results, writer.cursor() as progress:
			results.execute('CREATE TABLE plan_progress (completed INTEGER)')
			results.execute('INSERT INTO plan_progress VALUES (0)')
			results.execute('BEGIN')
			results.execute('SELECT completed FROM plan_progress')
			assert results.fetchone() == (0,)

			progress.execute('UPDATE plan_progress SET completed = 1')

			results.execute('SELECT completed FROM plan_progress')
			assert results.fetchone() == (0,)
			reader.rollback()

			results.execute('SELECT completed FROM plan_progress')
			assert results.fetchone() == (1,)
