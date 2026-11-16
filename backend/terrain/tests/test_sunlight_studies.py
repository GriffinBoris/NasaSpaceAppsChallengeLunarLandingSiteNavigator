import sqlite3
from contextlib import closing, nullcontext
from datetime import UTC, datetime
from multiprocessing import active_children
from threading import Event
from time import monotonic, sleep
from types import SimpleNamespace

import numpy
import pytest
from celery.contrib.testing.worker import start_worker
from celery.signals import worker_shutting_down
from core.celery import app
from core.tests.assertions import assert_validation_error
from django.db import transaction
from django.test import Client
from django.urls import reverse
from ephemeris.services.positions import EphemerisUnavailable
from kombu.exceptions import OperationalError

from terrain.models.SunlightFrame import SunlightFrame
from terrain.models.SunlightHorizon import SunlightHorizon
from terrain.models.SunlightPreparation import SunlightPreparation
from terrain.models.SunlightResult import SunlightResult
from terrain.models.SunlightSelection import SunlightSelection
from terrain.models.SunlightStudy import SunlightStudy
from terrain.models.TerrainDataset import TerrainDataset
from terrain.services.horizon_profile import HORIZON_BIN_COUNT, HORIZON_VERSION, HorizonProfile
from terrain.services.illumination import calculate_visibility
from terrain.services.illumination_patch import DEFAULT_RADIUS_METERS, PATCH_GRID_SIZE
from terrain.services.site_area import TERRAIN_GRID_SIZE
from terrain.services.study_calculation import iter_study
from terrain.services.study_jobs import process_study, publish_study, stop_study
from terrain.services.study_schedule import timestamps
from terrain.services.sunlight_processing import SunlightProcessor
from terrain.tasks import calculate_study

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def serial_study_workers(monkeypatch):
	def processor(dataset_id, locations, workers, geometry=None):
		return SunlightProcessor(dataset_id, locations, workers=1, geometry=geometry)

	monkeypatch.setattr('terrain.services.study_calculation.SunlightProcessor', processor)


@pytest.fixture(autouse=True)
def queued_studies(monkeypatch):
	queued = []
	monkeypatch.setattr('terrain.services.study_jobs.publish_study', lambda study_id, run_id: queued.append((study_id, str(run_id))))

	return queued


def run_study(study_id):
	study = SunlightStudy.objects.get(pk=study_id)
	calculate_study.run(study_id, str(study.run_id))


def stop_when(monkeypatch, condition):
	def events(study):
		for event in iter_study(study):
			yield event

			if condition(study):
				stop_study(study.pk, study.run_id)

	monkeypatch.setattr('terrain.services.study_jobs.iter_study', events)


def selection_url(selection_id=None):
	if selection_id is None:
		return reverse('terrain:selections:sunlight-selection-list')

	return reverse('terrain:selections:sunlight-selection-detail', kwargs={'selection_id': selection_id})


def study_url(study_id=None):
	if study_id is None:
		return reverse('terrain:studies:sunlight-study-list')

	return reverse('terrain:studies:sunlight-study-detail', kwargs={'study_id': study_id})


@pytest.fixture
def saved_selection():
	return SunlightSelection.objects.create(name='Rim', latitude=0, longitude=0, radius_meters=None)


@pytest.fixture
def study_parameters(analysis_dataset, saved_selection):
	return {
		'name': 'Morning',
		'dataset_id': analysis_dataset.pk,
		'selection_ids': [saved_selection.pk],
		'start_time': '2026-11-11T12:00:00Z',
		'end_time': '2026-11-11T12:10:00Z',
		'step_seconds': 300,
	}


@pytest.fixture
def fake_sun(monkeypatch):
	monkeypatch.setattr('terrain.services.study_calculation.kernel_signature', lambda: 'a' * 64)
	vector = numpy.array([149600000000.0, 0, 0])
	monkeypatch.setattr('terrain.services.illumination.calculate_surface_sun', lambda timestamp, position: (vector, 695700000.0))
	monkeypatch.setattr(
		'terrain.services.illumination_patch.calculate_surface_suns', lambda timestamp, positions: ([vector] * len(positions), 695700000.0)
	)
	monkeypatch.setattr('terrain.services.illumination_patch.PATCH_GRID_SIZE', 3)
	monkeypatch.setattr('terrain.services.study_calculation.loaded_ephemeris', lambda timestamp: nullcontext())
	monkeypatch.setattr(
		'terrain.services.study_calculation.calculate_surface_suns', lambda timestamp, positions: ([vector] * len(positions), 695700000.0)
	)
	monkeypatch.setattr(
		'terrain.services.study_calculation.calculate_surface_earths',
		lambda timestamp, positions: ([numpy.array([384400000.0, 0, 0])] * len(positions), 6371000.0),
	)


def test_selections_persist_rename_and_delete_without_authentication(client):
	response = client.post(
		selection_url(), {'name': 'Landing region', 'latitude': -89.9, 'longitude': 180, 'radius_meters': 2500}, content_type='application/json'
	)

	assert response.status_code == 201
	selection_id = response.data['id']
	assert SunlightSelection.objects.get(pk=selection_id).radius_meters == 2500

	response = client.patch(selection_url(selection_id), {'name': 'Renamed rim'}, content_type='application/json')

	assert response.status_code == 200
	assert client.get(selection_url()).data['selections'][0]['name'] == 'Renamed rim'
	assert client.delete(selection_url(selection_id)).status_code == 204
	assert not SunlightSelection.objects.exists()


@pytest.mark.parametrize(
	('field', 'value', 'expected_code'),
	[
		('latitude', 91, 'max_value'),
		('longitude', -181, 'min_value'),
		('radius_meters', 0, 'min_value'),
		('radius_meters', 50001, 'max_value'),
		('name', '', 'blank'),
		('latitude', 'NaN', 'invalid'),
		('radius_meters', 'NaN', 'invalid'),
	],
)
def test_selection_rejects_invalid_input(client, field, value, expected_code):
	data = {'name': 'Point', 'latitude': 0, 'longitude': 0, 'radius_meters': None, field: value}
	response = client.post(selection_url(), data, content_type='application/json')
	assert_validation_error(response, field, expected_code)
	assert not SunlightSelection.objects.exists()


