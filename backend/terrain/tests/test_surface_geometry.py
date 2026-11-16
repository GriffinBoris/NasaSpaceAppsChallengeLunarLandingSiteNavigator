from types import SimpleNamespace

import numpy
import pytest

from terrain.services.surface_coordinates import cube_surface_directions, face_coordinates, rays_cross_tile, surface_direction
from terrain.services.surface_mesh import SurfaceMesh, rays_cross_box, triangle_distances
from terrain.services.terrain_surface import TerrainSurface


@pytest.mark.parametrize(
	('latitude', 'longitude', 'expected'),
	[(0, 0, [1, 0, 0]), (0, 90, [0, 1, 0]), (90, 0, [0, 0, 1]), (-90, 0, [0, 0, -1]), (0, 180, [-1, 0, 0])],
)
def test_locations_use_spice_axes(latitude, longitude, expected):
	numpy.testing.assert_allclose(surface_direction(latitude, longitude), expected, atol=1e-15)


@pytest.mark.parametrize('face', range(6))
def test_cube_coordinates_round_trip_on_every_face(face):
	direction = cube_surface_directions(face, numpy.array(0.25), numpy.array(-0.6))

	actual_face, horizontal, vertical = face_coordinates(direction)

	assert actual_face == face
	assert horizontal == pytest.approx(0.25)
	assert vertical == pytest.approx(-0.6)


def test_triangle_intersections_distinguish_blocked_clear_parallel_and_backward_rays():
	triangles = numpy.array([[[2, -1, -1], [2, 1, -1], [2, 0, 1]]], dtype=float)
	directions = numpy.array([[1, 0, 0], [1, 2, 0], [0, 1, 0], [-1, 0, 0]], dtype=float)

	distances = triangle_distances(numpy.zeros(3), directions, triangles)[:, 0]

	assert distances[0] == pytest.approx(2)
	assert numpy.isinf(distances[1:]).all()


def test_parallel_rays_only_cross_a_box_when_inside_its_parallel_slabs():
	directions = numpy.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)

	selection = rays_cross_box(numpy.zeros(3), directions, numpy.array([1, -1, -1]), numpy.array([2, 1, 1]))

	numpy.testing.assert_array_equal(selection, [True, False, False])


def test_mesh_hierarchy_matches_all_triangle_intersections_for_rough_terrain():
	random = numpy.random.default_rng(728)
	mesh = SurfaceMesh((0, 2, 2, 2), random.uniform(-500, 1000, (17, 17)), 1737400)
	origin = numpy.array([1737500.0, 0, 0])
	directions = random.normal(size=(300, 3))
	directions /= numpy.linalg.norm(directions, axis=1, keepdims=True)
	triangles = mesh.triangles(0, 0, 16, 16)
	expected = numpy.isfinite(triangle_distances(origin, directions, triangles)).any(axis=1)

	numpy.testing.assert_array_equal(mesh.blocked_rays(origin, directions), expected)


def test_tile_cones_include_rays_that_reach_a_tile_and_exclude_rays_pointing_away():
	origin = numpy.array([2.0, 0, 0])
	directions = numpy.array([[-1, 0, 0], [1, 0, 0]], dtype=float)

	selection = rays_cross_tile(origin, directions, (1, 0, 0, 0), numpy.array([4.0, 4.0]))

	numpy.testing.assert_array_equal(selection, [True, False])


@pytest.fixture
def terrain_surface(monkeypatch):
	refinements = []

	for face in range(6):
		for level in range(2):
			for tile_y in range(2**level):
				for tile_x in range(2**level):
					refinements.append(f'{face}/{level}/{tile_x}/{tile_y}')

	dataset = SimpleNamespace(
		status='ready', storage_format='int16-delta-gzip', frame='MOON_ME_DE421', reference_radius=1737400, tile_size=5, refinements=refinements
	)
	monkeypatch.setattr('terrain.services.terrain_surface.read_tile_heights', lambda dataset, *coordinates: numpy.zeros(25))

	return TerrainSurface(dataset)


