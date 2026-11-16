import numpy
import open3d

from terrain.services.surface_mesh import MINIMUM_INTERSECTION_DISTANCE, SurfaceMesh

BOUNDARY_ORIGIN_DISTANCE = 0.01


class Open3DSurfaceBlock:
	def __init__(self, positions):
		middle_row = (positions.shape[0] - 1) // 2
		middle_column = (positions.shape[1] - 1) // 2
		self.anchor = positions[middle_row, middle_column].copy()
		up = self.anchor / numpy.linalg.norm(self.anchor)
		reference_axis = numpy.array([0.0, 0, 1])

		if abs(up[2]) > 0.9:
			reference_axis = numpy.array([0.0, 1, 0])

		east = numpy.cross(reference_axis, up)
		east /= numpy.linalg.norm(east)
		north = numpy.cross(up, east)
		self.basis = numpy.column_stack((east, north, up))
		local_positions = (positions.reshape(-1, 3) - self.anchor) @ self.basis
		vertices = local_positions.astype(numpy.float32)
		vertex_indices = numpy.arange(positions.shape[0] * positions.shape[1], dtype=numpy.uint32).reshape(positions.shape[:2])
		top_left = vertex_indices[:-1, :-1].ravel()
		top_right = vertex_indices[:-1, 1:].ravel()
		bottom_left = vertex_indices[1:, :-1].ravel()
		bottom_right = vertex_indices[1:, 1:].ravel()
		first_triangles = numpy.column_stack((top_left, bottom_left, top_right))
		second_triangles = numpy.column_stack((top_right, bottom_left, bottom_right))
		triangle_indices = numpy.concatenate((first_triangles, second_triangles))

		triangles = local_positions[triangle_indices]
		normals = numpy.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
		normals /= numpy.linalg.norm(normals, axis=1, keepdims=True)
		rounding_errors = vertices.astype(numpy.float64) - local_positions
		plane_errors = numpy.abs(numpy.sum(rounding_errors[triangle_indices] * normals[:, None, :], axis=2))
		self.maximum_plane_error = float(plane_errors.max())
		self.scene = None

		if self.maximum_plane_error > MINIMUM_INTERSECTION_DISTANCE / 4:
			return

		self.scene = open3d.t.geometry.RaycastingScene(nthreads=1)
		self.scene.add_triangles(open3d.core.Tensor(vertices), open3d.core.Tensor(triangle_indices))

	def blocked_rays(self, origin, directions):
		rays = numpy.empty((len(directions), 6), dtype=numpy.float32)
		rays[:, :3] = (origin - self.anchor) @ self.basis
		rays[:, 3:] = directions @ self.basis
		result = self.scene.test_occlusions(open3d.core.Tensor(rays), tnear=MINIMUM_INTERSECTION_DISTANCE, nthreads=1)

		return result.numpy()


class Open3DSurfaceMesh(SurfaceMesh):
	def __init__(self, coordinates, heights, reference_radius):
		super().__init__(coordinates, heights, reference_radius)

		corners = self.positions[[0, 0, -1, -1], [0, -1, -1, 0]]
		self.boundary_normals = numpy.cross(corners, numpy.roll(corners, -1, axis=0))
		self.boundary_normals /= numpy.linalg.norm(self.boundary_normals, axis=1, keepdims=True)
		block = Open3DSurfaceBlock(self.positions)
		self.maximum_plane_error = block.maximum_plane_error
		self.blocks = []

		if block.scene is not None:
			self.blocks = [block]
			return

		middle = self.segment_count // 2
		blocks = []

		for top, bottom in ((0, middle), (middle, self.segment_count)):
			for left, right in ((0, middle), (middle, self.segment_count)):
				blocks.append(Open3DSurfaceBlock(self.positions[top : bottom + 1, left : right + 1]))

		if all(block.scene is not None for block in blocks):
			self.blocks = blocks
			self.maximum_plane_error = max(block.maximum_plane_error for block in blocks)

	def blocked_rays(self, origin, directions):
		near_boundary = numpy.min(numpy.abs(self.boundary_normals @ origin)) <= BOUNDARY_ORIGIN_DISTANCE

		if not self.blocks or near_boundary:
			return super().blocked_rays(origin, directions)

		blocked = numpy.zeros(len(directions), dtype=bool)

		for block in self.blocks:
			ray_indices = numpy.flatnonzero(~blocked)

			if not len(ray_indices):
				break

			blocked[ray_indices] = block.blocked_rays(origin, directions[ray_indices])

		return blocked
