from django.urls import path

from terrain.views.studies.views import (
	SunlightFrameDetailView,
	SunlightStudyCalculateView,
	SunlightStudyDetailView,
	SunlightStudyListView,
	SunlightStudySiteCombinedVisibilityView,
	SunlightStudySiteDirectionsView,
	SunlightStudySiteHorizonView,
	SunlightStudySiteTerrainView,
	SunlightStudyStopView,
)

app_name = 'studies'
urlpatterns = [
	path('studies/', SunlightStudyListView.as_view(), name='sunlight-study-list'),
	path('studies/<int:study_id>/', SunlightStudyDetailView.as_view(), name='sunlight-study-detail'),
	path('studies/<int:study_id>/calculate/', SunlightStudyCalculateView.as_view(), name='sunlight-study-calculate'),
	path('studies/<int:study_id>/stop/', SunlightStudyStopView.as_view(), name='sunlight-study-stop'),
	path('studies/<int:study_id>/frames/<int:frame_id>/', SunlightFrameDetailView.as_view(), name='sunlight-frame-detail'),
	path(
		'studies/<int:study_id>/selections/<int:selection_id>/terrain/',
		SunlightStudySiteTerrainView.as_view(),
		name='sunlight-study-site-terrain',
	),
	path(
		'studies/<int:study_id>/selections/<int:selection_id>/directions/',
		SunlightStudySiteDirectionsView.as_view(),
		name='sunlight-study-site-directions',
	),
	path(
		'studies/<int:study_id>/selections/<int:selection_id>/combined/',
		SunlightStudySiteCombinedVisibilityView.as_view(),
		name='sunlight-study-site-combined-visibility',
	),
	path(
		'studies/<int:study_id>/selections/<int:selection_id>/horizon/',
		SunlightStudySiteHorizonView.as_view(),
		name='sunlight-study-site-horizon',
	),
]
