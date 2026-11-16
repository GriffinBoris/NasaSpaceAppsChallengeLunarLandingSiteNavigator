import json
from math import degrees

from django.conf import settings
from django.contrib import admin
from django.db.models import Exists, OuterRef
from django.db.models.functions import Length
from django.urls import reverse
from django.utils.html import format_html

from terrain.models.EarthVisibilityResult import EarthVisibilityResult
from terrain.models.LunarFeature import LunarFeature
from terrain.models.StudyCombinedVisibility import StudyCombinedVisibility
from terrain.models.SunlightFrame import SunlightFrame
from terrain.models.SunlightHorizon import SunlightHorizon
from terrain.models.SunlightPreparation import SunlightPreparation
from terrain.models.SunlightResult import SunlightResult
from terrain.models.SunlightSelection import SunlightSelection
from terrain.models.SunlightStudy import SunlightStudy
from terrain.models.TerrainDataset import TerrainDataset
from terrain.models.TerrainTile import TerrainTile
from terrain.services.horizon_profile import HorizonProfile


class ReadOnlyTerrainAdmin(admin.ModelAdmin):
	actions = None
	show_full_result_count = False
	readonly_fields = ('id', 'created_ts', 'updated_ts')

	def has_add_permission(self, request):
		return False

	def has_change_permission(self, request, obj=None):
		return False

	def has_delete_permission(self, request, obj=None):
		return False


@admin.register(TerrainDataset)
class TerrainDatasetAdmin(ReadOnlyTerrainAdmin):
	list_display = ('id', 'name', 'status', 'is_current', 'storage_format', 'max_level', 'tile_count', 'stored_tiles', 'created_ts', 'updated_ts')
	list_filter = ('status', 'storage_format', 'max_level')
	search_fields = ('name', 'storage_key')
	ordering = ('-id',)
	readonly_fields = (
		'id',
		'name',
		'status',
		'is_current',
		'storage_key',
		'storage_format',
		'storage_location',
		'tiles_present',
		'stored_tiles',
		'frame',
		'reference_radius',
		'tile_size',
		'max_level',
		'tile_count',
		'refinement_count',
		'source_details',
		'created_ts',
		'updated_ts',
	)
	fieldsets = (
		('Dataset version', {'fields': ('id', 'name', 'status', 'is_current', 'storage_key', 'created_ts', 'updated_ts')}),
		('Terrain', {'fields': ('frame', 'reference_radius', 'tile_size', 'max_level', 'tile_count', 'refinement_count')}),
		('Storage', {'fields': ('storage_format', 'storage_location', 'tiles_present', 'stored_tiles')}),
		('Sources', {'fields': ('source_details',)}),
	)

	def get_queryset(self, request):
		newer_versions = TerrainDataset.objects.filter(name=OuterRef('name'), id__gt=OuterRef('id')).exclude(status=TerrainDataset.Status.LOADING)
		queryset = super().get_queryset(request)

		return queryset.defer('refinements', 'sources').annotate(is_current=~Exists(newer_versions))

	@admin.display(boolean=True, description='Current')
	def is_current(self, dataset):
		return dataset.status != TerrainDataset.Status.LOADING and dataset.is_current

	@admin.display(description='Refinable tiles')
	def refinement_count(self, dataset):
		return len(dataset.refinements)

	@admin.display(description='Storage location')
	def storage_location(self, dataset):
		if dataset.status != TerrainDataset.Status.FILES:
			return 'Database: Terrain tile rows'

		return settings.TERRAIN_ROOT / str(dataset.storage_key)

	@admin.display(boolean=True, description='All six base tiles stored')
	def tiles_present(self, dataset):
		if dataset.status != TerrainDataset.Status.FILES:
			return dataset.tiles.filter(level=0, tile_x=0, tile_y=0).count() == 6

		directory = settings.TERRAIN_ROOT / str(dataset.storage_key)

		return all((directory / str(face) / '0/0/0.bin').is_file() for face in range(6))

	@admin.display(description='Computed tile rows')
	def stored_tiles(self, dataset):
		url = reverse('admin:terrain_terraintile_changelist')

		return format_html('<a href="{}?dataset__id__exact={}">Browse tile rows</a>', url, dataset.pk)

	@admin.display(description='Source metadata')
	def source_details(self, dataset):
		return format_html('<pre>{}</pre>', json.dumps(dataset.sources, indent=2))


