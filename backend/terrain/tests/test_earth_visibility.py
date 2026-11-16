import json
from contextlib import nullcontext
from types import SimpleNamespace

import numpy
import pytest
from core.tests.assertions import assert_validation_error
from django.urls import reverse

from terrain.models.EarthVisibilityResult import EarthVisibilityResult
from terrain.models.SunlightFrame import SunlightFrame
from terrain.models.SunlightPreparation import SunlightPreparation
from terrain.models.SunlightSelection import SunlightSelection
from terrain.models.SunlightStudy import SunlightStudy
from terrain.services import study_calculation
from terrain.services.earth_visibility import calculate_earth_visibility
from terrain.services.study_calculation import joint_grid
from terrain.services.study_jobs import stop_study
from terrain.services.surface_mesh import SurfaceMesh
from terrain.services.terrain_surface import TerrainSurface
from terrain.tasks import calculate_study

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def earth_inputs(analysis_dataset, monkeypatch):
	selection = SunlightSelection.objects.create(name='Rim', latitude=0, longitude=0, radius_meters=None)
	vector = numpy.array([384400000.0, 0, 0])
	monkeypatch.setattr('terrain.services.study_jobs.publish_study', lambda *arguments: None)
	monkeypatch.setattr('terrain.services.study_calculation.loaded_ephemeris', lambda timestamp: nullcontext())
	monkeypatch.setattr('terrain.services.study_calculation.kernel_signature', lambda: 'a' * 64)
	monkeypatch.setattr(
		'terrain.services.study_calculation.calculate_surface_suns', lambda timestamp, positions: ([vector * 400] * len(positions), 695700000.0)
	)
	monkeypatch.setattr(
		'terrain.services.study_calculation.calculate_surface_earths', lambda timestamp, positions: ([vector] * len(positions), 6371000.0)
	)
	monkeypatch.setattr(
		'terrain.services.earth_visibility.calculate_surface_earths', lambda timestamp, positions: ([vector] * len(positions), 6371000.0)
	)
	monkeypatch.setattr('terrain.services.illumination_patch.PATCH_GRID_SIZE', 3)

	return {
		'name': 'Earth windows',
		'dataset_id': analysis_dataset.pk,
		'selection_ids': [selection.pk],
		'start_time': '2026-11-11T12:00:00Z',
		'end_time': '2026-11-11T12:10:00Z',
		'step_seconds': 300,
		'worker_count': 1,
	}


def run_plan(study_id):
	study = SunlightStudy.objects.get(pk=study_id)
	calculate_study.run(study.pk, str(study.run_id))


@pytest.mark.parametrize('direction,expected', [(1, 1), (-1, 0)])
def test_earth_visibility_obeys_terrain_obstruction(analysis_dataset, direction, expected):
	surface = TerrainSurface(analysis_dataset, SurfaceMesh)
	position, normal, _ = surface.surface_point(0, 0)
	visibility = calculate_earth_visibility(surface, position, normal, numpy.array([direction * 384400000.0, 0, 0]), 6371000.0)

	assert visibility['visible_earth_fraction'] == expected
	assert visibility['earth_center_visible'] == bool(expected)
	assert visibility['earth_angular_radius_degrees'] == pytest.approx(0.9496506, abs=0.001)
	assert visibility['sampling_converged'] is True


def test_partial_earth_disk_is_distinct_from_center_visibility():
	class HorizonPlane:
		def blocked_rays(self, origin, directions):
			return directions[:, 2] <= 0

	visibility = calculate_earth_visibility(HorizonPlane(), numpy.zeros(3), numpy.array([0.0, 0, 1]), numpy.array([384400000.0, 0, 0]), 6371000.0)

	assert visibility['visible_earth_fraction'] == pytest.approx(0.5, abs=0.005)
	assert visibility['earth_center_visible'] is False


