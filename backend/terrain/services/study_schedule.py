from datetime import timedelta
from math import ceil

STEP_OPTIONS = [
	(60, '1 minute'),
	(300, '5 minutes'),
	(900, '15 minutes'),
	(1800, '30 minutes'),
	(3600, '1 hour'),
	(21600, '6 hours'),
	(86400, '1 day'),
]


def timestamps(start_time, end_time, step_seconds):
	count = ceil((end_time - start_time).total_seconds() / step_seconds)

	return [start_time + timedelta(seconds=index * step_seconds) for index in range(count)]
