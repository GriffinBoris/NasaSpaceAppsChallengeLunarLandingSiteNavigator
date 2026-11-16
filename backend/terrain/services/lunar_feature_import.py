from math import isfinite
from urllib.parse import urlsplit
from xml.etree import ElementTree
from zipfile import ZipFile

from django.db import transaction

from terrain.models.LunarFeature import LunarFeature

CATALOG_URL = 'https://asc-planetarynames-data.s3.us-west-2.amazonaws.com/MOON_nomenclature_center_pts.kmz'
KML_FILENAME = 'MOON_nomenclature_center_pts.kml'
NAMESPACES = {'kml': 'http://www.opengis.net/kml/2.2'}


def read_features(source_path):
	with ZipFile(source_path) as archive, archive.open(KML_FILENAME) as source_file:
		document = ElementTree.parse(source_file)

	features = []
	feature_ids = set()

	for placemark in document.findall('.//kml:Placemark', NAMESPACES):
		fields = {field.attrib['name']: field.text or '' for field in placemark.findall('.//kml:SimpleData', NAMESPACES)}
		usgs_id = int(urlsplit(fields['link']).path.rsplit('/', 1)[1])
		name = placemark.findtext('kml:name', namespaces=NAMESPACES)
		latitude = float(fields['center_lat'])
		longitude = float(fields['center_lon'])
		diameter_text = fields.get('diameter', '')
		diameter = float(diameter_text) if diameter_text else None

		if usgs_id <= 0 or usgs_id in feature_ids or not name:
			raise ValueError(f'Invalid or duplicate lunar feature: {usgs_id}.')

		if not isfinite(latitude) or not -90 <= latitude <= 90 or not isfinite(longitude) or not -180 <= longitude <= 360:
			raise ValueError(f'Invalid coordinates for {name}.')

		if diameter is not None and (not isfinite(diameter) or diameter < 0):
			raise ValueError(f'Invalid diameter for {name}.')

		longitude = (longitude + 180) % 360 - 180
		feature_ids.add(usgs_id)
		features.append(
			LunarFeature(
				usgs_id=usgs_id,
				name=name,
				clean_name=fields['clean_name'],
				feature_type=fields['type'],
				latitude=latitude,
				longitude=longitude,
				diameter_km=diameter,
				origin=fields.get('origin', ''),
				approval_status=fields['approval'],
			)
		)

	if not features:
		raise ValueError('The lunar feature catalog is empty.')

	return features


def import_lunar_features(source_path, on_progress):
	features = read_features(source_path)
	total = len(features)
	on_progress(0, total)

	with transaction.atomic():
		for offset in range(0, total, 500):
			batch = features[offset : offset + 500]
			LunarFeature.objects.bulk_create(
				batch,
				update_conflicts=True,
				unique_fields=['usgs_id'],
				update_fields=[
					'name',
					'clean_name',
					'feature_type',
					'latitude',
					'longitude',
					'diameter_km',
					'origin',
					'approval_status',
					'updated_ts',
				],
			)
			on_progress(offset + len(batch), total)

	return total
