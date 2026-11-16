from io import BytesIO, StringIO

import pytest
from django.core.management.base import OutputWrapper

from core.management.progress import Progress
from core.services.downloads import download_file


def test_download_finishes_atomically_and_reports_bytes(tmp_path, monkeypatch):
	response = BytesIO(b'lunar terrain')
	response.headers = {'Content-Length': '13'}
	monkeypatch.setattr('core.services.downloads.urlopen', lambda url, timeout, context: response)
	updates = []

	path = download_file(
		'https://example.com/LDEM_4.IMG', tmp_path, lambda downloaded_bytes, total_bytes: updates.append((downloaded_bytes, total_bytes))
	)

	assert path.read_bytes() == b'lunar terrain'
	assert updates == [(0, 13), (13, 13)]
	assert response.closed
	assert not path.with_suffix('.IMG.part').exists()


def test_cached_download_does_not_open_a_connection(tmp_path, monkeypatch):
	path = tmp_path / 'LDEM_4.IMG'
	path.write_bytes(b'cached terrain')

	def unexpected_request(url, timeout, context):
		raise AssertionError('A cached source must not be downloaded again.')

	monkeypatch.setattr('core.services.downloads.urlopen', unexpected_request)
	updates = []

	result = download_file(
		'https://example.com/LDEM_4.IMG', tmp_path, lambda downloaded_bytes, total_bytes: updates.append((downloaded_bytes, total_bytes))
	)

	assert result == path
	assert path.read_bytes() == b'cached terrain'
	assert updates == []


def test_short_download_removes_partial_files_and_can_be_retried(tmp_path, monkeypatch):
	response = BytesIO(b'partial')
	response.headers = {'Content-Length': '100'}
	monkeypatch.setattr('core.services.downloads.urlopen', lambda url, timeout, context: response)

	with pytest.raises(OSError, match='Incomplete download'):
		download_file('https://example.com/LDEM_4.IMG', tmp_path, lambda downloaded_bytes, total_bytes: None)

	assert list(tmp_path.iterdir()) == []
	assert response.closed

	response = BytesIO(b'complete')
	response.headers = {'Content-Length': '8'}
	path = download_file('https://example.com/LDEM_4.IMG', tmp_path, lambda downloaded_bytes, total_bytes: None)

	assert path.read_bytes() == b'complete'
	assert response.closed


def test_progress_updates_one_terminal_line_and_skips_repeated_percentages():
	class Terminal(StringIO):
		def isatty(self):
			return True

	output = Terminal()
	progress = Progress(OutputWrapper(output), 'Loading terrain')

	progress.update(0, 1000)
	progress.update(1, 1000)
	progress.update(500, 1000)
	progress.update(1000, 1000)

	assert output.getvalue() == 'Loading terrain:   0%\rLoading terrain:  50%\rLoading terrain: 100%\n'
