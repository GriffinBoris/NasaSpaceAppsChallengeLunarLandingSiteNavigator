from core.base_views import ProjectBaseAPIView
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from ephemeris.services.positions import EphemerisTimeError, EphemerisUnavailable
from ephemeris.views.exceptions import EphemerisServiceUnavailable
from kombu.exceptions import OperationalError
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response

from terrain.models.SunlightFrame import SunlightFrame
from terrain.models.SunlightStudy import SunlightStudy
from terrain.services.site_area import site_directions, site_terrain
from terrain.services.site_combined_visibility import site_combined_visibility
from terrain.services.site_horizon import site_horizon
from terrain.services.study_jobs import ACTIVE_STATUSES, delete_study, queue_study, stop_study
from terrain.services.study_results import result_changes
from terrain.services.terrain_surface import TerrainAnalysisUnavailable
from terrain.views.studies.serializers import (
	SiteCombinedVisibilityOutputSerializer,
	SiteDirectionsOutputSerializer,
	SiteHorizonOutputSerializer,
	SiteTerrainOutputSerializer,
	StudyResultChangesInputSerializer,
	SunlightFrameDetailOutputSerializer,
	SunlightFrameOutputSerializer,
	SunlightStudyCalculateInputSerializer,
	SunlightStudyEditInputSerializer,
	SunlightStudyInputSerializer,
	SunlightStudyOutputSerializer,
)


def study_summaries():
	complete = Q(frames__visible_sun_fraction__isnull=False, frames__cached_earth_result__isnull=False)

	return SunlightStudy.objects.annotate(
		completed_frames=Count('frames', filter=complete),
		saved_results=Count('frames', filter=Q(frames__visible_sun_fraction__isnull=False)) + Count('frames__cached_earth_result'),
	)


class StudyConflict(APIException):
	status_code = 409
	default_detail = 'This plan is already queued, running, stopping, or complete. Refresh to see its results.'
	default_code = 'study_conflict'


class StudyQueueUnavailable(APIException):
	status_code = 503
	default_detail = 'Unable to queue this plan. Check that Redis is running, then try again.'
	default_code = 'study_queue_unavailable'


def enqueue_study(study_id, worker_count=None):
	try:
		queued = queue_study(study_id, worker_count=worker_count)
	except OperationalError as error:
		raise StudyQueueUnavailable() from error

	if not queued:
		raise StudyConflict()


class SunlightStudyListView(ProjectBaseAPIView):
	def get(self, request):
		studies = study_summaries()

		return Response(SunlightStudyOutputSerializer(studies, many=True).data)

	def post(self, request):
		serializer = SunlightStudyInputSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		study = serializer.save()
		enqueue_study(study.pk)
		study = study_summaries().get(pk=study.pk)

		return Response(SunlightStudyOutputSerializer(study).data, status=201)


class SunlightStudyDetailView(ProjectBaseAPIView):
	@transaction.atomic
	def get(self, request, study_id):
		study = get_object_or_404(study_summaries(), pk=study_id)
		query = StudyResultChangesInputSerializer(data=request.query_params)
		query.is_valid(raise_exception=True)
		frames, reset = result_changes(study, query.validated_data['after_revision'])
		frames = frames.select_related('cached_earth_result').defer('result', 'joint_grid', 'cached_earth_result__result')

		return Response(
			{
				'reset': reset,
				'study': SunlightStudyOutputSerializer(study).data,
				'frames': SunlightFrameOutputSerializer(frames, many=True).data,
			}
		)

	def put(self, request, study_id):
		with transaction.atomic():
			study = get_object_or_404(SunlightStudy.objects.select_for_update(), pk=study_id)

			if study.status in ACTIVE_STATUSES:
				raise StudyConflict('Stop the calculation before editing this plan.')

			serializer = SunlightStudyEditInputSerializer(study, data=request.data)
			serializer.is_valid(raise_exception=True)
			study = serializer.save()

		if study.status == SunlightStudy.Status.PENDING:
			enqueue_study(study.pk)

		study = study_summaries().get(pk=study_id)

		return Response(SunlightStudyOutputSerializer(study).data)

	def delete(self, request, study_id):
		study = get_object_or_404(SunlightStudy, pk=study_id)

		if not delete_study(study.pk):
			raise StudyConflict('Stop the calculation before deleting this study.')

		return Response(status=204)


