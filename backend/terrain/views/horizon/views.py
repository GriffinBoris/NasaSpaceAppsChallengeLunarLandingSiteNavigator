from terrain.services.site_horizon import location_horizon
from terrain.views.horizon.serializers import LocationHorizonOutputSerializer
from terrain.views.illumination.views import IlluminationView


class LocationHorizonView(IlluminationView):
	calculation = staticmethod(location_horizon)
	serializer_class = LocationHorizonOutputSerializer
