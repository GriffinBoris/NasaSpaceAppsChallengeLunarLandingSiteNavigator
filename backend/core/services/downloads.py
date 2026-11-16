import ssl
from urllib.request import urlopen

import certifi


def download_file(source_url, download_directory, on_progress):
	source_path = download_directory / source_url.rsplit('/', 1)[1]
	download_directory.mkdir(parents=True, exist_ok=True)

	if source_path.is_file():
		return source_path

	partial_path = source_path.with_suffix(source_path.suffix + '.part')
	ssl_context = ssl.create_default_context(cafile=certifi.where())

	try:
		with urlopen(source_url, timeout=60, context=ssl_context) as response, partial_path.open('wb') as destination_file:
			total_bytes = int(response.headers.get('Content-Length', 0))
			downloaded_bytes = 0

			on_progress(0, total_bytes)

			while True:
				download_chunk = response.read(1024 * 1024)

				if not download_chunk:
					break

				destination_file.write(download_chunk)
				downloaded_bytes += len(download_chunk)

				on_progress(downloaded_bytes, total_bytes)

			if total_bytes and downloaded_bytes != total_bytes:
				raise OSError(f'Incomplete download: {source_path.name}.')

		partial_path.replace(source_path)
	finally:
		partial_path.unlink(missing_ok=True)

	return source_path
