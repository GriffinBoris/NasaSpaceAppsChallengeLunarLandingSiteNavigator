from datetime import UTC, datetime

import numpy
import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from terrain.models.SunlightHorizon import SunlightHorizon
from terrain.models.TerrainDataset import TerrainDataset
from terrain.models.TerrainTile import TerrainTile
from terrain.services.earth_result_cache import EarthResultCache
from terrain.services.horizon_profile import HorizonProfile
from terrain.services.sunlight_preparation import prepare_selection
from terrain.services.sunlight_result_cache import SunlightResultCache

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
	'model_name,payload_field', [('sunlightpreparation', 'samples'), ('sunlightresult', 'result'), ('earthvisibilityresult', 'result')]
)
def test_sunlight_cache_admin_is_read_only_and_defers_payloads(admin_client, analysis_dataset, model_name, payload_field):
	preparation = prepare_selection(analysis_dataset, {'latitude': 0, 'longitude': 0, 'radius_meters': None})
	if model_name == 'earthvisibilityresult':
		result = EarthResultCache(preparation, 'a' * 64).store(
			datetime(2026, 11, 11, tzinfo=UTC), {'visible_earth_fraction': 0.75, 'earth_center_visible': True}, None
		)
	else:
		result = SunlightResultCache(preparation, 'a' * 64).store(datetime(2026, 11, 11, tzinfo=UTC), {'visible_sun_fraction': 0.75}, None)
	row = preparation if model_name == 'sunlightpreparation' else result
	response = admin_client.get(reverse(f'admin:terrain_{model_name}_changelist'))
	stored = list(response.context['cl'].result_list)

	assert response.status_code == 200
	assert len(stored) == 1
	assert payload_field in stored[0].get_deferred_fields()
	detail_url = reverse(f'admin:terrain_{model_name}_change', kwargs={'object_id': row.pk})
	assert admin_client.get(detail_url).status_code == 200
	assert admin_client.post(detail_url, {}).status_code == 403
	assert admin_client.post(reverse(f'admin:terrain_{model_name}_delete', kwargs={'object_id': row.pk}), {'post': 'yes'}).status_code == 403


@pytest.mark.parametrize('model_name', ['sunlightpreparation', 'sunlightresult', 'earthvisibilityresult', 'studycombinedvisibility'])
def test_sunlight_cache_admin_requires_its_model_view_permission(client, django_user_model, model_name):
	user = django_user_model.objects.create_user(username='cache-viewer', is_staff=True)
	client.force_login(user)
	url = reverse(f'admin:terrain_{model_name}_changelist')

	assert client.get(url).status_code == 403
	user.user_permissions.add(Permission.objects.get(content_type__app_label='terrain', codename=f'view_{model_name}'))
	assert client.get(url).status_code == 200


@pytest.fixture
def dataset():
	dataset = TerrainDataset.objects.create(
		name='moon',
		status=TerrainDataset.Status.READY,
		frame='MOON_ME_DE421',
		reference_radius=1737400,
		tile_size=3,
		max_level=1,
		tile_count=1,
		refinements=['0/0/0/0'],
		sources=[{'filename': 'global.IMG', 'url': 'https://example.com/global.IMG'}],
	)
	heights = numpy.array([-1000, -0.5, 0, 0.5, 100, 200, 500, 1000, 2000], dtype='<f4')
	TerrainTile.objects.create(dataset=dataset, face=0, level=0, tile_x=0, tile_y=0, data=heights.tobytes())

	return dataset


def test_admin_lists_versions_marks_the_current_dataset_and_links_to_tiles(admin_client, dataset):
	newer_dataset = TerrainDataset.objects.create(
		name='moon',
		status=TerrainDataset.Status.READY,
		frame='MOON_ME_DE421',
		reference_radius=1737400,
		tile_size=65,
		max_level=9,
		tile_count=6,
		refinements=[],
		sources=[],
	)

	response = admin_client.get(reverse('admin:terrain_terraindataset_changelist'))
	versions = list(response.context['cl'].result_list)

	assert response.status_code == 200
	assert [(version.pk, version.is_current) for version in versions] == [(newer_dataset.pk, True), (dataset.pk, False)]
	assert f'{reverse("admin:terrain_terraintile_changelist")}?dataset__id__exact={dataset.pk}' in response.content.decode()


