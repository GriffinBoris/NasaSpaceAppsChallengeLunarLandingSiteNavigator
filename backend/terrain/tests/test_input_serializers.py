from datetime import UTC, datetime

import pytest

from terrain.models.SunlightFrame import SunlightFrame
from terrain.models.SunlightStudy import SunlightStudy
from terrain.models.TerrainDataset import TerrainDataset
from terrain.tests.fixtures import create_selection, create_study, create_terrain_dataset
from terrain.views.features.serializers import LunarFeatureLabelsQuerySerializer, LunarFeatureSearchQuerySerializer
from terrain.views.illumination.serializers import IlluminationPatchQuerySerializer, IlluminationQuerySerializer
from terrain.views.selections.serializers import SunlightSelectionInputSerializer
from terrain.views.studies.serializers import (
	StudyResultChangesInputSerializer,
	SunlightStudyCalculateInputSerializer,
	SunlightStudyEditInputSerializer,
	SunlightStudyInputSerializer,
)


class TestIlluminationQuerySerializer:
	def setup_method(self):
		self.data = {'timestamp': '2026-11-11T07:00:00-05:00', 'latitude': -89, 'longitude': 180}

	@pytest.mark.parametrize('serializer_class', [IlluminationQuerySerializer, IlluminationPatchQuerySerializer])
	def test_times_are_normalized_to_utc(self, serializer_class):
		serializer = serializer_class(data=self.data)
		assert serializer.is_valid(), serializer.errors
		assert serializer.validated_data['timestamp'] == datetime(2026, 11, 11, 12, tzinfo=UTC)
		assert serializer.validated_data['latitude'] == -89
		assert serializer.validated_data['longitude'] == 180

	def test_patch_radius_has_the_domain_default(self):
		serializer = IlluminationPatchQuerySerializer(data=self.data)
		assert serializer.is_valid(), serializer.errors
		assert serializer.validated_data['radius_meters'] == 5000

	def test_missing_coordinates_have_exact_errors(self):
		serializer = IlluminationQuerySerializer(data={'timestamp': self.data['timestamp']})
		assert not serializer.is_valid()
		assert serializer.errors == {'latitude': ['This field is required.'], 'longitude': ['This field is required.']}


class TestLunarFeatureSearchQuerySerializer:
	def test_empty_search_is_explicit(self):
		serializer = LunarFeatureSearchQuerySerializer(data={})
		assert serializer.is_valid(), serializer.errors
		assert serializer.validated_data == {'q': ''}


class TestLunarFeatureLabelsQuerySerializer:
	def test_label_bounds_are_validated_before_querying(self):
		serializer = LunarFeatureLabelsQuerySerializer(data={'latitude': 0, 'longitude': 0, 'radius_degrees': 91, 'minimum_diameter_km': 0})
		assert not serializer.is_valid()
		assert serializer.errors == {'radius_degrees': ['Ensure this value is less than or equal to 90.']}


@pytest.mark.django_db
class TestSunlightSelectionInputSerializer:
	def setup_method(self):
		self.selection = create_selection()
		self.data = {'name': 'South rim', 'latitude': -89, 'longitude': 180, 'radius_meters': 1000}

	def test_create_persists_region_geometry(self):
		serializer = SunlightSelectionInputSerializer(data=self.data)
		assert serializer.is_valid(), serializer.errors
		selection = serializer.save()
		selection.refresh_from_db()
		assert selection.name == 'South rim'
		assert selection.latitude == -89
		assert selection.longitude == 180
		assert selection.radius_meters == 1000

	def test_partial_rename_preserves_geometry(self):
		serializer = SunlightSelectionInputSerializer(self.selection, data={'name': 'Renamed'}, partial=True)
		assert serializer.is_valid(), serializer.errors
		serializer.save()
		self.selection.refresh_from_db()
		assert self.selection.name == 'Renamed'
		assert (self.selection.latitude, self.selection.longitude, self.selection.radius_meters) == (0, 0, None)

	def test_invalid_radius_is_keyed_to_its_field(self):
		serializer = SunlightSelectionInputSerializer(data={**self.data, 'radius_meters': 0})
		assert not serializer.is_valid()
		assert serializer.errors == {'radius_meters': ['Ensure this value is greater than or equal to 250.']}