def test_browser_mutations_require_csrf_cookie_and_header(saved_selection):
	client = Client(enforce_csrf_checks=True)
	url = selection_url(saved_selection.pk)

	assert client.patch(url, {'name': 'Blocked'}, content_type='application/json').status_code == 403
	assert client.delete(url).status_code == 403

	response = client.get(selection_url())
	csrf_token = response.cookies['csrftoken'].value
	response = client.patch(url, {'name': 'Allowed'}, content_type='application/json', HTTP_X_CSRFTOKEN=csrf_token)

	assert response.status_code == 200
	assert response.data['name'] == 'Allowed'
	assert client.post(study_url(), {}, content_type='application/json').status_code == 403
	assert (
		client.post(reverse('terrain:studies:sunlight-study-calculate', kwargs={'study_id': 1}), {}, content_type='application/json').status_code
		== 403
	)
	assert client.post(reverse('terrain:studies:sunlight-study-stop', kwargs={'study_id': 1})).status_code == 403


def test_study_pins_selection_geometry_names_and_dataset(client, study_parameters, saved_selection):
	response = client.post(study_url(), study_parameters, content_type='application/json')

	assert response.status_code == 201
	assert response.data['expected_frames'] == 2
	assert response.data['completed_frames'] == 0
	assert response.data['start_time'] == '2026-11-11T12:00:00Z'
	assert response.data['end_time'] == '2026-11-11T12:10:00Z'
	study_id = response.data['id']

	saved_selection.name = 'Changed'
	saved_selection.latitude = 45
	saved_selection.save()
	saved_selection.delete()
	stored = client.get(study_url(study_id)).data['study']

	assert stored['selections'][0]['name'] == 'Rim'
	assert stored['selections'][0]['latitude'] == 0
	assert stored['dataset_id'] == study_parameters['dataset_id']
	assert stored['worker_count'] == 4


@pytest.mark.parametrize('worker_count', [1, 2, 4, 8, 16])
def test_plan_keeps_and_uses_the_selected_worker_count(client, study_parameters, fake_sun, monkeypatch, worker_count):
	study_parameters['worker_count'] = worker_count
	response = client.post(study_url(), study_parameters, content_type='application/json')
	assert response.status_code == 201
	assert response.data['worker_count'] == worker_count
	assert SunlightStudy.objects.get(pk=response.data['id']).worker_count == worker_count
	client.post(reverse('terrain:studies:sunlight-study-stop', kwargs={'study_id': response.data['id']}))
	continued = client.generic('POST', reverse('terrain:studies:sunlight-study-calculate', kwargs={'study_id': response.data['id']}), data=b'')
	assert continued.data['worker_count'] == worker_count
	received_workers = []

	def processor(dataset_id, locations, workers, geometry=None):
		received_workers.append(workers)
		return SunlightProcessor(dataset_id, locations, workers=1, geometry=geometry)

	monkeypatch.setattr('terrain.services.study_calculation.SunlightProcessor', processor)
	run_study(response.data['id'])

	assert received_workers == [worker_count]
	assert client.get(study_url(response.data['id'])).data['study']['worker_count'] == worker_count


@pytest.mark.parametrize('worker_count', [0, 3, 9, 1.5])
def test_calculate_rejects_invalid_workers_without_queueing(client, study_parameters, queued_studies, worker_count):
	study = client.post(study_url(), study_parameters, content_type='application/json').data
	client.post(reverse('terrain:studies:sunlight-study-stop', kwargs={'study_id': study['id']}))
	queued_count = len(queued_studies)
	response = client.post(
		reverse('terrain:studies:sunlight-study-calculate', kwargs={'study_id': study['id']}),
		{'worker_count': worker_count},
		content_type='application/json',
	)

	assert_validation_error(response, 'worker_count', 'invalid_choice')
	assert 'worker_count' in str(response.data)
	assert len(queued_studies) == queued_count
	assert SunlightStudy.objects.get(pk=study['id']).status == 'stopped'
	assert SunlightStudy.objects.get(pk=study['id']).worker_count == 4


def test_continuing_can_change_workers_and_keep_completed_results(client, study_parameters, fake_sun, monkeypatch):
	study = client.post(study_url(), study_parameters, content_type='application/json').data
	stop_when(monkeypatch, lambda current: current.frames.exists())
	run_study(study['id'])
	saved_frames = list(SunlightFrame.objects.filter(study_id=study['id']).values_list('id', flat=True))
	assert len(saved_frames) == 1
	response = client.post(
		reverse('terrain:studies:sunlight-study-calculate', kwargs={'study_id': study['id']}), {'worker_count': 16}, content_type='application/json'
	)

	assert response.status_code == 202
	assert response.data['worker_count'] == 16
	assert list(SunlightFrame.objects.filter(study_id=study['id']).values_list('id', flat=True)) == saved_frames
	monkeypatch.setattr('terrain.services.study_jobs.iter_study', iter_study)
	run_study(study['id'])

	assert SunlightStudy.objects.get(pk=study['id']).status == 'complete'
	assert SunlightFrame.objects.filter(study_id=study['id']).count() == 2
	assert SunlightFrame.objects.filter(pk=saved_frames[0]).exists()


def test_worker_choices_and_default_come_from_the_api(client):
	response = client.get(selection_url())

	assert response.data['worker_options'] == [
		{'value': 1, 'label': '1 worker'},
		{'value': 2, 'label': '2 workers'},
		{'value': 4, 'label': '4 workers'},
		{'value': 8, 'label': '8 workers'},
		{'value': 16, 'label': '16 workers'},
	]
	assert response.data['default_worker_count'] == 4


@pytest.mark.parametrize(
	('field', 'value', 'expected_code'),
	[
		('selection_ids', [], 'empty'),
		('selection_ids', [999999], 'invalid'),
		('step_seconds', 120, 'invalid_choice'),
		('worker_count', 0, 'invalid_choice'),
		('worker_count', 3, 'invalid_choice'),
		('worker_count', 9, 'invalid_choice'),
		('end_time', '2026-11-11T12:00:00Z', 'invalid'),
		('end_time', '2026-11-11T11:00:00Z', 'invalid'),
	],
)
def test_study_rejects_invalid_schedule_before_writing(client, study_parameters, field, value, expected_code):
	study_parameters[field] = value
	response = client.post(study_url(), study_parameters, content_type='application/json')
	assert_validation_error(response, field, expected_code)
	assert not SunlightStudy.objects.exists()


