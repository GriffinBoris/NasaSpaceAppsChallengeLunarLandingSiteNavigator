from datetime import UTC, datetime, timedelta
from io import StringIO

import pytest
from core.tests.assertions import assert_validation_error
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse

from terrain.models.SunlightFrame import SunlightFrame
from terrain.models.SunlightPreparation import SunlightPreparation
from terrain.models.SunlightStudy import SunlightStudy
from terrain.services.earth_result_cache import EarthResultCache
from terrain.services.illumination_patch import patch_locations
from terrain.services.joint_visibility import joint_fractions
from terrain.services.site_combined_visibility import rebuild_combined_visibility
from terrain.services.study_calculation import save_frame
from terrain.services.sunlight_result_cache import SunlightResultCache
from terrain.services.terrain_surface import TerrainAnalysisUnavailable

pytestmark = pytest.mark.django_db


@pytest.fixture
def combined_study(analysis_dataset):
	selection = {'id': 7, 'name': 'Rim', 'latitude': -89, 'longitude': 40, 'radius_meters': 1000}
	start = datetime(2026, 11, 14, 23, 30, tzinfo=UTC)
	study = SunlightStudy.objects.create(
		name='Combined map',
		dataset=analysis_dataset,
		selections=[selection],
		start_time=start,
		end_time=start + timedelta(minutes=100),
		step_seconds=3600,
		expected_frames=2,
	)
	locations = patch_locations(-89, 40, 1000, analysis_dataset.reference_radius, grid_size=5)
	preparation_samples = []

	for location in locations:
		if location is None:
			preparation_samples.append(None)
			continue

		latitude, longitude = location
		preparation_samples.append({'latitude': latitude, 'longitude': longitude})

	preparation = SunlightPreparation.objects.create(
		dataset=analysis_dataset,
		latitude=-89,
		longitude=40,
		radius_meters=1000,
		grid_size=5,
		version=1,
		samples=preparation_samples,
	)
	sunlight_cache = SunlightResultCache(preparation, 'a' * 64)
	earth_cache = EarthResultCache(preparation, 'a' * 64)

	for index, timestamp in enumerate([start, start + timedelta(hours=1)]):
		sunlight_points = []
		earth_points = []

		for point_index, location in enumerate(locations):
			if location is None:
				sunlight_points.append(None)
				earth_points.append(None)
				continue

			sunlight_points.append({'visible_sun_fraction': 1 if point_index in (12, 14) else 0})
			earth_points.append({'visible_earth_fraction': 1, 'earth_center_visible': point_index == 12 or (index == 0 and point_index == 14)})

		patch = {'grid_size': 5, 'radius_meters': 1000, 'spacing_meters': 500}
		sunlight = sunlight_cache.store(timestamp, {'visible_sun_fraction': 1}, {**patch, 'points': sunlight_points})
		earth = earth_cache.store(timestamp, {'visible_earth_fraction': 1, 'earth_center_visible': True}, {**patch, 'points': earth_points})
		save_frame(study, selection, sunlight, 'SUN')
		save_frame(study, selection, earth, 'EARTH')

	return study


def combined_url(study, selection_id=7):
	return reverse('terrain:studies:sunlight-study-site-combined-visibility', kwargs={'study_id': study.pk, 'selection_id': selection_id})


def test_combined_map_uses_same_point_overlap_and_weights_partial_final_step(client, combined_study):
	response = client.get(combined_url(combined_study))

	assert response.status_code == 200
	result = response.data
	assert result['selection_id'] == 7
	assert result['total_seconds'] == result['checked_seconds'] == 6000
	assert result['checked_frames'] == result['expected_frames'] == 2
	grid = result['grid']
	assert grid['grid_size'] == 5
	assert grid['spacing_meters'] == 500
	assert grid['samples'][0] is None
	assert grid['samples'][12] == {'latitude': -89, 'longitude': 40, 'visible_seconds': 6000}
	assert grid['samples'][14]['visible_seconds'] == 3600
	assert grid['samples'][10]['visible_seconds'] == 0
	assert result['previews'][0]['grid_size'] == 3
	assert result['previews'][0]['fractions'] == [None, 0, None, 0, 1, 1, None, 0, None]
	assert result['previews'][1]['fractions'] == [None, 0, None, 0, 1, 0, None, 0, None]
	assert 'result' not in result


