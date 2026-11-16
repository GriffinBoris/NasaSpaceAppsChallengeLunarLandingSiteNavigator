from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from importlib import import_module
from multiprocessing import get_context

import django
from django.conf import settings
from django.db import connection, connections

worker_samples = None


def initialize_sunlight_worker(database, dataset_id, locations, stop_event, geometry):
	global worker_samples

	settings.DATABASES['default'] = database
	django.setup()

	try:
		samples_module = import_module('terrain.services.sunlight_samples')
		worker_samples = samples_module.SunlightSamples(dataset_id, locations, stop_event, geometry=geometry)
	finally:
		connections.close_all()


def prepare_worker_profile(index, content):
	try:
		return worker_samples.prepare_profile(index, content)
	finally:
		connections.close_all()


def calculate_worker_frame(body_vectors, body_radius, body):
	try:
		return worker_samples.calculate(body_vectors, body_radius, body)
	finally:
		connections.close_all()


class SunlightProcessor:
	def __init__(self, dataset_id, locations, workers, database=None, geometry=None):
		self.dataset_id = dataset_id
		self.locations = locations
		self.workers = min(workers, len(locations))

		if database is None:
			database = connection.settings_dict

		self.database = dict(database)
		self.geometry = geometry
		self.groups = []

		for group in range(self.workers):
			start = len(locations) * group // self.workers
			stop = len(locations) * (group + 1) // self.workers
			self.groups.append(range(start, stop))

	def __enter__(self):
		context = get_context('spawn')
		self.stop_event = context.Event()
		self.executors = []
		self.local_samples = None

		try:
			if self.workers == 1:
				samples_module = import_module('terrain.services.sunlight_samples')
				self.local_samples = samples_module.SunlightSamples(self.dataset_id, self.locations, self.stop_event, geometry=self.geometry)
			else:
				for indices in self.groups:
					group_geometry = None

					if self.geometry is not None:
						group_geometry = self.geometry[indices.start : indices.stop]

					executor = ProcessPoolExecutor(
						max_workers=1,
						mp_context=context,
						initializer=initialize_sunlight_worker,
						initargs=(self.database, self.dataset_id, self.locations[indices.start : indices.stop], self.stop_event, group_geometry),
					)
					self.executors.append(executor)
		except BaseException:
			self.close()
			raise

		return self

	def __exit__(self, exception_type, exception, traceback):
		self.close()

	def close(self):
		self.stop_event.set()

		for executor in self.executors:
			executor.shutdown(wait=True, cancel_futures=True)

	def prepare_profiles(self, contents, build_missing):
		if self.local_samples is not None:
			yield None, None

			for index, content in enumerate(contents):
				if content is not None or build_missing:
					yield index, self.local_samples.prepare_profile(index, content)

			return

		remaining = []

		for indices in self.groups:
			indices_to_prepare = [index for index in indices if contents[index] is not None or build_missing]
			remaining.append(iter(indices_to_prepare))

		pending = {}

		def submit_next(group):
			index = next(remaining[group], None)

			if index is not None:
				local_index = index - self.groups[group].start
				future = self.executors[group].submit(prepare_worker_profile, local_index, contents[index])
				pending[future] = index, group

		for group, executor in enumerate(self.executors):
			pending[executor.submit(prepare_worker_profile, None, None)] = None, group

		while pending:
			completed, _ = wait(pending, timeout=1, return_when=FIRST_COMPLETED)

			if not completed:
				yield None, None

			for future in completed:
				index, group = pending.pop(future)
				content = future.result()
				yield index, content
				submit_next(group)

	def calculate(self, body_vectors, body_radius, body='SUN'):
		if self.local_samples is not None:
			yield len(self.locations), self.local_samples.calculate(body_vectors, body_radius, body)
			return

		pending = {}
		results = [None] * len(self.locations)
		completed_count = 0

		for executor, indices in zip(self.executors, self.groups, strict=True):
			future = executor.submit(calculate_worker_frame, body_vectors[indices.start : indices.stop], body_radius, body)
			pending[future] = indices

		while pending:
			completed, _ = wait(pending, timeout=1, return_when=FIRST_COMPLETED)

			for future in completed:
				indices = pending.pop(future)
				results[indices.start : indices.stop] = future.result()
				completed_count += len(indices)

			yield completed_count, results
