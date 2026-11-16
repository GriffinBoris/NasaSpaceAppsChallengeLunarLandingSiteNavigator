import numpy
import pytest

from terrain.models.SunlightHorizon import SunlightHorizon
from terrain.models.TerrainDataset import TerrainDataset
from terrain.services.horizon_builder import BIN_WIDTH, estimated_box, update_edges
from terrain.services.horizon_profile import HORIZON_BIN_COUNT, HorizonProfile, local_basis
from terrain.services.horizon_storage import load_profiles, save_profile
from terrain.services.horizon_surface import HorizonSurface
from terrain.services.surface_mesh import SurfaceMesh
from terrain.services.terrain_surface import TerrainSurface


@pytest.mark.parametrize('face', range(6))
def test_estimated_boxes_contain_all_terrain_vertices(face):
	coordinates = face, 2, 2, 1
	minimum, maximum = estimated_box(coordinates, 1721000, 1754000)
	random = numpy.random.default_rng(123)
	mesh = SurfaceMesh(coordinates, random.uniform(-16400, 16600, (65, 65)), 1737400)

	assert (mesh.positions >= minimum).all()
	assert (mesh.positions <= maximum).all()


@pytest.mark.parametrize('latitude,longitude', [(12.3, 16.7), (-89.9, 173.4), (45.6, -135.7)])
def test_bounded_horizons_match_full_terrain_ray_tracing(rough_surface, latitude, longitude):
	surface = HorizonSurface(rough_surface)
	position, normal, _ = surface.surface_point(latitude, longitude)
	origin = position + normal * 0.001
	random = numpy.random.default_rng(937)
	directions = random.normal(size=(4096, 3))
	directions /= numpy.linalg.norm(directions, axis=1, keepdims=True)
	expected = rough_surface.blocked_rays(origin, directions)

	surface.prepare_profile(position, normal)
	actual = surface.blocked_rays(origin, directions)
	profile, _ = surface.profiles[origin.tobytes()]
	_, uncertain = profile.classify(directions, local_basis(position))

	numpy.testing.assert_array_equal(actual, expected)
	assert uncertain.mean() < 0.1
	assert (profile.lower <= profile.upper).all()

	azimuths = (numpy.arange(0, HORIZON_BIN_COUNT, 4) + 0.5) * BIN_WIDTH
	elevations = numpy.concatenate((profile.lower[::4] - 1e-7, profile.upper[::4] + 1e-7))
	azimuths = numpy.tile(azimuths, 2)
	local_directions = numpy.column_stack(
		(numpy.sin(azimuths) * numpy.cos(elevations), numpy.cos(azimuths) * numpy.cos(elevations), numpy.sin(elevations))
	)
	directions = local_directions @ local_basis(position).T
	expected = rough_surface.blocked_rays(origin, directions)

	numpy.testing.assert_array_equal(surface.blocked_rays(origin, directions), expected)


def test_horizon_upper_bound_captures_a_peak_narrower_than_one_angular_bin():
	lower = numpy.full(HORIZON_BIN_COUNT, -numpy.pi / 2)
	upper = lower.copy()
	angles = numpy.array([BIN_WIDTH * 0.1, BIN_WIDTH * 0.2])
	positions = numpy.column_stack((numpy.sin(angles), numpy.cos(angles), numpy.full(2, numpy.tan(numpy.radians(10))))) * 1000

	assert update_edges(lower, upper, positions[:1], positions[1:])
	assert numpy.degrees(upper[0]) >= 10
	assert lower[0] == -numpy.pi / 2

	profile = HorizonProfile(lower, upper)
	direction = numpy.array([[numpy.sin(angles.mean()), numpy.cos(angles.mean()), numpy.tan(numpy.radians(5))]])
	_, uncertain = profile.classify(direction, numpy.eye(3))

	assert uncertain[0]


def test_horizon_encoding_preserves_float64_bounds():
	lower = numpy.linspace(-0.1, 0.1, HORIZON_BIN_COUNT)
	upper = lower + 0.001
	profile = HorizonProfile.decode(HorizonProfile(lower, upper).encode())

	numpy.testing.assert_array_equal(profile.lower, lower)
	numpy.testing.assert_array_equal(profile.upper, upper)


@pytest.mark.django_db
def test_stored_horizons_reuse_the_exact_dataset_and_location(analysis_dataset, monkeypatch):
	location = (12.345, 16.789)
	surface = HorizonSurface(TerrainSurface(analysis_dataset))
	position, normal, _ = surface.surface_point(*location)
	content = surface.prepare_profile(position, normal)
	save_profile(analysis_dataset, location, content)
	stored = SunlightHorizon.objects.get()

	assert stored.dataset_id == analysis_dataset.pk
	assert stored.latitude == 12.345
	assert stored.longitude == 16.789
	assert stored.version == 1

	def fail_build(*arguments):
		raise AssertionError('A completed horizon must be reused.')

	monkeypatch.setattr('terrain.services.horizon_builder.HorizonBuilder.build', fail_build)
	cached = load_profiles(analysis_dataset, [location])[0]
	reused = HorizonSurface(TerrainSurface(analysis_dataset))
	reused.prepare_profile(position, normal, cached)

	assert SunlightHorizon.objects.count() == 1
	assert reused.profiles.keys() == surface.profiles.keys()


@pytest.mark.django_db
def test_horizons_from_other_datasets_and_versions_are_not_reused(analysis_dataset):
	other_dataset = TerrainDataset.objects.create(
		name='other', frame='MOON_ME_DE421', reference_radius=1737400, tile_size=33, max_level=0, tile_count=0, refinements=[], sources=[]
	)
	location = (12.345, 16.789)
	content = HorizonProfile.unresolved().encode()
	SunlightHorizon.objects.create(dataset=other_dataset, latitude=location[0], longitude=location[1], version=1, data=content)
	SunlightHorizon.objects.create(dataset=analysis_dataset, latitude=location[0], longitude=location[1], version=0, data=content)

	assert load_profiles(analysis_dataset, [location]) == [None]

	save_profile(analysis_dataset, location, content)

	assert load_profiles(analysis_dataset, [location]) == [content]
	assert SunlightHorizon.objects.count() == 3


@pytest.mark.django_db
def test_missing_horizons_use_direct_tracing_without_building(analysis_dataset, monkeypatch):
	def fail_build(*arguments):
		raise AssertionError('Missing horizons must not build during tracing.')

	monkeypatch.setattr('terrain.services.horizon_builder.HorizonBuilder.build', fail_build)
	surface = HorizonSurface(TerrainSurface(analysis_dataset))
	position, normal, _ = surface.surface_point(12.345, 16.789)
	origin = position + normal * 0.001
	directions = numpy.array([position / numpy.linalg.norm(position), -position / numpy.linalg.norm(position)])

	numpy.testing.assert_array_equal(surface.blocked_rays(origin, directions), [False, True])
	assert not SunlightHorizon.objects.exists()