class SunlightStudyCalculateView(ProjectBaseAPIView):
	def post(self, request, study_id):
		get_object_or_404(SunlightStudy, pk=study_id)
		serializer = SunlightStudyCalculateInputSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		enqueue_study(study_id, worker_count=serializer.validated_data.get('worker_count'))
		study = study_summaries().get(pk=study_id)

		return Response(SunlightStudyOutputSerializer(study).data, status=202)


class SunlightStudyStopView(ProjectBaseAPIView):
	def post(self, request, study_id):
		study = get_object_or_404(SunlightStudy, pk=study_id)
		stop_study(study.pk, study.run_id)
		study = study_summaries().get(pk=study_id)

		return Response(SunlightStudyOutputSerializer(study).data)


class SunlightFrameDetailView(ProjectBaseAPIView):
	def get(self, request, study_id, frame_id):
		frame = get_object_or_404(SunlightFrame.objects.select_related('cached_result', 'cached_earth_result'), study_id=study_id, pk=frame_id)

		return Response(SunlightFrameDetailOutputSerializer(frame).data)


def get_pinned_selection(study, selection_id):
	for selection in study.selections:
		if selection['id'] == selection_id:
			return selection

	raise Http404


class SunlightStudySiteTerrainView(ProjectBaseAPIView):
	def get(self, request, study_id, selection_id):
		study = get_object_or_404(SunlightStudy.objects.select_related('dataset'), pk=study_id)
		selection = get_pinned_selection(study, selection_id)

		try:
			terrain = site_terrain(study.dataset, selection)
		except TerrainAnalysisUnavailable as error:
			raise ValidationError({'dataset_id': str(error)}) from error

		return Response(SiteTerrainOutputSerializer(terrain).data)


class SunlightStudySiteDirectionsView(ProjectBaseAPIView):
	def get(self, request, study_id, selection_id):
		study = get_object_or_404(SunlightStudy.objects.select_related('dataset'), pk=study_id)
		selection = get_pinned_selection(study, selection_id)

		try:
			angles = site_directions(study, selection)
		except EphemerisTimeError as error:
			raise ValidationError({'start_time': str(error)}) from error
		except EphemerisUnavailable as error:
			raise EphemerisServiceUnavailable(str(error)) from error
		except TerrainAnalysisUnavailable as error:
			raise ValidationError({'dataset_id': str(error)}) from error

		return Response(SiteDirectionsOutputSerializer(angles).data)


class SunlightStudySiteHorizonView(ProjectBaseAPIView):
	def get(self, request, study_id, selection_id):
		study = get_object_or_404(SunlightStudy.objects.select_related('dataset'), pk=study_id)
		selection = get_pinned_selection(study, selection_id)
		horizon = site_horizon(study.dataset, selection)

		return Response(SiteHorizonOutputSerializer(horizon).data)


class SunlightStudySiteCombinedVisibilityView(ProjectBaseAPIView):
	@transaction.atomic
	def get(self, request, study_id, selection_id):
		study = get_object_or_404(SunlightStudy, pk=study_id)
		selection = get_pinned_selection(study, selection_id)
		query = StudyResultChangesInputSerializer(data=request.query_params)
		query.is_valid(raise_exception=True)

		try:
			combined = site_combined_visibility(study, selection, query.validated_data['after_revision'])
		except TerrainAnalysisUnavailable as error:
			raise ValidationError({'selection_id': str(error)}) from error

		return Response(SiteCombinedVisibilityOutputSerializer(combined).data)
