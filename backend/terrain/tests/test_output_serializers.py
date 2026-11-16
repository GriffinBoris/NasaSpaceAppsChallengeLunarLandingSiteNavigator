from datetime import UTC, datetime
from uuid import UUID

import pytest

from terrain.models.EarthVisibilityResult import EarthVisibilityResult
from terrain.models.LunarFeature import LunarFeature
from terrain.models.SunlightFrame import SunlightFrame
from terrain.models.SunlightResult import SunlightResult
from terrain.models.SunlightSelection import SunlightSelection
from terrain.models.SunlightStudy import SunlightStudy
from terrain.models.TerrainDataset import TerrainDataset
from terrain.views.dataset.serializers import TerrainDatasetOutputSerializer
from terrain.views.earth.serializers import EarthVisibilityPatchOutputSerializer
from terrain.views.features.serializers import LunarFeatureOutputSerializer
from terrain.views.horizon.serializers import LocationHorizonOutputSerializer
from terrain.views.illumination.serializers import IlluminationPatchOutputSerializer
from terrain.views.selections.serializers import SunlightSelectionOutputSerializer
from terrain.views.studies.serializers import (
	SiteCombinedVisibilityOutputSerializer,
	SiteDirectionsOutputSerializer,
	SiteHorizonOutputSerializer,
	SiteTerrainOutputSerializer,
	SunlightFrameDetailOutputSerializer,
	SunlightFrameOutputSerializer,
	SunlightStudyOutputSerializer,
)


class TestTerrainDatasetOutputSerializer:
	def setup_method(self):
		self.dataset = TerrainDataset(
			id=3,
			name='moon',
			storage_key=UUID('12345678-1234-1234-1234-123456789abc'),
			frame='MOON_ME_DE421',
			reference_radius=1737400,
			tile_size=33,
			max_level=7,
			tile_count=6,
			refinements=[],
			sources=[],
		)

	def test_catalog_contract_and_immutable_tile_identity(self):
		data = dict(TerrainDatasetOutputSerializer(self.dataset).data)
		assert data.pop('id') == 3
		assert data.pop('name') == 'moon'
		assert data.pop('storage_key') == '12345678-1234-1234-1234-123456789abc'
		assert data.pop('frame') == 'MOON_ME_DE421'
		assert data.pop('reference_radius') == 1737400
		assert data.pop('tile_size') == 33
		assert data.pop('max_level') == 7
		assert data.pop('tile_count') == 6
		assert data.pop('refinements') == []
		assert data.pop('sources') == []
		assert data.pop('tile_url_template') == 'terrain/12345678-1234-1234-1234-123456789abc/{face}/{level}/{x}/{y}/'
		assert not data


class TestLunarFeatureOutputSerializer:
	def setup_method(self):
		self.feature = LunarFeature(
			id=7,
			usgs_id=3691,
			name='Mare Tranquillitatis',
			feature_type='Mare, maria',
			latitude=8.3487,
			longitude=30.8346,
			diameter_km=None,
			origin='"Sea of Tranquility."',
		)

	def test_official_and_english_names_have_an_exact_contract(self):
		data = dict(LunarFeatureOutputSerializer(self.feature).data)
		assert data.pop('id') == 7
		assert data.pop('usgs_id') == 3691
		assert data.pop('name') == 'Mare Tranquillitatis'
		assert data.pop('english_name') == 'Sea of Tranquility'
		assert data.pop('feature_type') == 'Mare, maria'
		assert data.pop('latitude') == 8.3487
		assert data.pop('longitude') == 30.8346
		assert data.pop('diameter_km') is None
		assert data.pop('source_url') == 'https://planetarynames.wr.usgs.gov/Feature/3691'
		assert not data

	@pytest.mark.parametrize(
		('origin', 'english_name'),
		[
			('"Sea of Tranquility."', 'Sea of Tranquility'),
			('"Sea that has become known." Ranger VII impact site. ', 'Sea that has become known'),
			('“Lake of Darkness.”', 'Lake of Darkness'),
			('"Tranquility Base," Apollo 11 landing site.', 'Tranquility Base'),
			('Latin for "straight cliff" (the straight wall).', 'straight cliff'),
			('Sir Ernest Henry; British Antarctic explorer.', None),
			('"Unclosed description', None),
			('', None),
		],
	)
	def test_translations_exclude_biographies(self, origin, english_name):
		self.feature.origin = origin
		assert LunarFeatureOutputSerializer(self.feature).data['english_name'] == english_name