def test_missing_or_unverified_times_reduce_coverage_without_becoming_blocked(client, combined_study):
	combined_study.frames.filter(timestamp=combined_study.start_time).update(joint_visible_share=None, joint_grid=None)
	combined_study.end_time += timedelta(hours=1)
	combined_study.save()
	rebuild_combined_visibility(combined_study)

	response = client.get(combined_url(combined_study))

	assert response.status_code == 200
	assert response.data['total_seconds'] == 9600
	assert response.data['checked_seconds'] == 3600
	assert response.data['checked_frames'] == 1
	assert response.data['expected_frames'] == 3
	assert response.data['grid']['samples'][12]['visible_seconds'] == 3600
	assert response.data['grid']['samples'][14]['visible_seconds'] == 0
	assert len(response.data['previews']) == 1


def test_combined_map_without_paired_results_is_empty_and_does_not_prepare_data(client, combined_study):
	combined_study.frames.all().delete()
	rebuild_combined_visibility(combined_study)
	preparation_count = SunlightPreparation.objects.count()

	response = client.get(combined_url(combined_study))

	assert response.status_code == 200
	assert response.data['checked_seconds'] == 0
	assert response.data['grid'] is None
	assert response.data['previews'] == []
	assert SunlightPreparation.objects.count() == preparation_count
	assert SunlightFrame.objects.count() == 0


def test_publishing_combined_results_rejects_mixed_ephemerides(client, combined_study):
	frame = combined_study.frames.last()
	before = client.get(combined_url(combined_study)).data
	stored = frame.cached_result.result
	changed = SunlightResultCache(frame.cached_result.preparation, 'b' * 64).store(frame.timestamp, stored['center'], stored['patch'])

	with pytest.raises(TerrainAnalysisUnavailable, match='different terrain preparations or ephemerides'):
		save_frame(combined_study, combined_study.selections[0], changed, 'SUN')

	frame.refresh_from_db()
	assert frame.cached_result_id != changed.pk
	assert client.get(combined_url(combined_study)).data == before


def test_combined_map_is_scoped_to_pinned_regions(client, combined_study):
	assert client.get(combined_url(combined_study, selection_id=8)).status_code == 404

	combined_study.selections[0]['radius_meters'] = None
	combined_study.save()

	response = client.get(combined_url(combined_study))

	assert_validation_error(response, 'selection_id', 'invalid')
	assert 'Choose a region' in str(response.data)


def test_joint_grid_preserves_circle_and_requires_both_at_each_sample():
	sunlight = {
		'patch': {
			'points': [
				None,
				{'visible_sun_fraction': 1},
				{'visible_sun_fraction': 0},
				{'visible_sun_fraction': 0.005},
				{'visible_sun_fraction': 0.006},
			]
		}
	}
	earth = {
		'patch': {
			'points': [
				None,
				{'earth_center_visible': False},
				{'earth_center_visible': True},
				{'earth_center_visible': True},
				{'earth_center_visible': True},
			]
		}
	}

	assert joint_fractions(sunlight, earth) == [None, 0, 0, 0, 1]


def test_incremental_frames_include_updates_to_existing_ids(client, combined_study):
	selection = combined_study.selections[0]
	stored = combined_study.frames.first()
	study = SunlightStudy.objects.create(
		name='Incremental',
		dataset=combined_study.dataset,
		selections=[selection],
		start_time=combined_study.start_time,
		end_time=combined_study.end_time,
		step_seconds=combined_study.step_seconds,
		expected_frames=2,
	)
	url = reverse('terrain:studies:sunlight-study-detail', kwargs={'study_id': study.pk})
	save_frame(study, selection, stored.cached_result, 'SUN')
	initial = client.get(url).data
	assert initial['reset']
	assert initial['study']['result_revision'] == 1
	assert initial['frames'][0]['visible_earth_fraction'] is None

	save_frame(study, selection, stored.cached_earth_result, 'EARTH')
	changed = client.get(url, {'after_revision': 1}).data
	assert not changed['reset']
	assert changed['study']['result_revision'] == 2
	assert len(changed['frames']) == 1
	assert changed['frames'][0]['id'] == initial['frames'][0]['id']
	assert changed['frames'][0]['visible_earth_fraction'] == 1
	assert changed['frames'][0]['result_revision'] == 2
	assert client.get(url, {'after_revision': 2}).data['frames'] == []


