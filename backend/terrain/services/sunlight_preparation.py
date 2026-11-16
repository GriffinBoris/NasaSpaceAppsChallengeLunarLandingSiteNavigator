from terrain.models.SunlightPreparation import SunlightPreparation
from terrain.services import illumination_patch
from terrain.services.illumination import IlluminationPoint
from terrain.services.illumination_patch import IlluminationRegion, patch_locations
from terrain.services.terrain_surface import TerrainSurface

PREPARATION_VERSION = 1


def prepare_selection(dataset, selection):
	radius_meters = selection['radius_meters']
	grid_size = 1 if radius_meters is None else illumination_patch.PATCH_GRID_SIZE
	identity = {
		'dataset': dataset,
		'latitude': selection['latitude'],
		'longitude': selection['longitude'],
		'radius_meters': 0 if radius_meters is None else radius_meters,
		'grid_size': grid_size,
		'version': PREPARATION_VERSION,
	}
	stored = SunlightPreparation.objects.filter(**identity).first()

	if stored is not None:
		return stored

	locations = [(selection['latitude'], selection['longitude'])]

	if radius_meters is not None:
		locations = patch_locations(selection['latitude'], selection['longitude'], radius_meters, dataset.reference_radius, grid_size)

	surface = TerrainSurface(dataset)
	samples = []

	for location in locations:
		if location is None:
			samples.append(None)
			continue

		point = IlluminationPoint(surface, *location)
		samples.append(point.geometry())

	preparation, _ = SunlightPreparation.objects.get_or_create(**identity, defaults={'samples': samples})

	return preparation


def restore_selection(preparation):
	surface = TerrainSurface(preparation.dataset)

	if preparation.grid_size == 1:
		point = IlluminationPoint(surface, preparation.latitude, preparation.longitude, geometry=preparation.samples[0])

		return [point], None

	region = IlluminationRegion(
		surface,
		preparation.latitude,
		preparation.longitude,
		preparation.radius_meters,
		grid_size=preparation.grid_size,
		samples=preparation.samples,
	)

	return region.points, region
