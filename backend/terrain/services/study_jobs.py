import logging
from contextlib import closing
from functools import partial
from uuid import uuid4

from django.db import transaction
from django.db.models import Case, F, Value, When
from django.utils import timezone
from ephemeris.services.positions import EphemerisTimeError, EphemerisUnavailable
from kombu.exceptions import OperationalError

from terrain.models.SunlightStudy import SunlightStudy
from terrain.services.study_calculation import iter_study
from terrain.services.terrain_surface import TerrainAnalysisUnavailable
from terrain.tasks import calculate_study

logger = logging.getLogger(__name__)
ACTIVE_STATUSES = (SunlightStudy.Status.QUEUED, SunlightStudy.Status.RUNNING, SunlightStudy.Status.STOPPING)


def publish_study(study_id, run_id):
	try:
		calculate_study.apply_async(args=[study_id, str(run_id)], task_id=str(run_id))
	except OperationalError:
		logger.exception('Unable to queue sunlight study %s', study_id)
		SunlightStudy.objects.filter(pk=study_id, run_id=run_id, status=SunlightStudy.Status.QUEUED).update(
			status=SunlightStudy.Status.FAILED,
			error_message='Unable to queue this plan. Check that Redis is running, then try again.',
			updated_ts=timezone.now(),
		)
		raise


def queue_study(study_id, worker_count=None):
	run_id = uuid4()

	with transaction.atomic():
		claimed = SunlightStudy.objects.filter(
			pk=study_id, status__in=[SunlightStudy.Status.PENDING, SunlightStudy.Status.STOPPED, SunlightStudy.Status.FAILED]
		).update(
			status=SunlightStudy.Status.QUEUED,
			run_id=run_id,
			worker_count=F('worker_count') if worker_count is None else worker_count,
			progress={'completed': 0, 'total': 0, 'percentage': 0, 'stage': 'Queued'},
			error_message='',
			updated_ts=timezone.now(),
		)

		if not claimed:
			return False

		transaction.on_commit(partial(publish_study, study_id, run_id))

	return True


@transaction.atomic
def delete_study(study_id):
	claimed = SunlightStudy.objects.filter(pk=study_id).exclude(status__in=ACTIVE_STATUSES).update(updated_ts=timezone.now())

	if not claimed:
		return False

	SunlightStudy.objects.filter(pk=study_id).delete()

	return True


def stop_study(study_id, run_id):
	SunlightStudy.objects.filter(pk=study_id, run_id=run_id, status__in=[SunlightStudy.Status.QUEUED, SunlightStudy.Status.RUNNING]).update(
		status=Case(
			When(status=SunlightStudy.Status.QUEUED, then=Value(SunlightStudy.Status.STOPPED)),
			default=Value(SunlightStudy.Status.STOPPING),
		),
		updated_ts=timezone.now(),
	)


def process_study(study_id, run_id):
	job = SunlightStudy.objects.filter(pk=study_id, run_id=run_id)

	if not job.filter(status=SunlightStudy.Status.QUEUED).update(status=SunlightStudy.Status.RUNNING, updated_ts=timezone.now()):
		return

	study = job.select_related('dataset').get()

	try:
		with closing(iter_study(study)) as events:
			for event in events:
				if event['type'] == 'progress':
					updated = job.filter(status=SunlightStudy.Status.RUNNING).update(progress=event['progress'], updated_ts=timezone.now())

					if not updated:
						return

		job.filter(status=SunlightStudy.Status.RUNNING).update(status=SunlightStudy.Status.COMPLETE, updated_ts=timezone.now())
	except (EphemerisTimeError, EphemerisUnavailable, TerrainAnalysisUnavailable) as error:
		logger.warning('Sunlight study %s unavailable', study_id, exc_info=True)
		job.filter(status=SunlightStudy.Status.RUNNING).update(
			status=SunlightStudy.Status.FAILED, error_message=str(error), updated_ts=timezone.now()
		)
		raise
	except Exception:
		logger.exception('Sunlight study %s failed', study_id)
		job.filter(status=SunlightStudy.Status.RUNNING).update(
			status=SunlightStudy.Status.FAILED,
			error_message='Unable to finish this plan. Completed results are saved. You can retry.',
			updated_ts=timezone.now(),
		)
		raise
	finally:
		job.filter(status=SunlightStudy.Status.STOPPING).update(status=SunlightStudy.Status.STOPPED, updated_ts=timezone.now())