class TestSunlightSelectionOutputSerializer:
	def test_nullable_point_radius_and_timestamps(self):
		timestamp = datetime(2026, 11, 11, 12, tzinfo=UTC)
		selection = SunlightSelection(id=7, name='Rim', latitude=-89, longitude=180, radius_meters=None, created_ts=timestamp, updated_ts=timestamp)
		data = dict(SunlightSelectionOutputSerializer(selection).data)
		assert data.pop('id') == 7
		assert data.pop('name') == 'Rim'
		assert data.pop('latitude') == -89
		assert data.pop('longitude') == 180
		assert data.pop('radius_meters') is None
		assert data.pop('created_ts') == '2026-11-11T12:00:00Z'
		assert data.pop('updated_ts') == '2026-11-11T12:00:00Z'
		assert not data


class TestSunlightStudyOutputSerializer:
	def test_annotated_progress_and_lifecycle_have_an_exact_contract(self):
		timestamp = datetime(2026, 11, 11, 12, tzinfo=UTC)
		study = SunlightStudy(
			id=4,
			name='Morning',
			dataset_id=3,
			selections=[],
			start_time=timestamp,
			end_time=datetime(2026, 11, 12, 12, tzinfo=UTC),
			step_seconds=900,
			expected_frames=96,
			created_ts=timestamp,
		)
		study.completed_frames = 2
		study.saved_results = 4
		data = dict(SunlightStudyOutputSerializer(study).data)
		assert data.pop('id') == 4
		assert data.pop('name') == 'Morning'
		assert data.pop('dataset_id') == 3
		assert data.pop('selections') == []
		assert data.pop('start_time') == '2026-11-11T12:00:00Z'
		assert data.pop('end_time') == '2026-11-12T12:00:00Z'
		assert data.pop('step_seconds') == 900
		assert data.pop('worker_count') == 4
		assert data.pop('expected_frames') == 96
		assert data.pop('completed_frames') == 2
		assert data.pop('saved_results') == 4
		assert data.pop('result_revision') == 0
		assert data.pop('status') == 'pending'
		assert data.pop('progress') is None
		assert data.pop('error_message') == ''
		assert data.pop('created_ts') == '2026-11-11T12:00:00Z'
		assert not data


class TestSunlightFrameOutputSerializer:
	def setup_method(self):
		self.frame = SunlightFrame(
			id=9,
			study_id=4,
			selection_id=7,
			timestamp=datetime(2026, 11, 11, 12, tzinfo=UTC),
			visible_sun_fraction=0.5,
			thumbnail={'grid_size': 1, 'fractions': [0.5]},
			result={'center': {'visible_sun_fraction': 0.5}, 'patch': None},
		)
		self.expected = {
			'id': 9,
			'study_id': 4,
			'selection_id': 7,
			'timestamp': '2026-11-11T12:00:00Z',
			'visible_sun_fraction': 0.5,
			'thumbnail': {'grid_size': 1, 'fractions': [0.5]},
			'visible_earth_fraction': None,
			'earth_thumbnail': None,
			'earth_center_visible': None,
			'joint_visible_share': None,
			'result_revision': 0,
		}

	def test_summary_excludes_full_payloads_and_preserves_missing_earth(self):
		assert SunlightFrameOutputSerializer(self.frame).data == self.expected

	def test_detail_retains_legacy_payload_without_cached_results(self):
		data = dict(SunlightFrameDetailOutputSerializer(self.frame).data)
		assert data == {**self.expected, 'result': {'center': {'visible_sun_fraction': 0.5}, 'patch': None}, 'earth_result': None}

	def test_detail_prefers_both_cached_results(self):
		sunlight = {'center': {'visible_sun_fraction': 1}, 'patch': None}
		earth = {'center': {'earth_center_visible': True}, 'patch': None}
		self.frame.cached_result = SunlightResult(id=1, result=sunlight)
		self.frame.cached_earth_result = EarthVisibilityResult(id=2, result=earth, thumbnail={'grid_size': 1, 'fractions': [1]})
		data = dict(SunlightFrameDetailOutputSerializer(self.frame).data)
		assert data == {**self.expected, 'earth_thumbnail': {'grid_size': 1, 'fractions': [1]}, 'result': sunlight, 'earth_result': earth}


