from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction

from terrain.models.EarthVisibilityResult import EarthVisibilityResult
from terrain.models.LunarFeature import LunarFeature
from terrain.models.StudyCombinedVisibility import StudyCombinedVisibility
from terrain.models.SunlightFrame import SunlightFrame
from terrain.models.SunlightHorizon import SunlightHorizon
from terrain.models.SunlightResult import SunlightResult
from terrain.tests.fixtures import create_preparation, create_selection, create_study, create_terrain_dataset


@pytest.mark.django_db
class TestLunarFeature:
	def test_feature_usgs_id_is_unique(self):
		values = {
			'usgs_id': 948,
			'name': 'Bürg',
			'clean_name': 'Burg',
			'feature_type': 'Crater',
			'latitude': 45,
			'longitude': -2,
			'approval_status': 'Adopted by IAU',
		}
		LunarFeature.objects.create(**values)

		with pytest.raises(IntegrityError), transaction.atomic():
			LunarFeature.objects.create(**values)

		LunarFeature.objects.create(**{**values, 'usgs_id': 949})
		assert LunarFeature.objects.count() == 2


@pytest.mark.django_db
class TestTerrainDataset:
	def setup_method(self):
		self.dataset = create_terrain_dataset()

	def test_dataset_storage_key_is_unique(self):
		other_dataset = create_terrain_dataset()
		other_dataset.storage_key = self.dataset.storage_key

		with pytest.raises(IntegrityError), transaction.atomic():
			other_dataset.save(update_fields=['storage_key'])

		other_dataset.refresh_from_db()
		assert other_dataset.storage_key != self.dataset.storage_key


@pytest.mark.django_db
class TestSunlightHorizon:
	def setup_method(self):
		self.dataset = create_terrain_dataset()

	def test_horizon_identity_includes_dataset_location_and_version(self):
		values = {'dataset': self.dataset, 'latitude': 0, 'longitude': 0, 'version': 1, 'data': b'horizon'}
		SunlightHorizon.objects.create(**values)

		with pytest.raises(IntegrityError), transaction.atomic():
			SunlightHorizon.objects.create(**values)

		SunlightHorizon.objects.create(**{**values, 'version': 2})
		assert SunlightHorizon.objects.count() == 2


@pytest.mark.django_db
class TestSunlightPreparation:
	def setup_method(self):
		self.dataset = create_terrain_dataset()
		self.preparation = create_preparation(self.dataset)

	def test_preparation_identity_is_unique(self):
		with pytest.raises(IntegrityError), transaction.atomic():
			create_preparation(self.dataset)

		other = create_preparation(create_terrain_dataset())
		assert other.pk != self.preparation.pk


@pytest.mark.django_db
class TestSunlightResult:
	def setup_method(self):
		self.dataset = create_terrain_dataset()
		self.study = create_study(self.dataset, create_selection())
		self.preparation = create_preparation(self.dataset)

	def test_sunlight_result_identity_is_unique(self):
		values = {
			'preparation': self.preparation,
			'timestamp': self.study.start_time,
			'version': 1,
			'ephemeris_signature': 'a' * 64,
			'visible_sun_fraction': 1,
			'result': {},
		}
		SunlightResult.objects.create(**values)

		with pytest.raises(IntegrityError), transaction.atomic():
			SunlightResult.objects.create(**values)

		SunlightResult.objects.create(**{**values, 'ephemeris_signature': 'b' * 64})
		assert SunlightResult.objects.count() == 2


@pytest.mark.django_db
class TestEarthVisibilityResult:
	def setup_method(self):
		self.dataset = create_terrain_dataset()
		self.study = create_study(self.dataset, create_selection())
		self.preparation = create_preparation(self.dataset)

	def test_earth_result_identity_is_unique(self):
		values = {
			'preparation': self.preparation,
			'timestamp': self.study.start_time,
			'version': 1,
			'ephemeris_signature': 'a' * 64,
			'visible_earth_fraction': 1,
			'earth_center_visible': True,
			'result': {},
		}
		EarthVisibilityResult.objects.create(**values)

		with pytest.raises(IntegrityError), transaction.atomic():
			EarthVisibilityResult.objects.create(**values)

		EarthVisibilityResult.objects.create(**{**values, 'timestamp': self.study.start_time + timedelta(minutes=5)})
		assert EarthVisibilityResult.objects.count() == 2


@pytest.mark.django_db
class TestSunlightFrame:
	def setup_method(self):
		self.dataset = create_terrain_dataset()
		self.study = create_study(self.dataset, create_selection())

	def test_frame_identity_is_unique(self):
		values = {'study': self.study, 'selection_id': self.study.selections[0]['id'], 'timestamp': self.study.start_time}
		SunlightFrame.objects.create(**values)

		with pytest.raises(IntegrityError), transaction.atomic():
			SunlightFrame.objects.create(**values)

		SunlightFrame.objects.create(**{**values, 'timestamp': self.study.start_time + timedelta(minutes=5)})
		assert SunlightFrame.objects.count() == 2


@pytest.mark.django_db
class TestStudyCombinedVisibility:
	def setup_method(self):
		self.dataset = create_terrain_dataset()
		self.study = create_study(self.dataset, create_selection())
		self.preparation = create_preparation(self.dataset)

	def test_combined_visibility_identity_is_unique(self):
		values = {
			'study': self.study,
			'selection_id': self.study.selections[0]['id'],
			'preparation': self.preparation,
			'ephemeris_signature': 'a' * 64,
			'visible_seconds': [0],
		}
		StudyCombinedVisibility.objects.create(**values)

		with pytest.raises(IntegrityError), transaction.atomic():
			StudyCombinedVisibility.objects.create(**values)

		StudyCombinedVisibility.objects.create(**{**values, 'selection_id': self.study.selections[0]['id'] + 1})
		assert StudyCombinedVisibility.objects.count() == 2