def test_create_accepts_more_than_4096_results(client, study_parameters, queued_studies):
	study_parameters['end_time'] = '2026-11-15T12:00:00Z'
	study_parameters['step_seconds'] = 60

	response = client.post(study_url(), study_parameters, content_type='application/json')

	assert response.status_code == 201
	study = SunlightStudy.objects.get(pk=response.data['id'])
	assert study.expected_frames == 5760
	assert study.status == SunlightStudy.Status.QUEUED
	assert queued_studies == [(study.pk, str(study.run_id))]
	assert not SunlightFrame.objects.exists()


def test_edit_accepts_more_than_4096_results(client, study_parameters, queued_studies):
	study = client.post(study_url(), study_parameters, content_type='application/json').data
	client.post(reverse('terrain:studies:sunlight-study-stop', kwargs={'study_id': study['id']}))
	study_parameters['end_time'] = '2026-11-15T12:00:00Z'
	study_parameters['step_seconds'] = 60
	queued_count = len(queued_studies)

	response = client.put(study_url(study['id']), study_parameters, content_type='application/json')

	assert response.status_code == 200
	stored = SunlightStudy.objects.get(pk=study['id'])
	assert stored.expected_frames == 5760
	assert stored.status == SunlightStudy.Status.QUEUED
	assert queued_studies[queued_count:] == [(stored.pk, str(stored.run_id))]
	assert not SunlightFrame.objects.exists()


def test_study_rejects_duplicate_selections_and_loading_datasets(client, study_parameters, saved_selection, analysis_dataset):
	study_parameters['selection_ids'] = [saved_selection.pk, saved_selection.pk]

	response = client.post(study_url(), study_parameters, content_type='application/json')
	assert_validation_error(response, 'selection_ids', 'invalid')

	study_parameters['selection_ids'] = [saved_selection.pk]
	analysis_dataset.status = TerrainDataset.Status.LOADING
	analysis_dataset.save()

	response = client.post(study_url(), study_parameters, content_type='application/json')
	assert_validation_error(response, 'dataset_id', 'does_not_exist')


def test_schedule_is_utc_and_end_exclusive():
	result = timestamps(datetime(2026, 11, 11, 12, tzinfo=UTC), datetime(2026, 11, 11, 12, 11, tzinfo=UTC), 300)

	assert [timestamp.minute for timestamp in result] == [0, 5, 10]
	assert all(timestamp.tzinfo == UTC for timestamp in result)


def test_create_queues_multiple_plans_without_running_them(client, study_parameters, queued_studies):
	first = client.post(study_url(), study_parameters, content_type='application/json')
	second = client.post(study_url(), study_parameters, content_type='application/json')

	assert first.status_code == second.status_code == 201
	assert first.data['status'] == second.data['status'] == 'queued'
	assert {message[0] for message in queued_studies} == {first.data['id'], second.data['id']}
	assert len({message[1] for message in queued_studies}) == 2
	assert not SunlightFrame.objects.exists()
	assert client.get(study_url()).status_code == 200
	assert (
		client.post(
			reverse('terrain:studies:sunlight-study-calculate', kwargs={'study_id': first.data['id']}), {}, content_type='application/json'
		).status_code
		== 409
	)
	response = client.post(
		reverse('terrain:studies:sunlight-study-calculate', kwargs={'study_id': first.data['id']}),
		{'worker_count': 8},
		content_type='application/json',
	)
	assert response.status_code == 409
	assert SunlightStudy.objects.get(pk=first.data['id']).worker_count == 4
	assert client.delete(study_url(first.data['id'])).status_code == 409


def test_queue_waits_for_commit_and_does_not_publish_rolled_back_plans(client, study_parameters, queued_studies):
	with transaction.atomic():
		response = client.post(study_url(), study_parameters, content_type='application/json')

		assert response.status_code == 201
		assert queued_studies == []

	assert len(queued_studies) == 1

	with transaction.atomic():
		client.post(study_url(), study_parameters, content_type='application/json')
		transaction.set_rollback(True)

	assert len(queued_studies) == 1
	assert SunlightStudy.objects.count() == 1


def test_multiple_points_and_regions_save_frames_and_persist_progress(client, study_parameters, fake_sun, monkeypatch, django_assert_num_queries):
	monkeypatch.setattr('terrain.services.illumination_patch.PATCH_GRID_SIZE', 5)
	region = SunlightSelection.objects.create(name='Region', latitude=0, longitude=0, radius_meters=1250)
	study_parameters['selection_ids'].append(region.pk)
	study = client.post(study_url(), study_parameters, content_type='application/json').data

	run_study(study['id'])

	with django_assert_num_queries(4):
		detail = Client().get(study_url(study['id'])).data

	assert detail['study']['status'] == 'complete'
	assert detail['study']['completed_frames'] == 4
	assert detail['study']['progress']['percentage'] == 100
	assert detail['study']['error_message'] == ''
	assert len(detail['frames']) == 4
	assert all('result' not in frame for frame in detail['frames'])
	assert all('earth_result' not in frame for frame in detail['frames'])

	region_frame = next(frame for frame in detail['frames'] if frame['selection_id'] == region.pk)
	point_frame = next(frame for frame in detail['frames'] if frame['selection_id'] != region.pk)
	assert point_frame['thumbnail'] is None
	assert point_frame['earth_thumbnail'] is None
	assert region_frame['thumbnail']['grid_size'] == 3
	assert region_frame['earth_thumbnail'] == {'grid_size': 3, 'fractions': [None, 1, None, 1, 1, 1, None, 1, None]}
	assert region_frame['visible_sun_fraction'] == 1

	url = reverse('terrain:studies:sunlight-frame-detail', kwargs={'study_id': study['id'], 'frame_id': region_frame['id']})
	frame = client.get(url).data

	assert frame['timestamp'] == '2026-11-11T12:00:00Z'
	assert frame['earth_thumbnail'] == region_frame['earth_thumbnail']
	assert frame['result']['patch']['radius_meters'] == 1250
	assert frame['result']['center']['dataset_id'] == study_parameters['dataset_id']
	assert frame['result']['center']['timestamp'] == '2026-11-11T12:00:00Z'
	assert (
		client.post(
			reverse('terrain:studies:sunlight-study-calculate', kwargs={'study_id': study['id']}), {}, content_type='application/json'
		).status_code
		== 409
	)


