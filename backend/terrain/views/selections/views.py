from core.base_views import ProjectBaseAPIView
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.response import Response

from terrain.models.SunlightSelection import SunlightSelection
from terrain.models.SunlightStudy import SunlightStudy
from terrain.services.study_schedule import STEP_OPTIONS
from terrain.views.selections.serializers import SunlightSelectionInputSerializer, SunlightSelectionOutputSerializer


@method_decorator(ensure_csrf_cookie, name='dispatch')
class SunlightSelectionListView(ProjectBaseAPIView):
	def get(self, request):
		return Response(
			{
				'selections': SunlightSelectionOutputSerializer(SunlightSelection.objects.all(), many=True).data,
				'step_options': [{'seconds': seconds, 'label': label} for seconds, label in STEP_OPTIONS],
				'worker_options': [{'value': value, 'label': label} for value, label in SunlightStudy.WorkerCount.choices],
				'default_worker_count': SunlightStudy.WorkerCount.FOUR,
			}
		)

	def post(self, request):
		serializer = SunlightSelectionInputSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		selection = serializer.save()

		return Response(SunlightSelectionOutputSerializer(selection).data, status=201)


class SunlightSelectionDetailView(ProjectBaseAPIView):
	def patch(self, request, selection_id):
		selection = get_object_or_404(SunlightSelection, pk=selection_id)
		serializer = SunlightSelectionInputSerializer(selection, data=request.data, partial=True)
		serializer.is_valid(raise_exception=True)
		serializer.save()

		return Response(SunlightSelectionOutputSerializer(selection).data)

	def delete(self, request, selection_id):
		selection = get_object_or_404(SunlightSelection, pk=selection_id)
		selection.delete()

		return Response(status=204)