def test_plans_always_store_and_reuse_sunlight_and_earth_results(client, earth_inputs, monkeypatch):
	url = reverse('terrain:studies:sunlight-study-list')
	first = client.post(url, earth_inputs, content_type='application/json')
	assert first.status_code == 201
	run_plan(first.data['id'])
	study = SunlightStudy.objects.get(pk=first.data['id'])
	assert study.status == 'complete'
	frames = list(study.frames.all())
	assert len(frames) == 2
	assert all(frame.visible_earth_fraction == 1 and frame.earth_center_visible for frame in frames)
	assert all(frame.visible_sun_fraction == 1 for frame in frames)
	assert all(frame.joint_visible_share == 1 for frame in frames)
	assert client.get(reverse('terrain:studies:sunlight-study-detail', kwargs={'study_id': study.pk})).data['study']['completed_frames'] == 2
	assert EarthVisibilityResult.objects.count() == 2
	assert SunlightPreparation.objects.count() == 1

	def fail_calculation(*arguments, **keywords):
		raise AssertionError('Matching results must be reused.')

	monkeypatch.setattr('terrain.services.study_calculation.SunlightProcessor', fail_calculation)
	monkeypatch.setattr('terrain.services.study_calculation.calculate_surface_earths', fail_calculation)
	second = client.post(url, earth_inputs, content_type='application/json').data
	run_plan(second['id'])
	assert SunlightStudy.objects.get(pk=second['id']).status == 'complete'
	assert EarthVisibilityResult.objects.count() == 2
	frame = SunlightFrame.objects.filter(study_id=second['id']).first()
	response = client.get(reverse('terrain:studies:sunlight-frame-detail', kwargs={'study_id': second['id'], 'frame_id': frame.pk}))
	assert response.data['earth_result']['center']['earth_elevation_degrees'] == pytest.approx(90)
	assert response.data['result']['center']['visible_sun_fraction'] == 1


def test_continuing_an_older_plan_preserves_sunlight_and_adds_missing_earth(client, earth_inputs, monkeypatch):
	created = client.post(reverse('terrain:studies:sunlight-study-list'), earth_inputs, content_type='application/json').data
	run_plan(created['id'])
	study = SunlightStudy.objects.get(pk=created['id'])
	original_ids = list(study.frames.values_list('cached_result_id', flat=True))
	study.frames.update(cached_earth_result=None, visible_earth_fraction=None, earth_center_visible=None, joint_visible_share=None)
	EarthVisibilityResult.objects.all().delete()
	SunlightStudy.objects.filter(pk=study.pk).update(status='pending')

	response = client.post(reverse('terrain:studies:sunlight-study-calculate', kwargs={'study_id': study.pk}), {}, content_type='application/json')
	assert response.status_code == 202
	assert response.data['completed_frames'] == 0

	def fail_sunlight(*arguments):
		raise AssertionError('Existing sunlight must not be recalculated.')

	monkeypatch.setattr('terrain.services.study_calculation.calculate_surface_suns', fail_sunlight)
	run_plan(study.pk)
	study.refresh_from_db()
	assert study.status == 'complete'
	assert list(study.frames.values_list('cached_result_id', flat=True)) == original_ids
	assert EarthVisibilityResult.objects.count() == 2


def test_joint_visibility_requires_co_located_sunlight_and_earth_visibility():
	frame = SimpleNamespace(
		cached_result_id=1,
		cached_earth_result_id=2,
		cached_result=SimpleNamespace(
			preparation_id=3,
			ephemeris_signature='matching',
			result={'patch': {'points': [{'visible_sun_fraction': 1}, {'visible_sun_fraction': 0}, None]}},
		),
		cached_earth_result=SimpleNamespace(
			preparation_id=3,
			ephemeris_signature='matching',
			result={'patch': {'points': [{'earth_center_visible': False}, {'earth_center_visible': True}, None]}},
		),
	)

	assert joint_grid(frame) == [0, 0, None]
	frame.cached_earth_result.ephemeris_signature = 'different'
	assert joint_grid(frame) is None