def test_stop_retains_frames_and_resume_skips_saved_results(client, study_parameters, fake_sun, monkeypatch):
	study = client.post(study_url(), study_parameters, content_type='application/json').data
	stop_when(monkeypatch, lambda current: current.frames.exists())

	run_study(study['id'])

	stored_id = SunlightFrame.objects.get(study_id=study['id']).pk
	assert SunlightStudy.objects.get(pk=study['id']).status == 'stopped'
	monkeypatch.setattr('terrain.services.study_jobs.iter_study', iter_study)
	response = client.post(reverse('terrain:studies:sunlight-study-calculate', kwargs={'study_id': study['id']}), {}, content_type='application/json')

	assert response.status_code == 202
	assert response.data['completed_frames'] == 0
	run_study(study['id'])

	assert SunlightFrame.objects.filter(study_id=study['id']).count() == 2
	assert SunlightFrame.objects.filter(pk=stored_id).exists()
	assert SunlightStudy.objects.get(pk=study['id']).status == 'complete'


@pytest.mark.parametrize('radius_meters', [None, 1250])
def test_new_plans_reuse_results_after_the_source_plan_is_deleted(client, study_parameters, saved_selection, fake_sun, monkeypatch, radius_meters):
	saved_selection.radius_meters = radius_meters
	saved_selection.save()
	first = client.post(study_url(), study_parameters, content_type='application/json').data
	run_study(first['id'])
	first_frames = list(SunlightFrame.objects.filter(study_id=first['id']))
	cached_ids = [frame.cached_result_id for frame in first_frames]
	expected = [frame.calculation_result for frame in first_frames]
	assert all(frame.result is None for frame in first_frames)
	assert SunlightPreparation.objects.count() == 1
	assert SunlightResult.objects.count() == 2
	assert client.delete(study_url(first['id'])).status_code == 204

	alias = SunlightSelection.objects.create(name='Another name', latitude=0, longitude=0, radius_meters=radius_meters)
	study_parameters['selection_ids'] = [alias.pk]
	study_parameters['worker_count'] = 8

	def fail_calculation(*arguments, **keywords):
		raise AssertionError('Saved sunlight must be reused without terrain reads, SPICE calculations, or worker startup.')

	monkeypatch.setattr('terrain.services.terrain_surface.TerrainSurface.surface_point', fail_calculation)
	monkeypatch.setattr('terrain.services.study_calculation.calculate_surface_suns', fail_calculation)
	monkeypatch.setattr('terrain.services.study_calculation.SunlightProcessor', fail_calculation)
	second = client.post(study_url(), study_parameters, content_type='application/json').data

	run_study(second['id'])

	stored = SunlightStudy.objects.get(pk=second['id'])
	frames = list(stored.frames.all())
	assert stored.status == SunlightStudy.Status.COMPLETE
	assert stored.progress['percentage'] == 100
	assert 'reused saved Earth visibility' in stored.progress['stage']
	assert [frame.cached_result_id for frame in frames] == cached_ids
	assert all(frame.selection_id == alias.pk and frame.result is None for frame in frames)
	assert SunlightResult.objects.count() == 2
	url = reverse('terrain:studies:sunlight-frame-detail', kwargs={'study_id': stored.pk, 'frame_id': frames[0].pk})
	assert client.get(url).data['result'] == expected[0]


def test_overlapping_plan_calculates_only_missing_timestamps(client, study_parameters, fake_sun, monkeypatch):
	first = client.post(study_url(), study_parameters, content_type='application/json').data
	run_study(first['id'])
	shared_id = SunlightFrame.objects.get(study_id=first['id'], timestamp='2026-11-11T12:05:00Z').cached_result_id
	calculated_times = []

	def calculate_suns(timestamp, positions):
		calculated_times.append(timestamp)

		return [numpy.array([149600000000.0, 0, 0])] * len(positions), 695700000.0

	monkeypatch.setattr('terrain.services.study_calculation.calculate_surface_suns', calculate_suns)
	study_parameters['start_time'] = '2026-11-11T12:05:00Z'
	study_parameters['end_time'] = '2026-11-11T12:15:00Z'
	second = client.post(study_url(), study_parameters, content_type='application/json').data

	run_study(second['id'])

	assert calculated_times == [datetime(2026, 11, 11, 12, 10, tzinfo=UTC)]
	assert SunlightResult.objects.count() == 3
	assert SunlightFrame.objects.get(study_id=second['id'], timestamp='2026-11-11T12:05:00Z').cached_result_id == shared_id
	assert SunlightStudy.objects.get(pk=second['id']).status == SunlightStudy.Status.COMPLETE


@pytest.mark.parametrize('changed_input', ['ephemeris', 'calculation_version'])
def test_changed_calculation_inputs_recompute_shared_results(client, study_parameters, fake_sun, monkeypatch, changed_input):
	first = client.post(study_url(), study_parameters, content_type='application/json').data
	run_study(first['id'])
	first_ids = set(SunlightFrame.objects.filter(study_id=first['id']).values_list('cached_result_id', flat=True))

	if changed_input == 'ephemeris':
		monkeypatch.setattr('terrain.services.study_calculation.kernel_signature', lambda: 'b' * 64)
	else:
		monkeypatch.setattr('terrain.services.sunlight_result_cache.CALCULATION_VERSION', 2)

	second = client.post(study_url(), study_parameters, content_type='application/json').data

	run_study(second['id'])

	second_ids = set(SunlightFrame.objects.filter(study_id=second['id']).values_list('cached_result_id', flat=True))
	assert SunlightStudy.objects.get(pk=second['id']).status == SunlightStudy.Status.COMPLETE
	assert first_ids.isdisjoint(second_ids)
	assert SunlightPreparation.objects.count() == 1
	assert SunlightResult.objects.count() == 4


def test_legacy_frame_payloads_remain_readable(client, study_parameters):
	study = client.post(study_url(), study_parameters, content_type='application/json').data
	payload = {'center': {'visible_sun_fraction': 0.25}, 'patch': None}
	frame = SunlightFrame.objects.create(
		study_id=study['id'],
		selection_id=study_parameters['selection_ids'][0],
		timestamp=study_parameters['start_time'],
		visible_sun_fraction=0.25,
		result=payload,
	)

	response = client.get(reverse('terrain:studies:sunlight-frame-detail', kwargs={'study_id': study['id'], 'frame_id': frame.pk}))

	assert response.status_code == 200
	assert response.data['result'] == payload
	assert frame.cached_result_id is None