@admin.register(TerrainTile)
class TerrainTileAdmin(ReadOnlyTerrainAdmin):
	list_display = ('id', 'dataset_version', 'face', 'level', 'tile_x', 'tile_y', 'compressed_bytes', 'created_ts', 'updated_ts')
	list_filter = (('dataset', admin.RelatedOnlyFieldListFilter), 'face', 'level')
	search_fields = ('=id', '=dataset__id')
	ordering = ('id',)
	readonly_fields = ('id', 'dataset', 'face', 'level', 'tile_x', 'tile_y', 'compressed_bytes', 'created_ts', 'updated_ts')
	fields = readonly_fields

	def get_queryset(self, request):
		queryset = super().get_queryset(request)

		return queryset.select_related('dataset').defer('data', 'dataset__refinements', 'dataset__sources').annotate(stored_size=Length('data'))

	@admin.display(description='Dataset version', ordering='dataset_id')
	def dataset_version(self, tile):
		return f'{tile.dataset.name}, version {tile.dataset_id}'

	@admin.display(description='Stored bytes', ordering='stored_size')
	def compressed_bytes(self, tile):
		return tile.stored_size


@admin.register(SunlightSelection)
class SunlightSelectionAdmin(ReadOnlyTerrainAdmin):
	list_display = ('id', 'name', 'latitude', 'longitude', 'radius_meters', 'created_ts', 'updated_ts')
	search_fields = ('name',)