@pytest.mark.django_db
class TestSunlightStudyInputSerializer:
	def setup_method(self):
		self.dataset = create_terrain_dataset()
		self.selection = create_selection()
		self.data = {
			'name': 'Morning',
			'dataset_id': self.dataset.pk,
			'selection_ids': [self.selection.pk],
			'start_time': '2026-11-11T12:00:00Z',
			'end_time': '2026-11-11T12:10:00Z',
			'step_seconds': 300,
		}

	def test_create_pins_geometry_and_rounds_partial_steps_up(self):
		second_selection = create_selection(name='Second rim')
		self.data['selection_ids'].append(second_selection.pk)
		self.data['end_time'] = '2026-11-11T12:11:00Z'
		serializer = SunlightStudyInputSerializer(data=self.data)
		assert serializer.is_valid(), serializer.errors
		study = serializer.save()
		study.refresh_from_db()
		assert study.expected_frames == 6
		assert study.dataset_id == self.dataset.pk
		assert study.selections == [
			{'id': self.selection.pk, 'name': 'Rim', 'latitude': 0, 'longitude': 0, 'radius_meters': None},
			{'id': second_selection.pk, 'name': 'Second rim', 'latitude': 0, 'longitude': 0, 'radius_meters': None},
		]
		assert study.worker_count == SunlightStudy.WorkerCount.FOUR
		assert study.status == SunlightStudy.Status.PENDING

	@pytest.mark.parametrize(
		('field', 'value', 'message'),
		[
			('end_time', '2026-11-11T12:00:00Z', 'End time must be after start time.'),
			('selection_ids', [999999], 'Choose saved selections.'),
		],
	)
	def test_domain_errors_are_exact(self, field, value, message):
		serializer = SunlightStudyInputSerializer(data={**self.data, field: value})
		assert not serializer.is_valid()
		assert serializer.errors == {field: [message]}
		assert not SunlightStudy.objects.exists()

	def test_duplicate_selections_are_rejected(self):
		serializer = SunlightStudyInputSerializer(data={**self.data, 'selection_ids': [self.selection.pk, self.selection.pk]})
		assert not serializer.is_valid()
		assert serializer.errors == {'selection_ids': ['Choose each selection only once.']}

	def test_loading_dataset_cannot_be_pinned(self):
		self.dataset.status = TerrainDataset.Status.LOADING
		self.dataset.save(update_fields=['status'])
		serializer = SunlightStudyInputSerializer(data=self.data)
		assert not serializer.is_valid()
		assert serializer.errors == {'dataset_id': [f'Invalid pk "{self.dataset.pk}" - object does not exist.']}


@pytest.mark.django_db
class TestSunlightStudyEditInputSerializer:
	def setup_method(self):
		self.dataset = create_terrain_dataset()
		self.selection = create_selection()
		self.study = create_study(self.dataset, self.selection)
		self.data = {
			'name': 'Renamed',
			'selection_ids': [self.selection.pk],
			'start_time': self.study.start_time,
			'end_time': self.study.end_time,
			'step_seconds': 300,
			'worker_count': 2,
		}

	def test_rename_preserves_pinned_deleted_site_and_results(self):
		frame = SunlightFrame.objects.create(
			study=self.study, selection_id=self.selection.pk, timestamp=self.study.start_time, visible_sun_fraction=0.5
		)
		self.selection.delete()
		serializer = SunlightStudyEditInputSerializer(self.study, data=self.data)
		assert serializer.is_valid(), serializer.errors
		study = serializer.save()
		study.refresh_from_db()
		frame.refresh_from_db()
		assert study.name == 'Renamed'
		assert study.selections[0]['name'] == 'Rim'
		assert study.worker_count == 2
		assert study.result_revision == 1
		assert study.reset_revision == 0
		assert frame.visible_sun_fraction == 0.5

	def test_shortening_schedule_drops_only_stale_frames_and_resets_results(self):
		first = SunlightFrame.objects.create(study=self.study, selection_id=self.selection.pk, timestamp=self.study.start_time)
		stale = SunlightFrame.objects.create(study=self.study, selection_id=self.selection.pk, timestamp=self.study.end_time)
		self.data['end_time'] = '2026-11-11T12:05:00Z'
		serializer = SunlightStudyEditInputSerializer(self.study, data=self.data)
		assert serializer.is_valid(), serializer.errors
		study = serializer.save()
		study.refresh_from_db()
		assert study.expected_frames == 1
		assert study.status == SunlightStudy.Status.PENDING
		assert study.result_revision == study.reset_revision == 1
		assert list(study.frames.values_list('pk', flat=True)) == [first.pk]
		assert not SunlightFrame.objects.filter(pk=stale.pk).exists()


class TestSunlightStudyCalculateInputSerializer:
	@pytest.mark.parametrize('worker_count', [1, 2, 4, 8])
	def test_only_the_requested_worker_setting_is_writable(self, worker_count):
		serializer = SunlightStudyCalculateInputSerializer(data={'worker_count': worker_count, 'status': 'complete', 'dataset_id': 999})
		assert serializer.is_valid(), serializer.errors
		assert serializer.validated_data == {'worker_count': worker_count}


class TestStudyResultChangesInputSerializer:
	def test_omitted_cursor_requests_a_full_snapshot(self):
		serializer = StudyResultChangesInputSerializer(data={})
		assert serializer.is_valid(), serializer.errors
		assert serializer.validated_data == {'after_revision': None}

	def test_negative_cursor_has_an_exact_field_error(self):
		serializer = StudyResultChangesInputSerializer(data={'after_revision': -1})
		assert not serializer.is_valid()
		assert serializer.errors == {'after_revision': ['Ensure this value is greater than or equal to 0.']}