def test_surface_uses_finest_available_tiles_and_blocks_the_far_side(terrain_surface):
	position, normal, level = terrain_surface.surface_point(0, 0)

	numpy.testing.assert_allclose(position, [1737400, 0, 0], atol=1e-6)
	assert normal @ position > 0
	assert level == 2

	blocked = terrain_surface.blocked_rays(position + numpy.array([0.01, 0, 0]), numpy.array([[1.0, 0, 0], [-1.0, 0, 0]]))

	numpy.testing.assert_array_equal(blocked, [False, True])
	assert all(coordinates[1] == 2 for coordinates in terrain_surface.meshes)


def test_terrain_curvature_allows_a_horizontal_ray_but_blocks_a_downward_ray(terrain_surface):
	origin = numpy.array([1738400.0, 0, 0])
	directions = numpy.array([[0.0, 1, 0], [-0.2, 1, 0]])
	directions /= numpy.linalg.norm(directions, axis=1, keepdims=True)

	numpy.testing.assert_array_equal(terrain_surface.blocked_rays(origin, directions), [False, True])


def test_terrain_reuses_cache_without_tracing_unreachable_meshes(terrain_surface, monkeypatch):
	distant = terrain_surface.mesh((1, 2, 0, 0))

	def unexpected_trace(*arguments):
		raise AssertionError('Rays pointing away from cached terrain must skip its mesh.')

	monkeypatch.setattr(distant, 'blocked_rays', unexpected_trace)
	position, normal, _ = terrain_surface.surface_point(0, 0)
	directions = numpy.array([[1.0, 0, 0]])

	numpy.testing.assert_array_equal(terrain_surface.blocked_rays(position + normal * 0.001, directions), [False])


def test_surface_point_lies_on_its_actual_triangle():
	mesh = SurfaceMesh((0, 0, 0, 0), numpy.zeros((5, 5)), 1737400)
	direction = surface_direction(12, 16)
	_, horizontal, vertical = face_coordinates(direction)

	position, normal = mesh.surface_point(direction, (horizontal + 1) / 2, (1 - vertical) / 2)
	distances = triangle_distances(numpy.zeros(3), direction[None, :], mesh.triangles(0, 0, 4, 4))

	assert numpy.linalg.norm(position) == pytest.approx(distances.min())
	assert numpy.linalg.norm(position) < 1737400
	assert normal @ position > 0


def test_a_ridge_blocks_low_sunlight_but_not_high_sunlight():
	heights = numpy.zeros((5, 5))
	heights[:, 3] = 1000
	mesh = SurfaceMesh((0, 6, 32, 32), heights, 1737400)
	position = mesh.positions[2, 1]
	up = position / numpy.linalg.norm(position)
	east = numpy.cross(numpy.array([0.0, 0, 1]), up)
	east /= numpy.linalg.norm(east)
	origin = position + up * 0.01
	angles = numpy.radians([1, 10])
	directions = numpy.cos(angles)[:, None] * east + numpy.sin(angles)[:, None] * up

	numpy.testing.assert_array_equal(mesh.blocked_rays(origin, directions), [True, False])


@pytest.mark.parametrize('observer_direction', [[1, 0.2, 0.3], [-0.2, 1, 0.1], [0.1, -0.3, -1]])
def test_tile_hierarchy_matches_the_complete_surface_mesh(terrain_surface, observer_direction):
	triangles = []

	for face in range(6):
		for tile_y in range(4):
			for tile_x in range(4):
				mesh = SurfaceMesh((face, 2, tile_x, tile_y), numpy.zeros((5, 5)), 1737400)
				triangles.append(mesh.triangles(0, 0, 4, 4))

	origin = numpy.array(observer_direction, dtype=float)
	origin *= 1737500 / numpy.linalg.norm(origin)
	random = numpy.random.default_rng(930)
	directions = random.normal(size=(100, 3))
	directions /= numpy.linalg.norm(directions, axis=1, keepdims=True)
	expected = numpy.isfinite(triangle_distances(origin, directions, numpy.concatenate(triangles))).any(axis=1)

	numpy.testing.assert_array_equal(terrain_surface.blocked_rays(origin, directions), expected)