def test_stopping_queued_plan_and_old_messages_do_not_restart_it(client, study_parameters, fake_sun, queued_studies):
	study = client.post(study_url(), study_parameters, content_type='application/json').data
	old_run_id = queued_studies[0][1]
	response = client.post(reverse('terrain:studies:sunlight-study-stop', kwargs={'study_id': study['id']}))

	assert response.status_code == 200
	assert response.data['status'] == 'stopped'
	calculate_study.run(study['id'], old_run_id)
	assert not SunlightFrame.objects.exists()
	assert (
		client.post(
			reverse('terrain:studies:sunlight-study-calculate', kwargs={'study_id': study['id']}), {}, content_type='application/json'
		).status_code
		== 202
	)

	calculate_study.run(study['id'], old_run_id)
	stop_study(study['id'], old_run_id)

	assert SunlightStudy.objects.get(pk=study['id']).status == 'queued'
	assert not SunlightFrame.objects.exists()
	run_study(study['id'])
	assert SunlightStudy.objects.get(pk=study['id']).status == 'complete'


def test_running_stop_waits_for_cleanup_before_allowing_continue_or_delete(client, study_parameters, fake_sun, monkeypatch):
	study = client.post(study_url(), study_parameters, content_type='application/json').data

	def request_stop(current):
		response = client.post(reverse('terrain:studies:sunlight-study-stop', kwargs={'study_id': current.pk}))

		assert response.data['status'] == 'stopping'
		assert (
			client.post(
				reverse('terrain:studies:sunlight-study-calculate', kwargs={'study_id': current.pk}), {}, content_type='application/json'
			).status_code
			== 409
		)
		assert client.delete(study_url(current.pk)).status_code == 409

		return True

	stop_when(monkeypatch, request_stop)
	run_study(study['id'])

	assert SunlightStudy.objects.get(pk=study['id']).status == 'stopped'
	assert not SunlightFrame.objects.exists()
	assert client.delete(study_url(study['id'])).status_code == 204


def test_duplicate_delivery_and_deleted_jobs_are_ignored(client, study_parameters, fake_sun, monkeypatch):
	study = client.post(study_url(), study_parameters, content_type='application/json').data
	run_study(study['id'])

	def fail_calculation(study):
		raise AssertionError('Completed work must not be repeated.')

	monkeypatch.setattr('terrain.services.study_jobs.iter_study', fail_calculation)
	run_study(study['id'])
	assert SunlightFrame.objects.count() == 2
	run_id = SunlightStudy.objects.get(pk=study['id']).run_id
	assert client.delete(study_url(study['id'])).status_code == 204

	process_study(study['id'], str(run_id))
	assert not SunlightStudy.objects.exists()


def test_cancel_during_preparation_retains_completed_horizons_for_resume(client, study_parameters, fake_sun, monkeypatch):
	study_parameters['end_time'] = '2026-11-12T09:20:00Z'
	study = client.post(study_url(), study_parameters, content_type='application/json').data
	stop_when(monkeypatch, lambda current: SunlightHorizon.objects.exists())

	run_study(study['id'])

	assert SunlightHorizon.objects.count() == 1
	assert SunlightStudy.objects.get(pk=study['id']).complete_frames().count() == 1
	assert SunlightStudy.objects.get(pk=study['id']).status == 'stopped'
	monkeypatch.setattr('terrain.services.study_jobs.iter_study', iter_study)

	def fail_build(*arguments):
		raise AssertionError('Resuming must reuse the completed horizon.')

	monkeypatch.setattr('terrain.services.horizon_builder.HorizonBuilder.build', fail_build)
	assert (
		client.post(
			reverse('terrain:studies:sunlight-study-calculate', kwargs={'study_id': study['id']}), {}, content_type='application/json'
		).status_code
		== 202
	)
	run_study(study['id'])

	assert SunlightStudy.objects.get(pk=study['id']).status == 'complete'
	assert SunlightHorizon.objects.count() == 1
	assert SunlightFrame.objects.count() == 256


def test_first_paired_frame_is_available_while_remaining_horizons_are_prepared(client, study_parameters, saved_selection, fake_sun, monkeypatch):
	saved_selection.radius_meters = 1000
	saved_selection.save()
	study_parameters['end_time'] = '2026-11-12T09:20:00Z'
	study = client.post(study_url(), study_parameters, content_type='application/json').data
	stop_when(monkeypatch, lambda current: SunlightHorizon.objects.exists())

	run_study(study['id'])

	stored = client.get(study_url(study['id'])).data['study']
	assert stored['completed_frames'] == 1
	assert stored['progress'] == {
		'completed': 1,
		'total': 5,
		'percentage': 20,
		'stage': 'Rim: preparing remaining terrain and horizons, 1 of 5',
		'phase': 'preparing',
	}


def test_failed_study_keeps_completed_frames_and_returns_safe_error(client, study_parameters, fake_sun, monkeypatch):
	def fail_after_first_frame(*arguments):
		if SunlightFrame.objects.exists():
			raise RuntimeError('internal details')

		return calculate_visibility(*arguments)

	monkeypatch.setattr('terrain.services.sunlight_samples.calculate_visibility', fail_after_first_frame)
	study = client.post(study_url(), study_parameters, content_type='application/json').data

	with pytest.raises(RuntimeError, match='internal details'):
		run_study(study['id'])

	stored = client.get(study_url(study['id'])).data['study']
	assert stored['status'] == 'failed'
	assert stored['completed_frames'] == 1
	assert 'internal details' not in stored['error_message']
	assert stored['error_message']


def test_missing_ephemeris_fails_before_expensive_horizon_preparation(client, study_parameters, fake_sun, monkeypatch):
	study_parameters['end_time'] = '2026-11-12T09:20:00Z'

	def unavailable(timestamp):
		raise EphemerisUnavailable('SPICE data is missing.')

	monkeypatch.setattr('terrain.services.study_calculation.loaded_ephemeris', unavailable)
	study = client.post(study_url(), study_parameters, content_type='application/json').data

	with pytest.raises(EphemerisUnavailable):
		run_study(study['id'])

	stored = client.get(study_url(study['id'])).data['study']
	assert stored['status'] == 'failed'
	assert stored['error_message'] == 'SPICE data is missing.'
	assert not SunlightHorizon.objects.exists()
	assert not SunlightFrame.objects.exists()


