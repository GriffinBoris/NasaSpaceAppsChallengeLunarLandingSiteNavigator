from datetime import UTC
from math import ceil

from rest_framework import serializers

from terrain.models.SunlightFrame import SunlightFrame
from terrain.models.SunlightSelection import SunlightSelection
from terrain.models.SunlightStudy import SunlightStudy
from terrain.models.TerrainDataset import TerrainDataset
from terrain.services.site_combined_visibility import rebuild_combined_visibility
from terrain.services.study_schedule import STEP_OPTIONS, timestamps
from terrain.views.horizon.serializers import HorizonOutputSerializer


class SunlightStudyScheduleInputSerializer(serializers.ModelSerializer):
	name = serializers.CharField(max_length=120)
	selection_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
	start_time = serializers.DateTimeField(default_timezone=UTC)
	end_time = serializers.DateTimeField(default_timezone=UTC)
	step_seconds = serializers.ChoiceField(choices=STEP_OPTIONS)

	class Meta:
		model = SunlightStudy
		fields = ('name', 'selection_ids', 'start_time', 'end_time', 'step_seconds', 'worker_count')

	def validate(self, attributes):
		duration = (attributes['end_time'] - attributes['start_time']).total_seconds()

		if duration <= 0:
			raise serializers.ValidationError({'end_time': 'End time must be after start time.'})

		selection_ids = attributes.pop('selection_ids')

		if len(set(selection_ids)) != len(selection_ids):
			raise serializers.ValidationError({'selection_ids': 'Choose each selection only once.'})

		expected_frames = ceil(duration / attributes['step_seconds']) * len(selection_ids)

		attributes['selections'] = self.pin_selections(selection_ids)
		attributes['expected_frames'] = expected_frames

		return attributes

	def pin_selections(self, selection_ids):
		pinned_by_id = {}

		if self.instance is not None:
			for selection in self.instance.selections:
				pinned_by_id[selection['id']] = selection

		saved_by_id = SunlightSelection.objects.in_bulk(selection_ids)
		selections = []

		for selection_id in selection_ids:
			if selection_id in pinned_by_id:
				selections.append(pinned_by_id[selection_id])
				continue

			if selection_id not in saved_by_id:
				raise serializers.ValidationError({'selection_ids': 'Choose saved selections.'})

			selections.append(pin_selection(saved_by_id[selection_id]))

		return selections


class SunlightStudyCalculateInputSerializer(serializers.ModelSerializer):
	class Meta:
		model = SunlightStudy
		fields = ('worker_count',)


class SunlightStudyInputSerializer(SunlightStudyScheduleInputSerializer):
	dataset_id = serializers.PrimaryKeyRelatedField(source='dataset', queryset=TerrainDataset.objects.filter(status=TerrainDataset.Status.READY))

	class Meta(SunlightStudyScheduleInputSerializer.Meta):
		fields = (*SunlightStudyScheduleInputSerializer.Meta.fields, 'dataset_id')


class SunlightStudyEditInputSerializer(SunlightStudyScheduleInputSerializer):
	def update(self, instance, validated_data):
		selection_ids = {selection['id'] for selection in validated_data['selections']}
		schedule = (validated_data['start_time'], validated_data['end_time'], validated_data['step_seconds'])
		pinned_ids = {selection['id'] for selection in instance.selections}

		unchanged_schedule = schedule == (instance.start_time, instance.end_time, instance.step_seconds)
		validated_data['result_revision'] = instance.result_revision + 1

		if unchanged_schedule and selection_ids == pinned_ids:
			return super().update(instance, validated_data)

		times = set(timestamps(*schedule))
		stale_frame_ids = []

		for frame_id, selection_id, timestamp in instance.frames.values_list('id', 'selection_id', 'timestamp'):
			if selection_id not in selection_ids or timestamp not in times:
				stale_frame_ids.append(frame_id)

		instance.frames.filter(pk__in=stale_frame_ids).delete()
		is_complete = instance.complete_frames().count() == validated_data['expected_frames']
		validated_data['status'] = SunlightStudy.Status.PENDING

		if is_complete:
			validated_data['status'] = SunlightStudy.Status.COMPLETE

		validated_data['progress'] = None
		validated_data['error_message'] = ''
		validated_data['reset_revision'] = validated_data['result_revision']

		study = super().update(instance, validated_data)
		rebuild_combined_visibility(study)

		return study