@admin.register(SunlightHorizon)
class SunlightHorizonAdmin(ReadOnlyTerrainAdmin):
	list_display = ('id', 'dataset_id', 'latitude', 'longitude', 'version', 'compressed_bytes', 'created_ts', 'updated_ts')
	list_filter = ('dataset', 'version')
	readonly_fields = ('id', 'dataset', 'latitude', 'longitude', 'version', 'compressed_bytes', 'profile_summary', 'created_ts', 'updated_ts')
	fields = readonly_fields

	def get_queryset(self, request):
		return super().get_queryset(request).defer('data').annotate(stored_size=Length('data'))

	@admin.display(description='Stored bytes')
	def compressed_bytes(self, horizon):
		return horizon.stored_size

	@admin.display(description='Horizon bounds')
	def profile_summary(self, horizon):
		profile = HorizonProfile.decode(horizon.data)
		count = len(profile.lower)
		samples = []

		for index in range(0, count, count // 16):
			samples.append(
				{
					'azimuth_start_degrees': index * 360 / count,
					'lower_elevation_degrees': degrees(float(profile.lower[index])),
					'upper_elevation_degrees': degrees(float(profile.upper[index])),
				}
			)

		data = {'interval_count': count, 'sampled_intervals': samples}

		return format_html('<pre>{}</pre>', json.dumps(data, indent=2))


@admin.register(SunlightPreparation)
class SunlightPreparationAdmin(ReadOnlyTerrainAdmin):
	list_display = ('id', 'dataset_id', 'latitude', 'longitude', 'radius_meters', 'grid_size', 'version', 'created_ts', 'updated_ts')
	list_filter = ('dataset', 'version', 'grid_size')
	search_fields = ('=id', '=dataset__id')
	readonly_fields = ('id', 'dataset', 'latitude', 'longitude', 'radius_meters', 'grid_size', 'version', 'samples', 'created_ts', 'updated_ts')
	fields = readonly_fields
	raw_id_fields = ('dataset',)

	def get_queryset(self, request):
		return super().get_queryset(request).defer('samples')


@admin.register(SunlightResult)
class SunlightResultAdmin(ReadOnlyTerrainAdmin):
	list_display = ('id', 'preparation_id', 'timestamp', 'version', 'visible_sun_fraction', 'created_ts', 'updated_ts')
	list_filter = ('version', 'preparation__dataset')
	search_fields = ('=id', '=preparation__id')
	readonly_fields = (
		'id',
		'preparation',
		'timestamp',
		'version',
		'ephemeris_signature',
		'visible_sun_fraction',
		'thumbnail',
		'result',
		'created_ts',
		'updated_ts',
	)
	fields = readonly_fields
	raw_id_fields = ('preparation',)

	def get_queryset(self, request):
		return super().get_queryset(request).defer('result', 'thumbnail')


@admin.register(SunlightStudy)
class SunlightStudyAdmin(ReadOnlyTerrainAdmin):
	list_display = (
		'id',
		'name',
		'dataset_id',
		'status',
		'start_time',
		'end_time',
		'step_seconds',
		'worker_count',
		'expected_frames',
		'created_ts',
		'updated_ts',
	)
	list_filter = ('status',)


@admin.register(SunlightFrame)
class SunlightFrameAdmin(ReadOnlyTerrainAdmin):
	list_display = (
		'id',
		'study_id',
		'selection_id',
		'timestamp',
		'visible_sun_fraction',
		'visible_earth_fraction',
		'earth_center_visible',
		'created_ts',
		'updated_ts',
	)
	list_filter = ('study',)
	readonly_fields = (
		'id',
		'study',
		'selection_id',
		'timestamp',
		'visible_sun_fraction',
		'visible_earth_fraction',
		'earth_center_visible',
		'joint_visible_share',
		'joint_grid',
		'result_revision',
		'thumbnail',
		'cached_result',
		'cached_earth_result',
		'calculation_result',
		'created_ts',
		'updated_ts',
	)
	fields = readonly_fields
	raw_id_fields = ('study', 'cached_result', 'cached_earth_result')

	def get_queryset(self, request):
		return super().get_queryset(request).defer('result', 'thumbnail', 'joint_grid')


@admin.register(StudyCombinedVisibility)
class StudyCombinedVisibilityAdmin(ReadOnlyTerrainAdmin):
	list_display = ('id', 'study_id', 'selection_id', 'preparation_id', 'checked_frames', 'checked_seconds', 'created_ts', 'updated_ts')
	list_filter = ('study',)
	raw_id_fields = ('study', 'preparation')

	def get_queryset(self, request):
		return super().get_queryset(request).defer('visible_seconds')


@admin.register(LunarFeature)
class LunarFeatureAdmin(ReadOnlyTerrainAdmin):
	list_display = ('id', 'usgs_id', 'name', 'feature_type', 'latitude', 'longitude', 'approval_status', 'created_ts', 'updated_ts')
	list_filter = ('feature_type', 'approval_status')
	search_fields = ('name', 'clean_name', '=usgs_id')


@admin.register(EarthVisibilityResult)
class EarthVisibilityResultAdmin(ReadOnlyTerrainAdmin):
	list_display = ('id', 'preparation_id', 'timestamp', 'visible_earth_fraction', 'earth_center_visible', 'version', 'created_ts', 'updated_ts')
	list_filter = ('version', 'preparation__dataset', 'earth_center_visible')
	search_fields = ('=id', '=preparation__id')
	readonly_fields = (
		'id',
		'preparation',
		'timestamp',
		'version',
		'ephemeris_signature',
		'visible_earth_fraction',
		'earth_center_visible',
		'thumbnail',
		'result',
		'created_ts',
		'updated_ts',
	)
	fields = readonly_fields
	raw_id_fields = ('preparation',)

	def get_queryset(self, request):
		return super().get_queryset(request).defer('result', 'thumbnail')
