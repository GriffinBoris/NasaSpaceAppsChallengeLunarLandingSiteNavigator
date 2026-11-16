from django.test import override_settings
from django.urls import reverse


def test_index_returns_not_found_before_frontend_build(client, tmp_path):
	with override_settings(FRONTEND_DIST_DIR=tmp_path):
		response = client.get(reverse('index'))
	assert response.status_code == 404


def test_index_serves_built_frontend(client, tmp_path, settings):
	(tmp_path / 'index.html').write_text('<!doctype html><title>Built frontend</title>', encoding='utf-8')
	settings.FRONTEND_DIST_DIR = tmp_path
	settings.TEMPLATES = [{**settings.TEMPLATES[0], 'DIRS': [tmp_path]}]
	response = client.get(reverse('index'))
	assert response.status_code == 200
	assert b'<title>Built frontend</title>' in response.content


def test_missing_api_route_is_not_masked_by_spa(client):
	assert client.get('/api/does-not-exist/').status_code == 404


def test_index_serves_vite_modules_and_sets_csrf_cookie_without_a_build(client, settings, tmp_path):
	settings.FRONTEND_DEV_URL = 'http://localhost:5173'
	settings.FRONTEND_DIST_DIR = tmp_path
	response = client.get(reverse('index'))

	assert response.status_code == 200
	assert b'http://localhost:5173/static/@vite/client' in response.content
	assert b'http://localhost:5173/static/src/main.ts' in response.content
	assert 'csrftoken' in response.cookies
