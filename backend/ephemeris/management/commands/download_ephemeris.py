from core.management.progress import Progress
from core.services.downloads import download_file
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ephemeris.services.kernels import KERNEL_URLS


class Command(BaseCommand):
	help = 'Download the NASA SPICE kernels for Sun and Earth positions in the LOLA lunar frame.'

	def handle(self, **options):
		try:
			for source_url in KERNEL_URLS:
				filename = source_url.rsplit('/', 1)[1]
				progress = Progress(self.stdout, f'Downloading {filename}')

				download_file(source_url, settings.SPICE_ROOT, progress.update)
				self.stdout.write(f'Ready: {filename}')
		except OSError as error:
			raise CommandError(str(error)) from error

		self.stdout.write(self.style.SUCCESS('SPICE ephemeris data ready.'))
