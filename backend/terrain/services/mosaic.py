from math import isclose
from xml.etree.ElementTree import Element, ElementTree, SubElement

import rasterio

from terrain.services.tile_grid import REFERENCE_RADIUS


def build_mosaic(source_paths, destination_path):
	sources = []

	for source_path in source_paths:
		with rasterio.open(source_path) as dataset:
			offset = dataset.offsets[0]

			if dataset.driver == 'PDS':
				if offset != REFERENCE_RADIUS:
					raise ValueError('The PDS reference radius must be 1737400 meters.')

				offset = 0

			sources.append(
				{
					'path': source_path.resolve(),
					'crs': dataset.crs,
					'transform': dataset.transform,
					'width': dataset.width,
					'height': dataset.height,
					'scale': dataset.scales[0],
					'offset': offset,
					'dtype': dataset.dtypes[0],
				}
			)

	first_source = sources[0]
	pixel_width = first_source['transform'].a
	pixel_height = -first_source['transform'].e

	if first_source['crs'] is None or pixel_width <= 0 or pixel_height <= 0:
		raise ValueError('Global source tiles must use a north-up lunar coordinate system.')

	left = min(source['transform'].c for source in sources)
	top = max(source['transform'].f for source in sources)
	width = 0
	height = 0

	for source in sources:
		transform = source['transform']

		if (
			source['crs'] != first_source['crs']
			or source['dtype'] != 'int16'
			or source['scale'] != first_source['scale']
			or source['offset'] != first_source['offset']
			or not isclose(transform.a, pixel_width)
			or not isclose(-transform.e, pixel_height)
			or transform.b != 0
			or transform.d != 0
		):
			raise ValueError('Global source tiles must use the same north-up Int16 grid and height scale.')

		source['column'] = round((transform.c - left) / pixel_width)
		source['row'] = round((top - transform.f) / pixel_height)
		width = max(width, source['column'] + source['width'])
		height = max(height, source['row'] + source['height'])

	if sum(source['width'] * source['height'] for source in sources) != width * height:
		raise ValueError('Global source tiles must cover the complete mosaic.')

	mosaic = Element('VRTDataset', rasterXSize=str(width), rasterYSize=str(height))
	SubElement(mosaic, 'SRS').text = first_source['crs'].to_wkt()
	SubElement(mosaic, 'GeoTransform').text = f'{left}, {pixel_width}, 0, {top}, 0, {-pixel_height}'
	band = SubElement(mosaic, 'VRTRasterBand', dataType='Int16', band='1')
	SubElement(band, 'NoDataValue').text = '-32768'
	SubElement(band, 'Scale').text = str(first_source['scale'])
	SubElement(band, 'Offset').text = str(first_source['offset'])

	for source in sources:
		simple_source = SubElement(band, 'SimpleSource')
		SubElement(simple_source, 'SourceFilename', relativeToVRT='0').text = str(source['path'])
		SubElement(simple_source, 'SourceBand').text = '1'
		SubElement(simple_source, 'SrcRect', xOff='0', yOff='0', xSize=str(source['width']), ySize=str(source['height']))
		SubElement(
			simple_source,
			'DstRect',
			xOff=str(source['column']),
			yOff=str(source['row']),
			xSize=str(source['width']),
			ySize=str(source['height']),
		)

	partial_path = destination_path.with_suffix('.vrt.part')

	try:
		ElementTree(mosaic).write(partial_path, encoding='utf-8', xml_declaration=True)
		partial_path.replace(destination_path)
	finally:
		partial_path.unlink(missing_ok=True)

	return destination_path