def test_earth_point_endpoint_uses_public_validated_observer_coordinates(client, analysis_dataset, earth_inputs):
	url = reverse('terrain:earth:earth-visibility-detail', kwargs={'dataset_id': analysis_dataset.pk})
	parameters = {'timestamp': '2026-11-11T12:00:00Z', 'latitude': 0, 'longitude': 0}
	response = client.get(url, parameters)

	assert response.status_code == 200
	assert response.data['earth_center_visible'] is True
	assert response.data['visible_earth_fraction'] == 1
	assert response.data['timestamp'] == '2026-11-11T12:00:00Z'
	assert 'visible_sun_fraction' not in response.data
	response = client.get(url, {**parameters, 'latitude': 91})
	assert_validation_error(response, 'latitude', 'max_value')


def test_earth_region_stream_preserves_the_circle_and_reports_progress(client, analysis_dataset, earth_inputs):
	url = reverse('terrain:earth:earth-visibility-patch-detail', kwargs={'dataset_id': analysis_dataset.pk})
	parameters = {'timestamp': '2026-11-11T12:00:00Z', 'latitude': 0, 'longitude': 0, 'radius_meters': 250}
	response = client.get(url, parameters)
	assert response.status_code == 200
	events = [json.loads(line) for line in b''.join(response.streaming_content).splitlines()]
	assert events[-2]['progress']['percentage'] == 100
	patch = events[-1]['result']
	assert patch['grid_size'] == 3
	assert [index for index, point in enumerate(patch['points']) if point is not None] == [1, 3, 4, 5, 7]
	assert all(point['visible_earth_fraction'] == 1 for point in patch['points'] if point is not None)
	assert patch['center']['earth_center_visible'] is True
	assert EarthVisibilityResult.objects.count() == 0


@pytest.mark.parametrize('changed_identity', ['ephemeris', 'version'])
def test_earth_cache_requires_matching_kernels_and_calculation_version(client, earth_inputs, monkeypatch, changed_identity):
	url = reverse('terrain:studies:sunlight-study-list')
	first = client.post(url, earth_inputs, content_type='application/json').data
	run_plan(first['id'])

	if changed_identity == 'ephemeris':
		monkeypatch.setattr('terrain.services.study_calculation.kernel_signature', lambda: 'b' * 64)
	else:
		monkeypatch.setattr('terrain.services.earth_result_cache.EARTH_CALCULATION_VERSION', 2)

	second = client.post(url, earth_inputs, content_type='application/json').data
	run_plan(second['id'])
	assert SunlightStudy.objects.get(pk=second['id']).status == 'complete'
	assert EarthVisibilityResult.objects.count() == 4
	assert SunlightPreparation.objects.count() == 1


def test_combined_plan_resumes_without_replacing_completed_results(client, earth_inputs, monkeypatch):
	created = client.post(reverse('terrain:studies:sunlight-study-list'), earth_inputs, content_type='application/json').data
	original_save = study_calculation.save_frame

	def save_and_stop(study, selection, result, body):
		frame = original_save(study, selection, result, body)

		if body == 'EARTH':
			stop_study(study.pk, study.run_id)

		return frame

	monkeypatch.setattr(study_calculation, 'save_frame', save_and_stop)
	run_plan(created['id'])
	study = SunlightStudy.objects.get(pk=created['id'])
	assert study.status == 'stopped'
	summary = client.get(reverse('terrain:studies:sunlight-study-detail', kwargs={'study_id': study.pk})).data['study']
	assert summary['completed_frames'] == 1
	assert summary['saved_results'] == 2

	original_frame_ids = list(study.frames.values_list('pk', 'cached_result_id', 'cached_earth_result_id'))
	monkeypatch.setattr(study_calculation, 'save_frame', original_save)
	response = client.post(reverse('terrain:studies:sunlight-study-calculate', kwargs={'study_id': study.pk}), {}, content_type='application/json')
	assert response.status_code == 202
	run_plan(study.pk)
	study.refresh_from_db()
	assert study.status == 'complete'
	assert study.complete_frames().count() == 2
	assert (
		list(study.frames.filter(pk=original_frame_ids[0][0]).values_list('pk', 'cached_result_id', 'cached_earth_result_id')) == original_frame_ids
	)
	assert EarthVisibilityResult.objects.count() == 2
