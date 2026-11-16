from core.management.progress import Progress
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from terrain.models.SunlightFrame import SunlightFrame
from terrain.models.SunlightStudy import SunlightStudy
from terrain.services.site_combined_visibility import rebuild_combined_visibility
from terrain.services.study_calculation import joint_grid
from terrain.services.terrain_surface import TerrainAnalysisUnavailable


class Command(BaseCommand):
	help = 'Prepare compact overlap grids for one saved plan without recalculating terrain or visibility.'

	def add_arguments(self, parser):
		parser.add_argument('study_id', type=int)

	@transaction.atomic
	def handle(self, **options):
		try:
			study = SunlightStudy.objects.select_for_update().get(pk=options['study_id'])

			if study.status in (SunlightStudy.Status.QUEUED, SunlightStudy.Status.RUNNING, SunlightStudy.Status.STOPPING):
				raise CommandError('Stop the plan before preparing its saved results.')

			study.result_revision += 1
			study.reset_revision = study.result_revision
			study.save(update_fields=('result_revision', 'reset_revision', 'updated_ts'))
			frames = study.frames.select_related('cached_result', 'cached_earth_result')
			frames = frames.defer('result', 'thumbnail', 'cached_result__thumbnail', 'cached_earth_result__thumbnail')
			total_frames = frames.count()
			progress = Progress(self.stdout, 'Preparing saved results')
			frame_batch = []

			for completed_frames, frame in enumerate(frames.iterator(chunk_size=32), start=1):
				frame.joint_grid = None

				if frame.joint_visible_share is not None:
					frame.joint_grid = joint_grid(frame)

				frame.result_revision = study.result_revision
				frame_batch.append(frame)

				if len(frame_batch) == 32:
					SunlightFrame.objects.bulk_update(frame_batch, ('joint_grid', 'result_revision'))
					frame_batch.clear()

				progress.update(completed_frames, total_frames)

			if frame_batch:
				SunlightFrame.objects.bulk_update(frame_batch, ('joint_grid', 'result_revision'))

			rebuild_combined_visibility(study)
			self.stdout.write(self.style.SUCCESS(f'Prepared saved results for plan {study.pk}.'))
		except SunlightStudy.DoesNotExist as error:
			raise CommandError('The saved plan does not exist.') from error
		except (TerrainAnalysisUnavailable, OSError) as error:
			raise CommandError(str(error)) from error
