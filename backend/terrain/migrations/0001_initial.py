import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='LunarFeature',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated time')),
                ('usgs_id', models.PositiveIntegerField(unique=True, verbose_name='USGS ID')),
                ('name', models.TextField(db_index=True, verbose_name='Name')),
                ('clean_name', models.TextField(db_index=True, verbose_name='Clean name')),
                ('feature_type', models.TextField(verbose_name='Feature type')),
                ('latitude', models.FloatField(verbose_name='Latitude')),
                ('longitude', models.FloatField(verbose_name='Longitude')),
                ('diameter_km', models.FloatField(blank=True, null=True, verbose_name='Diameter km')),
                ('origin', models.TextField(blank=True, verbose_name='Origin')),
                ('approval_status', models.TextField(verbose_name='Approval status')),
            ],
            options={
                'ordering': ('name', 'usgs_id'),
            },
        ),
        migrations.CreateModel(
            name='SunlightPreparation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated time')),
                ('latitude', models.FloatField(verbose_name='Latitude')),
                ('longitude', models.FloatField(verbose_name='Longitude')),
                ('radius_meters', models.FloatField(verbose_name='Radius meters')),
                ('grid_size', models.PositiveSmallIntegerField(verbose_name='Grid size')),
                ('version', models.PositiveSmallIntegerField(verbose_name='Version')),
                ('samples', models.JSONField(verbose_name='Samples')),
            ],
        ),
        migrations.CreateModel(
            name='SunlightSelection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated time')),
                ('name', models.TextField(verbose_name='Name')),
                ('latitude', models.FloatField(verbose_name='Latitude')),
                ('longitude', models.FloatField(verbose_name='Longitude')),
                ('radius_meters', models.FloatField(blank=True, null=True, verbose_name='Radius meters')),
            ],
            options={
                'ordering': ('name', 'id'),
            },
        ),
        migrations.CreateModel(
            name='SunlightStudy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated time')),
                ('name', models.TextField(verbose_name='Name')),
                ('selections', models.JSONField(verbose_name='Selections')),
                ('start_time', models.DateTimeField(verbose_name='Start time')),
                ('end_time', models.DateTimeField(verbose_name='End time')),
                ('step_seconds', models.PositiveIntegerField(verbose_name='Step seconds')),
                ('worker_count', models.PositiveSmallIntegerField(choices=[(1, '1 worker'), (2, '2 workers'), (4, '4 workers'), (8, '8 workers'), (16, '16 workers')], default=4, verbose_name='Worker count')),
                ('expected_frames', models.PositiveIntegerField(verbose_name='Expected frames')),
                ('status', models.TextField(choices=[('pending', 'Pending'), ('queued', 'Queued'), ('running', 'Running'), ('stopping', 'Stopping'), ('stopped', 'Stopped'), ('failed', 'Failed'), ('complete', 'Complete')], default='pending', verbose_name='Status')),
                ('run_id', models.UUIDField(editable=False, null=True, verbose_name='Run id')),
                ('progress', models.JSONField(blank=True, null=True, verbose_name='Progress')),
                ('error_message', models.TextField(blank=True, verbose_name='Error message')),
                ('result_revision', models.PositiveBigIntegerField(default=0, verbose_name='Result revision')),
                ('reset_revision', models.PositiveBigIntegerField(default=0, verbose_name='Reset revision')),
            ],
            options={
                'ordering': ('-id',),
            },
        ),
        migrations.CreateModel(
            name='TerrainDataset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated time')),
                ('name', models.SlugField(verbose_name='Name')),
                ('status', models.TextField(choices=[('files', 'Legacy files'), ('loading', 'Loading'), ('ready', 'Ready')], db_default='files', default='files', verbose_name='Status')),
                ('storage_key', models.UUIDField(default=uuid.uuid4, unique=True, verbose_name='Storage key')),
                ('storage_format', models.TextField(choices=[('float32', 'Float32'), ('int16-delta-gzip', 'Int16 delta + gzip')], default='float32', verbose_name='Storage format')),
                ('frame', models.TextField(verbose_name='Frame')),
                ('reference_radius', models.FloatField(verbose_name='Reference radius')),
                ('tile_size', models.PositiveSmallIntegerField(verbose_name='Tile size')),
                ('max_level', models.PositiveSmallIntegerField(verbose_name='Max level')),
                ('tile_count', models.PositiveIntegerField(verbose_name='Tile count')),
                ('refinements', models.JSONField(verbose_name='Refinements')),
                ('sources', models.JSONField(verbose_name='Sources')),
            ],
            options={
                'ordering': ('name', '-id'),
            },
        ),
        migrations.CreateModel(
            name='EarthVisibilityResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated time')),
                ('timestamp', models.DateTimeField(verbose_name='Timestamp')),
                ('version', models.PositiveSmallIntegerField(verbose_name='Version')),
                ('ephemeris_signature', models.CharField(max_length=64, verbose_name='Ephemeris signature')),
                ('visible_earth_fraction', models.FloatField(verbose_name='Visible earth fraction')),
                ('earth_center_visible', models.BooleanField(verbose_name='Earth center visible')),
                ('thumbnail', models.JSONField(null=True, verbose_name='Thumbnail')),
                ('result', models.JSONField(verbose_name='Result')),
                ('preparation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='earth_results', to='terrain.sunlightpreparation', verbose_name='Preparation')),
            ],
        ),
        migrations.CreateModel(
            name='SunlightResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated time')),
                ('timestamp', models.DateTimeField(verbose_name='Timestamp')),
                ('version', models.PositiveSmallIntegerField(verbose_name='Version')),
                ('ephemeris_signature', models.CharField(max_length=64, verbose_name='Ephemeris signature')),
                ('visible_sun_fraction', models.FloatField(verbose_name='Visible sun fraction')),
                ('thumbnail', models.JSONField(null=True, verbose_name='Thumbnail')),
                ('result', models.JSONField(verbose_name='Result')),
                ('preparation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='results', to='terrain.sunlightpreparation', verbose_name='Preparation')),
            ],
        ),
        migrations.CreateModel(
            name='SunlightFrame',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated time')),
                ('selection_id', models.PositiveBigIntegerField(verbose_name='Selection id')),
                ('timestamp', models.DateTimeField(verbose_name='Timestamp')),
                ('visible_sun_fraction', models.FloatField(null=True, verbose_name='Visible sun fraction')),
                ('thumbnail', models.JSONField(null=True, verbose_name='Thumbnail')),
                ('result', models.JSONField(null=True, verbose_name='Result')),
                ('visible_earth_fraction', models.FloatField(null=True, verbose_name='Visible earth fraction')),
                ('earth_center_visible', models.BooleanField(null=True, verbose_name='Earth center visible')),
                ('joint_visible_share', models.FloatField(null=True, verbose_name='Joint visible share')),
                ('joint_grid', models.JSONField(null=True, verbose_name='Joint grid')),
                ('result_revision', models.PositiveBigIntegerField(db_index=True, default=0, verbose_name='Result revision')),
                ('cached_earth_result', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='frames', to='terrain.earthvisibilityresult', verbose_name='Cached earth result')),
                ('cached_result', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='frames', to='terrain.sunlightresult', verbose_name='Cached result')),
                ('study', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='frames', to='terrain.sunlightstudy', verbose_name='Study')),
            ],
            options={
                'ordering': ('timestamp', 'selection_id'),
            },
        ),
        migrations.CreateModel(
            name='StudyCombinedVisibility',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated time')),
                ('selection_id', models.PositiveBigIntegerField(verbose_name='Selection id')),
                ('ephemeris_signature', models.CharField(max_length=64, verbose_name='Ephemeris signature')),
                ('visible_seconds', models.JSONField(verbose_name='Visible seconds')),
                ('checked_frames', models.PositiveIntegerField(default=0, verbose_name='Checked frames')),
                ('checked_seconds', models.FloatField(default=0, verbose_name='Checked seconds')),
                ('preparation', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='terrain.sunlightpreparation', verbose_name='Preparation')),
                ('study', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='combined_visibility', to='terrain.sunlightstudy', verbose_name='Study')),
            ],
            options={
                'ordering': ('study_id', 'selection_id'),
            },
        ),
        migrations.AddField(
            model_name='sunlightstudy',
            name='dataset',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sunlight_studies', to='terrain.terraindataset', verbose_name='Dataset'),
        ),
        migrations.AddField(
            model_name='sunlightpreparation',
            name='dataset',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sunlight_preparations', to='terrain.terraindataset', verbose_name='Dataset'),
        ),
        migrations.CreateModel(
            name='SunlightHorizon',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated time')),
                ('latitude', models.FloatField(verbose_name='Latitude')),
                ('longitude', models.FloatField(verbose_name='Longitude')),
                ('version', models.PositiveSmallIntegerField(verbose_name='Version')),
                ('data', models.BinaryField(verbose_name='Data')),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sunlight_horizons', to='terrain.terraindataset', verbose_name='Dataset')),
            ],
        ),
        migrations.CreateModel(
            name='TerrainTile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_ts', models.DateTimeField(auto_now_add=True, verbose_name='Created time')),
                ('updated_ts', models.DateTimeField(auto_now=True, verbose_name='Updated time')),
                ('face', models.PositiveSmallIntegerField(verbose_name='Face')),
                ('level', models.PositiveSmallIntegerField(verbose_name='Level')),
                ('tile_x', models.PositiveIntegerField(verbose_name='Tile x')),
                ('tile_y', models.PositiveIntegerField(verbose_name='Tile y')),
                ('data', models.BinaryField(verbose_name='Data')),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tiles', to='terrain.terraindataset', verbose_name='Dataset')),
            ],
            options={
                'ordering': ('dataset_id', 'face', 'level', 'tile_x', 'tile_y'),
            },
        ),
        migrations.AddConstraint(
            model_name='earthvisibilityresult',
            constraint=models.UniqueConstraint(fields=('preparation', 'timestamp', 'version', 'ephemeris_signature'), name='unique_earth_visibility_result'),
        ),
        migrations.AddConstraint(
            model_name='sunlightresult',
            constraint=models.UniqueConstraint(fields=('preparation', 'timestamp', 'version', 'ephemeris_signature'), name='unique_sunlight_result'),
        ),
        migrations.AddConstraint(
            model_name='sunlightframe',
            constraint=models.UniqueConstraint(fields=('study', 'selection_id', 'timestamp'), name='unique_sunlight_frame'),
        ),
        migrations.AddConstraint(
            model_name='studycombinedvisibility',
            constraint=models.UniqueConstraint(fields=('study', 'selection_id'), name='unique_study_combined_visibility'),
        ),
        migrations.AddConstraint(
            model_name='sunlightpreparation',
            constraint=models.UniqueConstraint(fields=('dataset', 'latitude', 'longitude', 'radius_meters', 'grid_size', 'version'), name='unique_sunlight_preparation'),
        ),
        migrations.AddConstraint(
            model_name='sunlighthorizon',
            constraint=models.UniqueConstraint(fields=('dataset', 'latitude', 'longitude', 'version'), name='unique_sunlight_horizon'),
        ),
        migrations.AddConstraint(
            model_name='terraintile',
            constraint=models.UniqueConstraint(fields=('dataset', 'face', 'level', 'tile_x', 'tile_y'), name='unique_terrain_tile'),
        ),
    ]