class TestIlluminationPatchOutputSerializer:
	def test_sunlight_patch_preserves_exterior_cells_and_full_center_metadata(self):
		center = {
			'dataset_id': 3,
			'timestamp': datetime(2026, 11, 11, 12, tzinfo=UTC),
			'latitude': -89,
			'longitude': 180,
			'frame': 'MOON_ME_DE421',
			'elevation_meters': -100,
			'analysis_level': 7,
			'sun_elevation_degrees': 1,
			'sun_azimuth_degrees': 90,
			'sun_angular_radius_degrees': 0.26,
			'visible_sun_fraction': 0.5,
			'disk_sample_count': 1024,
			'sampling_converged': True,
			'fraction_tolerance': 0.005,
		}
		point = {'visible_sun_fraction': 0.5, 'sampling_converged': True}
		patch = {
			'center': center,
			'grid_size': 3,
			'radius_meters': 1000,
			'spacing_meters': 1000,
			'points': [None, point, None, point, point, point, None, point, None],
		}
		data = dict(IlluminationPatchOutputSerializer(patch).data)
		assert data.pop('center') == {**center, 'timestamp': '2026-11-11T12:00:00Z'}
		assert data.pop('grid_size') == 3
		assert data.pop('radius_meters') == 1000
		assert data.pop('spacing_meters') == 1000
		assert data.pop('points') == [None, point, None, point, point, point, None, point, None]
		assert not data


class TestEarthVisibilityPatchOutputSerializer:
	def test_earth_center_visibility_stays_separate_from_disk_fraction(self):
		center = {
			'dataset_id': 3,
			'timestamp': datetime(2026, 11, 11, 12, tzinfo=UTC),
			'latitude': -89,
			'longitude': 180,
			'frame': 'MOON_ME_DE421',
			'elevation_meters': -100,
			'analysis_level': 7,
			'earth_elevation_degrees': 0,
			'earth_azimuth_degrees': 90,
			'earth_angular_radius_degrees': 0.95,
			'visible_earth_fraction': 0.25,
			'earth_center_visible': False,
			'disk_sample_count': 1024,
			'sampling_converged': True,
			'fraction_tolerance': 0.005,
		}
		point = {'visible_earth_fraction': 0.25, 'earth_center_visible': False, 'sampling_converged': True}
		patch = {
			'center': center,
			'grid_size': 3,
			'radius_meters': 1000,
			'spacing_meters': 1000,
			'points': [None, point, None, point, point, point, None, point, None],
		}
		data = dict(EarthVisibilityPatchOutputSerializer(patch).data)
		assert data['center']['earth_center_visible'] is False
		assert data.pop('center') == {**center, 'timestamp': '2026-11-11T12:00:00Z'}
		assert data.pop('grid_size') == 3
		assert data.pop('radius_meters') == 1000
		assert data.pop('spacing_meters') == 1000
		assert data.pop('points') == [None, point, None, point, point, point, None, point, None]
		assert not data


class TestLocationHorizonOutputSerializer:
	def test_bounded_profile_and_current_body_directions(self):
		bounds = {'lower_elevation_degrees': [-1, 0, 1], 'upper_elevation_degrees': [0, 1, 2]}
		result = {
			'dataset_id': 3,
			'timestamp': datetime(2026, 11, 11, 12, tzinfo=UTC),
			'latitude': -89,
			'longitude': 180,
			'azimuth_offset_degrees': 20,
			'bounds': bounds,
			'sun': {'elevation_degrees': 1, 'azimuth_degrees': 90},
			'earth': {'elevation_degrees': -1, 'azimuth_degrees': 180},
		}
		data = dict(LocationHorizonOutputSerializer(result).data)
		assert data.pop('dataset_id') == 3
		assert data.pop('timestamp') == '2026-11-11T12:00:00Z'
		assert data.pop('latitude') == -89
		assert data.pop('longitude') == 180
		assert data.pop('azimuth_offset_degrees') == 20
		assert data.pop('bounds') == {'lower_elevation_degrees': [-1, 0, 1], 'upper_elevation_degrees': [0, 1, 2]}
		assert data.pop('sun') == {'elevation_degrees': 1, 'azimuth_degrees': 90}
		assert data.pop('earth') == {'elevation_degrees': -1, 'azimuth_degrees': 180}
		assert not data


