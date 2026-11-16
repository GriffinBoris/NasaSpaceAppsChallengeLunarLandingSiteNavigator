from io import StringIO
from xml.etree import ElementTree
from zipfile import ZipFile

import pytest
from core.tests.assertions import assert_validation_error
from django.core.management import call_command
from django.urls import reverse

from terrain.models.LunarFeature import LunarFeature
from terrain.services.lunar_feature_import import KML_FILENAME, import_lunar_features

pytestmark = pytest.mark.django_db


@pytest.fixture
def catalog_file(tmp_path):
	def write(records):
		root = ElementTree.Element('kml', xmlns='http://www.opengis.net/kml/2.2')
		document = ElementTree.SubElement(root, 'Document')

		for record in records:
			placemark = ElementTree.SubElement(document, 'Placemark', id='export-row-number')
			ElementTree.SubElement(placemark, 'name').text = record['name']
			data = ElementTree.SubElement(ElementTree.SubElement(placemark, 'ExtendedData'), 'SchemaData')

			for name, value in record.items():
				if name != 'name':
					ElementTree.SubElement(data, 'SimpleData', name=name).text = str(value)

		path = tmp_path / 'catalog.kmz'

		with ZipFile(path, 'w') as archive:
			archive.writestr(KML_FILENAME, ElementTree.tostring(root, encoding='utf-8'))

		return path

	return write


@pytest.fixture
def feature_record():
	return {
		'name': 'Bürg',
		'clean_name': 'Burg',
		'link': 'http://planetarynames.wr.usgs.gov/Feature/948',
		'type': 'Crater, craters',
		'center_lat': 45.0734,
		'center_lon': 358.1489,
		'diameter': 41.042278,
		'origin': 'Johann Tobias; Austrian astronomer.',
		'approval': 'Adopted by IAU',
	}


def test_import_uses_stable_ids_preserves_names_and_updates_existing_rows(catalog_file, feature_record):
	path = catalog_file([feature_record])
	updates = []
	assert import_lunar_features(path, lambda completed, total: updates.append((completed, total))) == 1
	stored = LunarFeature.objects.get(usgs_id=948)
	original_id = stored.pk
	assert stored.name == 'Bürg'
	assert stored.clean_name == 'Burg'
	assert stored.latitude == 45.0734
	assert stored.longitude == pytest.approx(-1.8511)
	assert stored.diameter_km == 41.042278
	assert stored.source_url == 'https://planetarynames.wr.usgs.gov/Feature/948'
	assert updates == [(0, 1), (1, 1)]
	feature_record['name'] = 'Updated name'
	feature_record['approval'] = 'Dropped'
	path = catalog_file([feature_record])
	import_lunar_features(path, lambda completed, total: None)
	stored.refresh_from_db()
	assert LunarFeature.objects.count() == 1
	assert stored.pk == original_id
	assert stored.name == 'Updated name'
	assert stored.approval_status == 'Dropped'
	assert path.is_file()


@pytest.mark.parametrize(('field', 'value'), [('center_lat', 'NaN'), ('center_lat', 91), ('center_lon', 500), ('diameter', -1)])
def test_invalid_catalog_leaves_the_previous_catalog_unchanged(catalog_file, feature_record, field, value):
	import_lunar_features(catalog_file([feature_record]), lambda completed, total: None)
	previous = LunarFeature.objects.values().get()
	bad_record = {**feature_record, field: value}

	with pytest.raises(ValueError):
		import_lunar_features(catalog_file([bad_record]), lambda completed, total: None)

	assert LunarFeature.objects.values().get() == previous


def test_duplicate_ids_and_empty_catalog_fail_without_writing(catalog_file, feature_record):
	for records in [[], [feature_record, feature_record]]:
		with pytest.raises(ValueError):
			import_lunar_features(catalog_file(records), lambda completed, total: None)

	assert not LunarFeature.objects.exists()


def test_missing_optional_diameter_and_origin_are_supported(catalog_file, feature_record):
	feature_record.pop('diameter')
	feature_record.pop('origin')
	import_lunar_features(catalog_file([feature_record]), lambda completed, total: None)
	assert LunarFeature.objects.get().diameter_km is None
	assert LunarFeature.objects.get().origin == ''


