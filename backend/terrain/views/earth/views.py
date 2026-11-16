from terrain.services.earth_visibility import calculate_earth_point, iter_earth_patch
from terrain.views.earth.serializers import EarthVisibilityOutputSerializer, EarthVisibilityPatchOutputSerializer
from terrain.views.illumination.views import IlluminationPatchView, IlluminationView


class EarthVisibilityView(IlluminationView):
	calculation = staticmethod(calculate_earth_point)
	serializer_class = EarthVisibilityOutputSerializer


class EarthVisibilityPatchView(IlluminationPatchView):
	calculation = staticmethod(iter_earth_patch)
	result_serializer = EarthVisibilityPatchOutputSerializer
