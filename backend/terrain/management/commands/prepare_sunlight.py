from core.management.progress import Progress
from django.core.management.base import BaseCommand, CommandError

from terrain.models.SunlightSelection import SunlightSelection
from terrain.models.SunlightStudy import SunlightStudy
from terrain.models.TerrainDataset import TerrainDataset
from terrain.services.horizon_storage import load_profiles, save_profile
from terrain.services.sunlight_preparation import prepare_selection, restore_selection
from terrain.services.sunlight_processing import SunlightProcessor
from terrain.services.terrain_surface import TerrainAnalysisUnavailable


class Command(BaseCommand):
	help = 'Store reusable terrain samples and horizon profiles for one saved sunlight site.'

	def add_arguments(self, parser):
		parser.add_argument('dataset_id', type=int)
		parser.add_argument('selection_id', type=int)
		parser.add_argument('--workers', type=int, choices=SunlightStudy.WorkerCount.values, default=SunlightStudy.WorkerCount.FOUR)

	def handle(self, **options):
		try:
			dataset = TerrainDataset.objects.get(pk=options['dataset_id'], status=TerrainDataset.Status.READY)
			selection = SunlightSelection.objects.get(pk=options['selection_id'])

			self.stdout.write('Preparing terrain samples')
			preparation = prepare_selection(
				dataset, {'latitude': selection.latitude, 'longitude': selection.longitude, 'radius_meters': selection.radius_meters}
			)
			points, _ = restore_selection(preparation)
			locations = [(point.latitude, point.longitude) for point in points]
			geometry = [point.geometry() for point in points]
			contents = load_profiles(dataset, locations)
			progress = Progress(self.stdout, 'Preparing horizons')
			completed = 0
			progress.update(0, len(points))

			with SunlightProcessor(dataset.pk, locations, workers=options['workers'], geometry=geometry) as processor:
				for index, content in processor.prepare_profiles(contents, build_missing=True):
					if index is None:
						continue

					if content is not None:
						save_profile(dataset, locations[index], content)

					completed += 1
					progress.update(completed, len(points))

			message = f'Prepared site {selection.pk} on dataset {dataset.pk}. Samples and horizons are stored in the database.'
			self.stdout.write(self.style.SUCCESS(message))
		except TerrainDataset.DoesNotExist as error:
			raise CommandError('Choose a ready terrain dataset.') from error
		except SunlightSelection.DoesNotExist as error:
			raise CommandError('Saved sunlight site does not exist.') from error
		except (TerrainAnalysisUnavailable, OSError) as error:
			raise CommandError(str(error)) from error
