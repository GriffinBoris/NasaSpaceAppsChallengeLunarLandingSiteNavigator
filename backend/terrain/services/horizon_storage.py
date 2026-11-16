from itertools import batched

from django.db.models import Q

from terrain.models.SunlightHorizon import SunlightHorizon
from terrain.services.horizon_profile import HORIZON_VERSION


def load_profiles(dataset, locations):
	profiles = {}

	for group in batched(locations, 128):
		query = Q()

		for latitude, longitude in group:
			query |= Q(latitude=latitude, longitude=longitude)

		rows = SunlightHorizon.objects.filter(query, dataset=dataset, version=HORIZON_VERSION).values_list('latitude', 'longitude', 'data')

		for latitude, longitude, content in rows:
			profiles[latitude, longitude] = content

	return [profiles.get(location) for location in locations]


def save_profile(dataset, location, content):
	latitude, longitude = location
	SunlightHorizon.objects.get_or_create(
		dataset=dataset, latitude=latitude, longitude=longitude, version=HORIZON_VERSION, defaults={'data': content}
	)