def test_queue_failure_is_visible_and_can_be_retried(client, study_parameters, monkeypatch):
	def unavailable(*arguments, **keywords):
		raise OperationalError('private connection details')

	monkeypatch.setattr('terrain.services.study_jobs.publish_study', publish_study)
	monkeypatch.setattr(calculate_study, 'apply_async', unavailable)
	client.raise_request_exception = False
	response = client.post(study_url(), study_parameters, content_type='application/json')

	assert response.status_code == 503
	assert 'private connection details' not in str(response.data)
	study = SunlightStudy.objects.get()
	assert study.status == 'failed'
	assert 'Redis' in study.error_message
	assert not SunlightFrame.objects.exists()
	queued = []
	monkeypatch.setattr(calculate_study, 'apply_async', lambda **keywords: queued.append(keywords))
	response = client.post(reverse('terrain:studies:sunlight-study-calculate', kwargs={'study_id': study.pk}), {}, content_type='application/json')

	assert response.status_code == 202
	assert response.data['error_message'] == ''
	assert len(queued) == 1
	assert queued[0]['args'] == [study.pk, queued[0]['task_id']]


def test_frame_detail_is_scoped_to_the_full_study_identity(client, study_parameters, fake_sun):
	first = client.post(study_url(), study_parameters, content_type='application/json').data
	second = client.post(study_url(), study_parameters, content_type='application/json').data
	run_study(first['id'])
	frame = SunlightFrame.objects.filter(study_id=first['id']).first()

	assert client.get(reverse('terrain:studies:sunlight-frame-detail', kwargs={'study_id': second['id'], 'frame_id': frame.pk})).status_code == 404
	assert client.delete(study_url(first['id'])).status_code == 204
	assert not SunlightFrame.objects.exists()


def test_saved_dataset_version_is_available_independently_of_current_catalog(client, analysis_dataset):
	url = reverse('terrain:dataset:terrain-version-detail', kwargs={'dataset_id': analysis_dataset.pk})

	assert client.get(url).data['id'] == analysis_dataset.pk

	analysis_dataset.status = TerrainDataset.Status.LOADING
	analysis_dataset.save()

	assert client.get(url).status_code == 404


def test_real_workers_save_and_resume_only_in_parent(client, study_parameters, saved_selection, worker_database, fake_sun, monkeypatch):
	saved_selection.radius_meters = 1250
	saved_selection.save()

	def processor(dataset_id, locations, workers, geometry=None):
		return SunlightProcessor(dataset_id, locations, workers=workers, database=worker_database, geometry=geometry)

	monkeypatch.setattr('terrain.services.study_calculation.SunlightProcessor', processor)
	previous_children = {child.pid for child in active_children()}
	study = client.post(study_url(), study_parameters, content_type='application/json').data
	stop_when(monkeypatch, lambda current: current.frames.exists())
	run_study(study['id'])

	assert SunlightStudy.objects.get(pk=study['id']).status == 'stopped'
	assert SunlightFrame.objects.filter(study_id=study['id']).count() == 1
	assert {child.pid for child in active_children()} <= previous_children
	monkeypatch.setattr('terrain.services.study_jobs.iter_study', iter_study)
	assert (
		client.post(
			reverse('terrain:studies:sunlight-study-calculate', kwargs={'study_id': study['id']}), {}, content_type='application/json'
		).status_code
		== 202
	)
	run_study(study['id'])

	assert SunlightStudy.objects.get(pk=study['id']).status == 'complete'
	assert SunlightFrame.objects.filter(study_id=study['id']).count() == 2
	assert {child.pid for child in active_children()} <= previous_children

	with sqlite3.connect(worker_database['NAME']) as stored:
		assert stored.execute('SELECT COUNT(*) FROM terrain_sunlightframe').fetchone()[0] == 0
		assert stored.execute('SELECT COUNT(*) FROM terrain_sunlighthorizon').fetchone()[0] == 0


def test_failed_preparation_does_not_publish_partial_horizons(client, study_parameters, fake_sun, monkeypatch):
	study_parameters['end_time'] = '2026-11-12T09:20:00Z'

	def fail_build(*arguments):
		raise RuntimeError('Failed preparation')

	monkeypatch.setattr('terrain.services.horizon_builder.HorizonBuilder.build', fail_build)
	study = client.post(study_url(), study_parameters, content_type='application/json').data

	with pytest.raises(RuntimeError, match='Failed preparation'):
		run_study(study['id'])

	assert SunlightStudy.objects.get(pk=study['id']).status == 'failed'
	assert not SunlightHorizon.objects.exists()
	assert SunlightStudy.objects.get(pk=study['id']).complete_frames().count() == 1


def test_one_day_study_traces_without_building_missing_horizons(client, study_parameters, fake_sun, monkeypatch):
	study_parameters['end_time'] = '2026-11-12T12:00:00Z'
	study_parameters['step_seconds'] = 900

	def fail_build(*arguments):
		raise AssertionError('One cold day should use direct tracing.')

	monkeypatch.setattr('terrain.services.horizon_builder.HorizonBuilder.build', fail_build)
	study = client.post(study_url(), study_parameters, content_type='application/json').data
	run_study(study['id'])

	assert SunlightStudy.objects.get(pk=study['id']).status == 'complete'
	assert SunlightFrame.objects.count() == 96
	assert not SunlightHorizon.objects.exists()


def test_celery_thread_worker_runs_spawned_open3d_processes(client, study_parameters, saved_selection, worker_database, fake_sun, monkeypatch):
	saved_selection.radius_meters = 1250
	saved_selection.save()

	def processor(dataset_id, locations, workers, geometry=None):
		return SunlightProcessor(dataset_id, locations, workers=workers, database=worker_database, geometry=geometry)

	monkeypatch.setattr('terrain.services.study_calculation.SunlightProcessor', processor)
	monkeypatch.setattr('terrain.services.study_jobs.publish_study', publish_study)
	previous_children = {child.pid for child in active_children()}

	with start_worker(app, pool=app.conf.worker_pool, concurrency=app.conf.worker_concurrency, perform_ping_check=False, shutdown_timeout=15):
		study = client.post(study_url(), study_parameters, content_type='application/json').data
		deadline = monotonic() + 15

		while monotonic() < deadline:
			stored = SunlightStudy.objects.get(pk=study['id'])

			if stored.status in ['complete', 'failed']:
				break

			sleep(0.05)

		assert stored.status == 'complete', stored.error_message
		assert stored.progress['percentage'] == 100
		assert SunlightFrame.objects.filter(study=stored).count() == 2

	assert {child.pid for child in active_children()} <= previous_children