def test_admin_details_show_source_metadata_and_refinement_count(admin_client, dataset):
	response = admin_client.get(reverse('admin:terrain_terraindataset_change', kwargs={'object_id': dataset.pk}))
	content = response.content.decode()

	assert response.status_code == 200
	assert 'global.IMG' in content
	assert str(dataset.storage_key) in content
	assert 'Refinable tiles' in content
	assert 'All six base tiles stored' in content
	assert '0/0/0/0' not in content


def test_admin_cannot_modify_or_delete_dataset_records(admin_client, dataset):
	change_url = reverse('admin:terrain_terraindataset_change', kwargs={'object_id': dataset.pk})
	delete_url = reverse('admin:terrain_terraindataset_delete', kwargs={'object_id': dataset.pk})

	assert admin_client.post(change_url, {'name': 'changed'}).status_code == 403
	assert admin_client.post(delete_url, {'post': 'yes'}).status_code == 403

	dataset.refresh_from_db()

	assert dataset.name == 'moon'


def test_source_metadata_is_escaped_in_admin(admin_client, dataset):
	dataset.sources = [{'filename': '<script>alert(1)</script>'}]
	dataset.save(update_fields=['sources'])

	response = admin_client.get(reverse('admin:terrain_terraindataset_change', kwargs={'object_id': dataset.pk}))
	content = response.content.decode()

	assert '<script>alert(1)</script>' not in content
	assert '&lt;script&gt;alert(1)&lt;/script&gt;' in content


def test_computed_tile_rows_are_browseable_without_loading_binary_payloads(admin_client, dataset):
	response = admin_client.get(reverse('admin:terrain_terraintile_changelist'), {'dataset__id__exact': dataset.pk})
	tiles = list(response.context['cl'].result_list)

	assert response.status_code == 200
	assert len(tiles) == 1
	assert tiles[0].dataset_id == dataset.pk
	assert 'data' in tiles[0].get_deferred_fields()
	assert tiles[0].stored_size == 36


def test_tile_row_details_are_read_only_without_loading_binary_payloads(admin_client, dataset):
	tile = dataset.tiles.get()
	response = admin_client.get(reverse('admin:terrain_terraintile_change', kwargs={'object_id': tile.pk}))

	assert response.status_code == 200
	assert 'data' in response.context['original'].get_deferred_fields()
	assert admin_client.post(reverse('admin:terrain_terraintile_change', kwargs={'object_id': tile.pk}), {'face': 5}).status_code == 403
	assert admin_client.post(reverse('admin:terrain_terraintile_delete', kwargs={'object_id': tile.pk}), {'post': 'yes'}).status_code == 403


def test_tile_row_admin_requires_its_model_view_permission(client, django_user_model, dataset):
	user = django_user_model.objects.create_user(username='tile-viewer', is_staff=True)
	client.force_login(user)
	url = reverse('admin:terrain_terraintile_changelist')

	assert client.get(url).status_code == 403

	user.user_permissions.add(Permission.objects.get(content_type__app_label='terrain', codename='view_terraintile'))

	assert client.get(url).status_code == 200


def test_cached_horizons_are_read_only_and_payloads_are_deferred_on_admin_lists(admin_client, analysis_dataset):
	content = HorizonProfile.unresolved().encode()
	horizon = SunlightHorizon.objects.create(dataset=analysis_dataset, latitude=-89.9, longitude=180, version=1, data=content)
	response = admin_client.get(reverse('admin:terrain_sunlighthorizon_changelist'))
	rows = list(response.context['cl'].result_list)

	assert response.status_code == 200
	assert rows[0].dataset_id == analysis_dataset.pk
	assert rows[0].stored_size == len(content)
	assert 'data' in rows[0].get_deferred_fields()

	url = reverse('admin:terrain_sunlighthorizon_change', kwargs={'object_id': horizon.pk})
	response = admin_client.get(url)

	assert response.status_code == 200
	assert b'sampled_intervals' in response.content
	assert b'4096' in response.content
	assert admin_client.post(url, {'version': 2}).status_code == 403
	assert admin_client.post(reverse('admin:terrain_sunlighthorizon_delete', kwargs={'object_id': horizon.pk}), {'post': 'yes'}).status_code == 403


def test_horizon_admin_requires_its_model_view_permission(client, django_user_model):
	user = django_user_model.objects.create_user(username='horizon-viewer', is_staff=True)
	client.force_login(user)
	url = reverse('admin:terrain_sunlighthorizon_changelist')

	assert client.get(url).status_code == 403

	user.user_permissions.add(Permission.objects.get(content_type__app_label='terrain', codename='view_sunlighthorizon'))

	assert client.get(url).status_code == 200