class TestSiteHorizonOutputSerializer:
	def test_missing_profile_is_explicit(self):
		data = dict(SiteHorizonOutputSerializer({'selection_id': 7, 'azimuth_offset_degrees': 0, 'bounds': None}).data)
		assert data.pop('selection_id') == 7
		assert data.pop('azimuth_offset_degrees') == 0
		assert data.pop('bounds') is None
		assert not data


class TestSiteDirectionsOutputSerializer:
	def test_both_body_series_have_an_exact_shape(self):
		result = {
			'selection_id': 7,
			'sun': {'elevation_degrees': [1, 2], 'azimuth_degrees': [90, 91]},
			'earth': {'elevation_degrees': [-1, 0], 'azimuth_degrees': [180, 181]},
		}
		data = dict(SiteDirectionsOutputSerializer(result).data)
		assert data.pop('selection_id') == 7
		assert data.pop('sun') == {'elevation_degrees': [1, 2], 'azimuth_degrees': [90, 91]}
		assert data.pop('earth') == {'elevation_degrees': [-1, 0], 'azimuth_degrees': [180, 181]}
		assert not data


class TestSiteTerrainOutputSerializer:
	def test_height_grid_exposes_its_units_and_spacing(self):
		result = {
			'selection_id': 7,
			'radius_meters': 1000,
			'grid_size': 3,
			'spacing_meters': 1000,
			'reference_radius_meters': 1737400,
			'heights_meters': [-4, -3, -2, -1, 0, 1, 2, 3, 4],
		}
		data = dict(SiteTerrainOutputSerializer(result).data)
		assert data.pop('selection_id') == 7
		assert data.pop('radius_meters') == 1000
		assert data.pop('grid_size') == 3
		assert data.pop('spacing_meters') == 1000
		assert data.pop('reference_radius_meters') == 1737400
		assert data.pop('heights_meters') == [-4, -3, -2, -1, 0, 1, 2, 3, 4]
		assert not data


class TestSiteCombinedVisibilityOutputSerializer:
	def test_aggregate_and_incremental_preview_preserve_the_circle(self):
		sample = {'latitude': -89, 'longitude': 180, 'visible_seconds': 300}
		samples = [None, sample, None, sample, sample, sample, None, sample, None]
		fractions = [None, 1, None, 1, 1, 1, None, 1, None]
		result = {
			'selection_id': 7,
			'result_revision': 2,
			'reset': False,
			'total_seconds': 600,
			'checked_seconds': 300,
			'checked_frames': 1,
			'expected_frames': 2,
			'grid': {'grid_size': 3, 'radius_meters': 1000, 'spacing_meters': 1000, 'samples': samples},
			'previews': [{'frame_id': 9, 'grid_size': 3, 'fractions': fractions}],
		}
		data = dict(SiteCombinedVisibilityOutputSerializer(result).data)
		assert data.pop('selection_id') == 7
		assert data.pop('result_revision') == 2
		assert data.pop('reset') is False
		assert data.pop('total_seconds') == 600
		assert data.pop('checked_seconds') == 300
		assert data.pop('checked_frames') == 1
		assert data.pop('expected_frames') == 2
		assert data.pop('grid') == {
			'grid_size': 3,
			'radius_meters': 1000,
			'spacing_meters': 1000,
			'samples': [None, sample, None, sample, sample, sample, None, sample, None],
		}
		assert data.pop('previews') == [{'frame_id': 9, 'grid_size': 3, 'fractions': [None, 1, None, 1, 1, 1, None, 1, None]}]
		assert not data

	def test_missing_grid_is_not_a_zero_visibility_map(self):
		result = {
			'selection_id': 7,
			'result_revision': 0,
			'reset': True,
			'total_seconds': 600,
			'checked_seconds': 0,
			'checked_frames': 0,
			'expected_frames': 2,
			'grid': None,
			'previews': [],
		}
		data = dict(SiteCombinedVisibilityOutputSerializer(result).data)
		assert data.pop('selection_id') == 7
		assert data.pop('result_revision') == 0
		assert data.pop('reset') is True
		assert data.pop('total_seconds') == 600
		assert data.pop('checked_seconds') == 0
		assert data.pop('checked_frames') == 0
		assert data.pop('expected_frames') == 2
		assert data.pop('grid') is None
		assert data.pop('previews') == []
		assert not data