def test_worker_shutdown_only_stops_its_current_run(client, study_parameters, monkeypatch):
	assert calculate_study.acks_late

	owned = client.post(study_url(), study_parameters, content_type='application/json').data
	queued = client.post(study_url(), study_parameters, content_type='application/json').data
	current = SunlightStudy.objects.get(pk=owned['id'])
	SunlightStudy.objects.filter(pk=current.pk).update(status='running')
	requests = [
		SimpleNamespace(name=calculate_study.name, args=[current.pk, str(current.run_id)]),
		SimpleNamespace(name='another.task', args=[queued['id']]),
	]
	monkeypatch.setattr('terrain.tasks.active_requests', requests)

	responses = worker_shutting_down.send(sender='worker', sig='SIGTERM', how='Warm', exitcode=0)

	assert all(response is None for receiver, response in responses)
	assert SunlightStudy.objects.get(pk=current.pk).status == 'stopping'
	assert SunlightStudy.objects.get(pk=queued['id']).status == 'queued'


def test_real_worker_shutdown_keeps_completed_frames_and_closes_processes(
	client, study_parameters, saved_selection, worker_database, fake_sun, monkeypatch
):
	saved_selection.radius_meters = 1250
	saved_selection.save()
	paused = Event()
	release = Event()

	def processor(dataset_id, locations, workers, geometry=None):
		return SunlightProcessor(dataset_id, locations, workers=workers, database=worker_database, geometry=geometry)

	def pause_after_frame(study):
		with closing(iter_study(study)) as events:
			for event in events:
				yield event

				if study.frames.exists():
					paused.set()
					assert release.wait(10)

	monkeypatch.setattr('terrain.services.study_calculation.SunlightProcessor', processor)
	monkeypatch.setattr('terrain.services.study_jobs.iter_study', pause_after_frame)
	monkeypatch.setattr('terrain.services.study_jobs.publish_study', publish_study)
	previous_children = {child.pid for child in active_children()}

	with start_worker(
		app, pool=app.conf.worker_pool, concurrency=app.conf.worker_concurrency, perform_ping_check=False, shutdown_timeout=15
	) as worker:
		study = client.post(study_url(), study_parameters, content_type='application/json').data

		try:
			assert paused.wait(10)
			queued = client.post(study_url(), study_parameters, content_type='application/json').data
			worker_shutting_down.send(sender='worker', sig='SIGTERM', how='Warm', exitcode=0)
		finally:
			release.set()

		worker.stop()
		deadline = monotonic() + 10

		while monotonic() < deadline:
			stored = SunlightStudy.objects.get(pk=study['id'])

			if stored.status in ['stopped', 'failed', 'complete']:
				break

			sleep(0.05)

		assert stored.status == 'stopped', stored.error_message
		assert SunlightFrame.objects.filter(study=stored).count() == 1
		assert SunlightStudy.objects.get(pk=queued['id']).status == 'queued'

		with app.connection_for_write() as broker:
			broker.default_channel.queue_delete(queue=app.conf.task_default_queue)

	assert {child.pid for child in active_children()} <= previous_children


def test_edit_keeps_fitting_results_and_queues_only_missing_work(client, study_parameters, fake_sun, queued_studies):
	study = client.post(study_url(), study_parameters, content_type='application/json').data
	run_study(study['id'])
	kept_ids = set(SunlightFrame.objects.filter(study_id=study['id']).values_list('pk', flat=True))
	added = SunlightSelection.objects.create(name='Ridge', latitude=1, longitude=1, radius_meters=None)
	edit = {**study_parameters, 'name': 'Longer', 'selection_ids': [*study_parameters['selection_ids'], added.pk], 'end_time': '2026-11-11T12:15:00Z'}

	response = client.put(study_url(study['id']), edit, content_type='application/json')

	assert response.status_code == 200
	assert response.data['name'] == 'Longer'
	assert response.data['status'] == 'queued'
	assert response.data['expected_frames'] == 6
	assert response.data['completed_frames'] == 2
	assert queued_studies[-1][0] == study['id']
	run_study(study['id'])
	assert SunlightFrame.objects.filter(study_id=study['id']).count() == 6
	assert kept_ids <= set(SunlightFrame.objects.filter(study_id=study['id']).values_list('pk', flat=True))
	assert SunlightStudy.objects.get(pk=study['id']).status == 'complete'


def test_edit_removing_sites_or_times_drops_their_results_without_queueing(client, study_parameters, fake_sun, queued_studies):
	study = client.post(study_url(), study_parameters, content_type='application/json').data
	run_study(study['id'])
	queued_count = len(queued_studies)
	edit = {**study_parameters, 'end_time': '2026-11-11T12:05:00Z'}

	response = client.put(study_url(study['id']), edit, content_type='application/json')

	assert response.status_code == 200
	assert response.data['status'] == 'complete'
	assert response.data['completed_frames'] == 1
	assert len(queued_studies) == queued_count


def test_rename_keeps_status_results_and_pinned_geometry_of_deleted_sites(client, study_parameters, saved_selection, queued_studies):
	study = client.post(study_url(), study_parameters, content_type='application/json').data
	client.post(reverse('terrain:studies:sunlight-study-stop', kwargs={'study_id': study['id']}))
	saved_selection.delete()
	queued_count = len(queued_studies)

	response = client.put(study_url(study['id']), {**study_parameters, 'name': 'Renamed'}, content_type='application/json')

	assert response.status_code == 200
	assert response.data['status'] == 'stopped'
	assert response.data['selections'][0]['name'] == 'Rim'
	assert len(queued_studies) == queued_count
	response = client.put(study_url(study['id']), {**study_parameters, 'selection_ids': [999999]}, content_type='application/json')
	assert_validation_error(response, 'selection_ids', 'invalid')

	response = client.put(study_url(study['id']), {**study_parameters, 'end_time': '2026-11-11T11:00:00Z'}, content_type='application/json')
	assert_validation_error(response, 'end_time', 'invalid')
	assert SunlightStudy.objects.get(pk=study['id']).name == 'Renamed'


def test_edit_is_rejected_while_a_plan_is_queued(client, study_parameters):
	study = client.post(study_url(), study_parameters, content_type='application/json').data

	response = client.put(study_url(study['id']), {**study_parameters, 'name': 'Late'}, content_type='application/json')

	assert response.status_code == 409
	assert SunlightStudy.objects.get(pk=study['id']).name == 'Morning'