def pin_selection(selection):
	return {
		'id': selection.pk,
		'name': selection.name,
		'latitude': selection.latitude,
		'longitude': selection.longitude,
		'radius_meters': selection.radius_meters,
	}


class SunlightStudyOutputSerializer(serializers.ModelSerializer):
	start_time = serializers.DateTimeField(default_timezone=UTC)
	end_time = serializers.DateTimeField(default_timezone=UTC)
	created_ts = serializers.DateTimeField(default_timezone=UTC)
	completed_frames = serializers.IntegerField()
	saved_results = serializers.IntegerField()

	class Meta:
		model = SunlightStudy
		fields = (
			'id',
			'name',
			'dataset_id',
			'selections',
			'start_time',
			'end_time',
			'step_seconds',
			'worker_count',
			'expected_frames',
			'completed_frames',
			'saved_results',
			'result_revision',
			'status',
			'progress',
			'error_message',
			'created_ts',
		)
		read_only_fields = fields


class SunlightFrameOutputSerializer(serializers.ModelSerializer):
	timestamp = serializers.DateTimeField(default_timezone=UTC)
	earth_thumbnail = serializers.JSONField(source='cached_earth_result.thumbnail', read_only=True, default=None)

	class Meta:
		model = SunlightFrame
		fields = (
			'id',
			'study_id',
			'selection_id',
			'timestamp',
			'visible_sun_fraction',
			'thumbnail',
			'visible_earth_fraction',
			'earth_thumbnail',
			'earth_center_visible',
			'joint_visible_share',
			'result_revision',
		)
		read_only_fields = fields


class SunlightFrameDetailOutputSerializer(SunlightFrameOutputSerializer):
	result = serializers.JSONField(source='calculation_result', read_only=True)
	earth_result = serializers.JSONField(source='cached_earth_result.result', read_only=True, default=None)

	class Meta(SunlightFrameOutputSerializer.Meta):
		fields = (*SunlightFrameOutputSerializer.Meta.fields, 'result', 'earth_result')
		read_only_fields = fields


class SiteTerrainOutputSerializer(serializers.Serializer):
	selection_id = serializers.IntegerField()
	radius_meters = serializers.FloatField()
	grid_size = serializers.IntegerField()
	spacing_meters = serializers.FloatField()
	reference_radius_meters = serializers.FloatField()
	heights_meters = serializers.ListField(child=serializers.FloatField())


class BodyDirectionsOutputSerializer(serializers.Serializer):
	elevation_degrees = serializers.ListField(child=serializers.FloatField())
	azimuth_degrees = serializers.ListField(child=serializers.FloatField())


class SiteDirectionsOutputSerializer(serializers.Serializer):
	selection_id = serializers.IntegerField()
	sun = BodyDirectionsOutputSerializer()
	earth = BodyDirectionsOutputSerializer()


class SiteHorizonOutputSerializer(HorizonOutputSerializer):
	selection_id = serializers.IntegerField()


class CombinedSampleOutputSerializer(serializers.Serializer):
	latitude = serializers.FloatField()
	longitude = serializers.FloatField()
	visible_seconds = serializers.FloatField()


class CombinedGridOutputSerializer(serializers.Serializer):
	grid_size = serializers.IntegerField()
	radius_meters = serializers.FloatField()
	spacing_meters = serializers.FloatField()
	samples = serializers.ListField(child=CombinedSampleOutputSerializer(allow_null=True))


class CombinedPreviewOutputSerializer(serializers.Serializer):
	frame_id = serializers.IntegerField()
	grid_size = serializers.IntegerField()
	fractions = serializers.ListField(child=serializers.IntegerField(allow_null=True))


class SiteCombinedVisibilityOutputSerializer(serializers.Serializer):
	selection_id = serializers.IntegerField()
	result_revision = serializers.IntegerField()
	reset = serializers.BooleanField()
	total_seconds = serializers.FloatField()
	checked_seconds = serializers.FloatField()
	checked_frames = serializers.IntegerField()
	expected_frames = serializers.IntegerField()
	grid = CombinedGridOutputSerializer(allow_null=True)
	previews = CombinedPreviewOutputSerializer(many=True)


class StudyResultChangesInputSerializer(serializers.Serializer):
	after_revision = serializers.IntegerField(min_value=0, required=False, default=None)