def test_duplicate_saves_do_not_add_overlap_duration_twice(client, combined_study):
	frame = combined_study.frames.first()
	before = client.get(combined_url(combined_study)).data
	save_frame(combined_study, combined_study.selections[0], frame.cached_earth_result, 'EARTH')
	after = client.get(combined_url(combined_study), {'after_revision': before['result_revision']}).data
	assert not after['reset']
	assert len(after['previews']) == 1
	assert after['grid'] == before['grid']
	assert after['checked_frames'] == before['checked_frames']
	assert after['checked_seconds'] == before['checked_seconds']
	assert client.get(combined_url(combined_study), {'after_revision': after['result_revision']}).data['previews'] == []


def test_schedule_edits_reset_cursors_and_reweight_retained_grids(client, combined_study):
	before = client.get(combined_url(combined_study)).data
	url = reverse('terrain:studies:sunlight-study-detail', kwargs={'study_id': combined_study.pk})
	response = client.put(
		url,
		{
			'name': combined_study.name,
			'selection_ids': [7],
			'start_time': combined_study.start_time.isoformat(),
			'end_time': (combined_study.start_time + timedelta(minutes=30)).isoformat(),
			'step_seconds': 3600,
			'worker_count': 4,
		},
		content_type='application/json',
	)
	assert response.status_code == 200

	changed = client.get(url, {'after_revision': before['result_revision']}).data
	assert changed['reset']
	assert len(changed['frames']) == 1
	combined = client.get(combined_url(combined_study), {'after_revision': before['result_revision']}).data
	assert combined['reset']
	assert combined['checked_seconds'] == 1800
	assert combined['grid']['samples'][12]['visible_seconds'] == 1800
	assert combined['grid']['samples'][14]['visible_seconds'] == 1800


@pytest.mark.parametrize(('after_revision', 'expected_code'), [('invalid', 'invalid'), ('-1', 'min_value')])
def test_invalid_result_cursors_are_rejected(client, combined_study, after_revision, expected_code):
	url = reverse('terrain:studies:sunlight-study-detail', kwargs={'study_id': combined_study.pk})
	for result_url in (url, combined_url(combined_study)):
		response = client.get(result_url, {'after_revision': after_revision})
		assert_validation_error(response, 'after_revision', expected_code)


def test_explicit_saved_result_preparation_preserves_existing_overlap_and_can_repeat(client, combined_study):
	before = client.get(combined_url(combined_study)).data
	combined_study.combined_visibility.all().delete()
	combined_study.frames.update(joint_grid=None, result_revision=0)
	response = client.get(combined_url(combined_study))
	assert_validation_error(response, 'selection_id', 'invalid')
	call_command('prepare_plan_results', combined_study.pk, stdout=StringIO())

	after = client.get(combined_url(combined_study)).data
	assert after['grid'] == before['grid']
	assert after['previews'] == before['previews']
	assert after['checked_seconds'] == before['checked_seconds']
	assert after['result_revision'] == before['result_revision'] + 1
	call_command('prepare_plan_results', combined_study.pk, stdout=StringIO())
	assert client.get(combined_url(combined_study)).data['grid'] == before['grid']


def test_explicit_result_preparation_rejects_active_plans(combined_study):
	combined_study.status = SunlightStudy.Status.RUNNING
	combined_study.save()

	with pytest.raises(CommandError, match='Stop the plan'):
		call_command('prepare_plan_results', combined_study.pk, stdout=StringIO())