def test_site_terrain_samples_the_plans_pinned_area_on_a_grid_aligned_with_sunlight_maps(client, study_parameters, saved_selection, analysis_dataset):
	region = SunlightSelection.objects.create(name='Crater', latitude=0, longitude=0, radius_meters=1250)
	study_parameters['selection_ids'].append(region.pk)
	study = client.post(study_url(), study_parameters, content_type='application/json').data
	region_id = region.pk
	region.delete()

	region_terrain = client.get(
		reverse('terrain:studies:sunlight-study-site-terrain', kwargs={'study_id': study['id'], 'selection_id': region_id})
	).data
	point_terrain = client.get(
		reverse('terrain:studies:sunlight-study-site-terrain', kwargs={'study_id': study['id'], 'selection_id': saved_selection.pk})
	).data

	assert region_terrain['grid_size'] == TERRAIN_GRID_SIZE
	assert (TERRAIN_GRID_SIZE - 1) % (PATCH_GRID_SIZE - 1) == 0
	assert len(region_terrain['heights_meters']) == TERRAIN_GRID_SIZE**2
	assert region_terrain['radius_meters'] == 1250
	assert region_terrain['spacing_meters'] == 2500 / (TERRAIN_GRID_SIZE - 1)
	assert point_terrain['radius_meters'] == DEFAULT_RADIUS_METERS
	assert region_terrain['reference_radius_meters'] == analysis_dataset.reference_radius
	assert (
		client.get(reverse('terrain:studies:sunlight-study-site-terrain', kwargs={'study_id': study['id'], 'selection_id': 999999})).status_code
		== 404
	)


def test_site_directions_give_sun_and_earth_angles_for_every_time_in_the_plan(client, study_parameters, saved_selection, monkeypatch):
	study = client.post(study_url(), study_parameters, content_type='application/json').data
	scheduled = []

	def body_directions(times, position):
		scheduled.extend(times)

		return {'SUN': [numpy.array([0.0, 1, 0]) * 1.5e11 for _ in times], 'EARTH': [numpy.array([0.0, 0, 1]) * 3.8e8 for _ in times]}

	monkeypatch.setattr('terrain.services.surface_directions.calculate_surface_body_series', body_directions)

	response = client.get(
		reverse('terrain:studies:sunlight-study-site-directions', kwargs={'study_id': study['id'], 'selection_id': saved_selection.pk})
	)

	assert response.status_code == 200
	assert set(response.data) == {'selection_id', 'sun', 'earth'}
	assert [timestamp.minute for timestamp in scheduled] == [0, 5]
	assert response.data['sun']['azimuth_degrees'] == [90, 90]
	assert response.data['sun']['elevation_degrees'] == [0, 0]
	assert response.data['earth']['azimuth_degrees'] == [0, 0]
	assert response.data['earth']['elevation_degrees'] == [0, 0]
	scheduled.clear()
	assert (
		client.get(reverse('terrain:studies:sunlight-study-site-directions', kwargs={'study_id': study['id'], 'selection_id': 999999})).status_code
		== 404
	)
	assert scheduled == []


def test_site_horizon_preserves_bounds_and_uses_pinned_coordinates(client, study_parameters, saved_selection, analysis_dataset):
	study = client.post(study_url(), study_parameters, content_type='application/json').data
	lower = numpy.full(HORIZON_BIN_COUNT, numpy.radians(2.0))
	upper = numpy.full(HORIZON_BIN_COUNT, numpy.radians(3.0))
	lower[1] = numpy.radians(-4.0)
	upper[7] = numpy.radians(14.0)
	upper[-1] = numpy.radians(17.0)
	SunlightHorizon.objects.create(
		dataset=analysis_dataset, latitude=0, longitude=0, version=HORIZON_VERSION, data=HorizonProfile(lower, upper).encode()
	)
	saved_selection.latitude = 10
	saved_selection.save()
	selection_id = saved_selection.pk
	saved_selection.delete()

	response = client.get(reverse('terrain:studies:sunlight-study-site-horizon', kwargs={'study_id': study['id'], 'selection_id': selection_id}))

	assert response.status_code == 200
	assert set(response.data) == {'selection_id', 'azimuth_offset_degrees', 'bounds'}
	assert response.data['selection_id'] == selection_id
	assert response.data['azimuth_offset_degrees'] == pytest.approx(0)
	assert len(response.data['bounds']['lower_elevation_degrees']) == 512
	assert response.data['bounds']['lower_elevation_degrees'][0] == pytest.approx(-4)
	assert response.data['bounds']['upper_elevation_degrees'][0] == pytest.approx(14)
	assert response.data['bounds']['upper_elevation_degrees'][-1] == pytest.approx(17)
	assert SunlightHorizon.objects.count() == 1


def test_site_horizon_does_not_prepare_missing_or_outdated_profiles(client, study_parameters, saved_selection, analysis_dataset):
	study = client.post(study_url(), study_parameters, content_type='application/json').data
	SunlightHorizon.objects.create(
		dataset=analysis_dataset, latitude=0, longitude=0, version=HORIZON_VERSION + 1, data=HorizonProfile.unresolved().encode()
	)
	url = reverse('terrain:studies:sunlight-study-site-horizon', kwargs={'study_id': study['id'], 'selection_id': saved_selection.pk})

	response = client.get(url)

	assert response.status_code == 200
	assert response.data['bounds'] is None
	assert SunlightHorizon.objects.count() == 1
	assert (
		client.get(reverse('terrain:studies:sunlight-study-site-horizon', kwargs={'study_id': study['id'], 'selection_id': 999999})).status_code
		== 404
	)
	assert (
		client.get(
			reverse('terrain:studies:sunlight-study-site-horizon', kwargs={'study_id': 999999, 'selection_id': saved_selection.pk})
		).status_code
		== 404
	)


@pytest.mark.parametrize('latitude,expected_offset', [(90, 90), (-90, 270)])
def test_site_horizon_aligns_polar_profiles_with_geographic_azimuth(
	client, study_parameters, saved_selection, analysis_dataset, latitude, expected_offset
):
	saved_selection.latitude = latitude
	saved_selection.longitude = 90
	saved_selection.save()
	study = client.post(study_url(), study_parameters, content_type='application/json').data
	SunlightHorizon.objects.create(
		dataset=analysis_dataset, latitude=latitude, longitude=90, version=HORIZON_VERSION, data=HorizonProfile.unresolved().encode()
	)

	response = client.get(
		reverse('terrain:studies:sunlight-study-site-horizon', kwargs={'study_id': study['id'], 'selection_id': saved_selection.pk})
	)

	assert response.status_code == 200
	assert response.data['azimuth_offset_degrees'] == pytest.approx(expected_offset)
	assert response.data['bounds'] is None