def test_failed_publication_rolls_back_all_rows(catalog_file, feature_record):
	records = [{**feature_record, 'link': f'https://planetarynames.wr.usgs.gov/Feature/{index}'} for index in range(1, 502)]

	def fail_after_batch(completed, total):
		if completed:
			raise OSError('Output unavailable')

	with pytest.raises(OSError, match='Output unavailable'):
		import_lunar_features(catalog_file(records), fail_after_batch)

	assert not LunarFeature.objects.exists()


def test_command_downloads_through_shared_cache_and_imports_rows(catalog_file, feature_record, monkeypatch, settings):
	path = catalog_file([feature_record])
	downloads = []

	def download(url, directory, progress):
		downloads.append((url, directory))
		return path

	monkeypatch.setattr('terrain.management.commands.import_lunar_features.download_file', download)
	output = StringIO()
	call_command('import_lunar_features', stdout=output)
	assert downloads[0][1] == settings.MEDIA_ROOT / 'nomenclature'
	assert LunarFeature.objects.get().usgs_id == 948
	assert 'Stored 1 lunar features' in output.getvalue()


def test_search_is_public_and_matches_official_and_clean_names(client, catalog_file, feature_record):
	import_lunar_features(catalog_file([feature_record]), lambda completed, total: None)
	url = reverse('terrain:features:lunar-feature-search')

	for query in ['Bürg', 'burg']:
		response = client.get(url, {'q': query})
		assert response.status_code == 200
		assert response.data['catalog_loaded'] is True
		assert response.data['features'][0]['name'] == 'Bürg'
		assert response.data['features'][0]['english_name'] is None
		assert set(response.data['features'][0]) == {
			'id',
			'usgs_id',
			'name',
			'english_name',
			'feature_type',
			'latitude',
			'longitude',
			'diameter_km',
			'source_url',
		}

	assert client.get(url, {'q': 'Tycho'}).data == {'features': [], 'catalog_loaded': True}


def test_search_distinguishes_an_empty_catalog_and_hides_retired_names(client, catalog_file, feature_record):
	url = reverse('terrain:features:lunar-feature-search')
	assert client.get(url).data == {'features': [], 'catalog_loaded': False}
	feature_record['approval'] = 'Dropped'
	import_lunar_features(catalog_file([feature_record]), lambda completed, total: None)
	assert client.get(url, {'q': 'Burg'}).data == {'features': [], 'catalog_loaded': True}


def test_search_matches_english_names_in_catalog_origins_and_excludes_retired_features(client, catalog_file, feature_record):
	record = {
		**feature_record,
		'name': 'Mare Tranquillitatis',
		'clean_name': 'Mare Tranquillitatis',
		'link': 'https://planetarynames.wr.usgs.gov/Feature/3691',
		'origin': '"Sea of Tranquility."',
	}
	retired_record = {**record, 'link': 'https://planetarynames.wr.usgs.gov/Feature/3692', 'approval': 'Dropped'}
	import_lunar_features(catalog_file([record, retired_record]), lambda completed, total: None)

	response = client.get(reverse('terrain:features:lunar-feature-search'), {'q': 'Sea of Tranquility'})

	assert response.status_code == 200
	assert [(feature['usgs_id'], feature['name']) for feature in response.data['features']] == [(3691, 'Mare Tranquillitatis')]
	assert response.data['features'][0]['english_name'] == 'Sea of Tranquility'


@pytest.mark.parametrize(('query', 'expected_code'), [('a', 'min_length'), ('x' * 121, 'max_length')])
def test_search_rejects_invalid_queries(client, query, expected_code):
	response = client.get(reverse('terrain:features:lunar-feature-search'), {'q': query})
	assert_validation_error(response, 'q', expected_code)


def test_search_is_bounded_and_empty_query_does_not_list_every_feature(client, catalog_file, feature_record):
	records = [
		{**feature_record, 'name': f'Crater {index:02}', 'link': f'https://planetarynames.wr.usgs.gov/Feature/{index}'} for index in range(1, 26)
	]
	import_lunar_features(catalog_file(records), lambda completed, total: None)
	url = reverse('terrain:features:lunar-feature-search')
	assert client.get(url).data['features'] == []
	features = client.get(url, {'q': 'crater'}).data['features']
	assert len(features) == 20
	assert [feature['name'] for feature in features] == [f'Crater {index:02}' for index in range(1, 21)]


def test_feature_admin_is_read_only(admin_client, catalog_file, feature_record):
	import_lunar_features(catalog_file([feature_record]), lambda completed, total: None)
	response = admin_client.get(reverse('admin:terrain_lunarfeature_changelist'))
	assert response.status_code == 200
	assert 'Bürg' in response.content.decode()
	assert admin_client.get(reverse('admin:terrain_lunarfeature_add')).status_code == 403


def test_labels_filter_the_view_and_size_and_prioritize_large_features(client, catalog_file, feature_record):
	features = [('Small', 0, 0, 1), ('Visible', 0, 0, 10), ('Large', 1, 1, 100), ('Distant', 40, 0, 500), ('Far longitude', 0, 40, 500)]
	records = []

	for index, (name, latitude, longitude, diameter) in enumerate(features, start=1):
		records.append(
			{
				**feature_record,
				'name': name,
				'center_lat': latitude,
				'center_lon': longitude,
				'diameter': diameter,
				'link': f'https://planetarynames.wr.usgs.gov/Feature/{index}',
			}
		)

	import_lunar_features(catalog_file(records), lambda completed, total: None)
	response = client.get(
		reverse('terrain:features:lunar-feature-labels'),
		{
			'latitude': 0,
			'longitude': 0,
			'radius_degrees': 5,
			'minimum_diameter_km': 5,
		},
	)
	assert response.status_code == 200
	assert [feature['name'] for feature in response.data] == ['Large', 'Visible']


@pytest.mark.parametrize('longitude', [179, -179])
def test_labels_cover_both_sides_of_the_date_line(client, catalog_file, feature_record, longitude):
	records = [
		{**feature_record, 'center_lat': 0, 'center_lon': value, 'link': f'https://planetarynames.wr.usgs.gov/Feature/{index}'}
		for index, value in enumerate([178, -178, 0], start=1)
	]
	import_lunar_features(catalog_file(records), lambda completed, total: None)
	response = client.get(
		reverse('terrain:features:lunar-feature-labels'),
		{
			'latitude': 0,
			'longitude': longitude,
			'radius_degrees': 5,
			'minimum_diameter_km': 1,
		},
	)
	assert [feature['usgs_id'] for feature in response.data] == [1, 2]


@pytest.mark.parametrize('latitude', [89, -89])
def test_polar_label_views_include_all_longitudes(client, catalog_file, feature_record, latitude):
	records = [
		{**feature_record, 'center_lat': latitude, 'center_lon': longitude, 'link': f'https://planetarynames.wr.usgs.gov/Feature/{index}'}
		for index, longitude in enumerate([-170, 0, 170], start=1)
	]
	import_lunar_features(catalog_file(records), lambda completed, total: None)
	response = client.get(
		reverse('terrain:features:lunar-feature-labels'),
		{
			'latitude': latitude,
			'longitude': 0,
			'radius_degrees': 5,
			'minimum_diameter_km': 1,
		},
	)
	assert len(response.data) == 3


@pytest.mark.parametrize(
	('field', 'value', 'expected_code'),
	[
		('latitude', 'NaN', 'invalid'),
		('longitude', 181, 'max_value'),
		('radius_degrees', 0, 'min_value'),
		('radius_degrees', 91, 'max_value'),
		('minimum_diameter_km', 'Infinity', 'invalid'),
	],
)
def test_labels_reject_invalid_view_parameters(client, field, value, expected_code):
	parameters = {'latitude': 0, 'longitude': 0, 'radius_degrees': 10, 'minimum_diameter_km': 1, field: value}
	response = client.get(reverse('terrain:features:lunar-feature-labels'), parameters)
	assert_validation_error(response, field, expected_code)


def test_label_results_are_bounded_and_exclude_retired_features(client, catalog_file, feature_record):
	records = [
		{**feature_record, 'center_lat': 0, 'center_lon': 0, 'link': f'https://planetarynames.wr.usgs.gov/Feature/{index}'} for index in range(1, 303)
	]
	records[0]['approval'] = 'Dropped'
	import_lunar_features(catalog_file(records), lambda completed, total: None)
	response = client.get(
		reverse('terrain:features:lunar-feature-labels'),
		{
			'latitude': 0,
			'longitude': 0,
			'radius_degrees': 5,
			'minimum_diameter_km': 1,
		},
	)
	assert len(response.data) == 300
	assert response.data[0]['usgs_id'] == 2
