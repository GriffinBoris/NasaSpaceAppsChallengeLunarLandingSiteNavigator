# Lunar Landing Site Navigator

Explore how location and time affect sunlight and Earth visibility on the Moon. Pick a named feature, a past landing site, or any point on a 3D Moon built from NASA elevation data. Check visibility at a UTC time, or run background plans over days or months to compare sites.

Built by Griffin Boris, team **RAC Space**, for the [2026 NASA Space Apps Lunar Landing Site Navigator challenge](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/).

## Slides and walkthrough

[View the presentation (PDF)](Lunar-Landing-Site-Navigator.pdf).

[Watch the app walkthrough on YouTube](https://youtu.be/wNXYeoxe5sA).

## Run with Docker Compose

1. Install Git and Docker with Docker Compose. [Task](https://taskfile.dev/) is optional; [Taskfile.yml](Taskfile.yml) groups the Docker commands into shortcuts. No host Python, Node.js, or Redis installation is required.

2. Clone the repository and enter its directory:

   ```sh
   git clone https://github.com/GriffinBoris/NasaSpaceAppsChallengeLunarLandingSiteNavigator.git
   cd NasaSpaceAppsChallengeLunarLandingSiteNavigator
   ```

3. Start the application. Use either the Task command or its Docker Compose equivalent throughout this guide.

   **Task:**

   ```sh
   task docker:start
   ```

   **Docker Compose:**

   ```sh
   docker compose up --build --detach --wait
   ```

4. Follow [Load data](#load-data) before using a fresh installation. Startup runs database migrations, but does not download terrain, SPICE kernels, or feature names.

Compose starts Django, Vite, Celery, and Redis. The app runs at [localhost:8000](http://localhost:8000). If that port is busy, prefix either startup command with `WEB_PORT=8001` and open [localhost:8001](http://localhost:8001). Optional settings are listed in [.env.example](.env.example).

Task sets your local user and group IDs for mounted files. On macOS or Linux without Task, you can do the same with `LOCAL_UID=$(id -u) LOCAL_GID=$(id -g) docker compose up --build --detach --wait`.

Saved data lives in `backend/db.sqlite3` and `backend/media/`; Redis keeps queued messages in a Docker volume. Stopping the stack preserves this data. Normal shutdown lets an active plan stop at a calculation checkpoint; use **Continue** after restarting. A forced shutdown can leave a plan marked running.

The app has public APIs and shared sites and plans. Anyone who can access an instance can edit them. Compose binds the website and Vite to localhost for local development.

## Load data

Run these steps once on a fresh checkout. Skip completed imports. Run commands from the repository root while the stack is running.

1. Download the NASA/JPL DE421 SPICE kernels used to calculate Sun and Earth positions.

   **Task:**

   ```sh
   task docker:backend:ephemeris:download
   ```

   **Docker Compose:**

   ```sh
   docker compose exec web python manage.py download_ephemeris
   ```

2. Import NASA LOLA terrain. The `128` preset matches the walkthrough and downloads about **2.1 GB**. Allow additional space for the imported database and retained source files.

   **Task:**

   ```sh
   task docker:backend:terrain:128 WORKERS=4
   ```

   **Docker Compose:**

   ```sh
   docker compose exec web python manage.py ingest_terrain 128 --workers 4
   ```

3. Import the USGS/IAU lunar feature names used by search and map labels.

   **Task:**

   ```sh
   task docker:backend:features:load
   ```

   **Docker Compose:**

   ```sh
   docker compose exec web python manage.py import_lunar_features
   ```

4. Open [localhost:8000](http://localhost:8000). Search for a feature such as **Shackleton**, or select a point on the Moon. Use **Calculate** to check the selected UTC time, or save a site and create a **New plan** to study a date range. The checkout does not include the walkthrough's saved sites or plans.

### Terrain options

Choose one preset. Each import includes all of its coarser zoom levels, so lower-resolution imports are not a prerequisite. The importer stores compressed tiles in the database and keeps downloaded sources for reuse. Re-importing terrain creates another dataset version.

| Preset       | LOLA source                            | Source spacing at the equator | Download size     |
| ------------ | -------------------------------------- | ----------------------------- | ----------------- |
| `4`          | Global `LDEM_4`                        | About 7.6 km                  | 2 MB              |
| `16`         | Global `LDEM_16`                       | About 1.9 km                  | 33 MB             |
| `64`         | Global `LDEM_64`                       | About 474 m                   | 531 MB            |
| `128`        | Global `LDEM_128`                      | About 237 m                   | 2.1 GB            |
| `256`        | Four global `LDEM_256` source tiles    | About 118 m                   | 8.5 GB            |
| `512`        | Sixteen global `LDEM_512` source tiles | About 59 m                    | 34 GB             |
| `south-pole` | `LDEM_16` plus south-pole GeoTIFF      | Global 1.9 km; polar 80 m     | 33 MB plus 189 MB |

For a small first download, choose `4` or `16`. For the highest supported global resolution, choose `512`. Source spacing does not guarantee rendered detail or calculation accuracy.

Imports use two workers by default and support two to eight. For example, import `512` with eight workers using either command:

**Task:**

```sh
task docker:backend:terrain:512 WORKERS=8
```

**Docker Compose:**

```sh
docker compose exec web python manage.py ingest_terrain 512 --workers 8
```

## Data, assumptions, and credits

NASA LRO's Lunar Orbiter Laser Altimeter (LOLA) supplies the elevation data for the 3D surface and terrain-obstruction calculations. NASA/JPL SPICE supplies Sun and Earth positions from a lunar surface observer. JPL Horizons was used to check Earth's calculated direction; it does not validate the terrain shadows. The USGS/IAU catalog supplies lunar feature names and locations.

Results depend on terrain resolution and spatial and time sampling. Earth visibility measures geometric line of sight, without a ground-station or radio-link model. Solar output is an illustrative instantaneous estimate using fixed reference sunlight, panel area, efficiency, and incidence angle. It excludes eclipses, battery storage, and hardware losses. This prototype has not been validated for landing safety.

AI assisted with development, debugging, data integration, calculations, and project documentation. See [AI use](AI_USE.md) for details.

### Sources and acknowledgments

| Source                                                                                                                                                                                                                  | Use                                                                                                                                                                                                                                                                 |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [NASA LRO LOLA global elevation products](https://imbrium.mit.edu/DATA/LOLA_GDR/CYLINDRICAL/IMG/)                                                                                                                       | Terrain heights for the Moon viewer and obstruction calculations.                                                                                                                                                                                                   |
| [NASA/JPL NAIF SPICE](https://naif.jpl.nasa.gov/naif/)                                                                                                                                                                  | Sun and Earth positions, lunar orientation, reference frames, radii, and time conversion.                                                                                                                                                                           |
| [JPL Horizons API](https://ssd-api.jpl.nasa.gov/doc/horizons.html) and [manual](https://ssd.jpl.nasa.gov/horizons/manual.html)                                                                                          | Reference checks for Earth's azimuth and elevation. Runtime positions come from SPICE.                                                                                                                                                                              |
| [USGS/IAU Moon nomenclature](https://planetarynames.wr.usgs.gov/Page/MOON/target) and [center-point KMZ](https://asc-planetarynames-data.s3.us-west-2.amazonaws.com/MOON_nomenclature_center_pts.kmz)                   | Feature names, coordinates, approximate sizes, and source links.                                                                                                                                                                                                    |
| [Artificial objects on the Moon](https://en.wikipedia.org/wiki/List_of_artificial_objects_on_the_Moon)                                                                                                                  | Featured landing-site coordinates, with supporting NASA references for [Odysseus](https://www.nasa.gov/missions/lro/nasas-lro-images-intuitive-machines-odysseus-lander/) and [Chang'e 4](https://nssdc.gsfc.nasa.gov/planetary/lunar/lunar_artifact_impacts.html). |
| [NASA solar irradiance](https://earth.gsfc.nasa.gov/climate/projects/solar-irradiance/science) and [PVsyst cosine effect](https://www.pvsyst.com/help/project-design/shadings/backtracking-strategy/cosine-effect.html) | Fixed 1,361 W/m² reference sunlight and the panel-incidence relationship.                                                                                                                                                                                           |
| [LEAG illumination-modeling abstract](https://www.hou.usra.edu/meetings/leag2015/pdf/2041.pdf)                                                                                                                          | Background for separating terrain-horizon preparation from time evaluation; not validation of this implementation.                                                                                                                                                  |
| [Inter](https://fontsource.org/fonts/inter), [Archivo](https://fontsource.org/fonts/archivo), and [Lucide](https://lucide.dev)                                                                                          | Interface fonts and icons.                                                                                                                                                                                                                                          |

SPICE kernels: [naif0012.tls](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls), [de421.bsp](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/a_old_versions/de421.bsp), [moon_080317.tf](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/fk/satellites/moon_080317.tf), [moon_pa_de421_1900-2050.bpc](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/moon_pa_de421_1900-2050.bpc), and [pck00011.tpc](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc). Surface-observer geometry follows [SPICE's observer-position method](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/spkcpo_c.html).

The optional south-pole preset uses [NASA Goddard's LOLA south-pole product](https://pgda.gsfc.nasa.gov/products/90), specifically [LDEM_80S_80MPP_ADJ.TIF](https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_80MPP_ADJ.TIF).

Software dependencies are listed in [backend/pyproject.toml](backend/pyproject.toml) and [frontend/package.json](frontend/package.json), with resolved versions in [uv.lock](uv.lock) and [frontend/package-lock.json](frontend/package-lock.json). The walkthrough uses original app footage captured with Playwright and Chrome and edited with FFmpeg.

## Development

1. Run the full checks after starting Docker.

   **Task:**

   ```sh
   task docker:check
   ```

   **Docker Compose:**

   ```sh
   docker compose up --build --detach --wait
   docker compose exec -T --workdir /app web ruff check --no-cache backend --extend-exclude backend/media,backend/static
   docker compose exec -T --workdir /app web ruff format --check --no-cache backend --extend-exclude backend/media,backend/static
   docker compose exec -T web python manage.py check
   docker compose exec -T web python manage.py makemigrations --check --dry-run
   docker compose exec -T --workdir /app --env DJANGO_SETTINGS_MODULE=core.settings.dev_pytest web python -m pytest -p no:cacheprovider
   docker compose run --build --rm --no-deps frontend npm run lint
   docker compose run --build --rm --no-deps frontend npm test
   ```

   Startup builds and type-checks the frontend. The remaining commands check Python lint and formatting, Django configuration, migration drift, backend tests, frontend lint, and frontend tests. Backend tests use a temporary database and an in-memory broker.

2. Use these commands for common tasks:

   | Action                   | Task                                     | Docker Compose                                                                                                                         |
   | ------------------------ | ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
   | Stop and keep data       | `task docker:down`                       | `docker compose down`                                                                                                                  |
   | Follow calculation logs  | `task docker:logs SERVICE=celery`        | `docker compose logs --follow celery`                                                                                                  |
   | Open a Django shell      | `task docker:shell`                      | `docker compose exec web python manage.py shell`                                                                                       |
   | Create an admin account  | `task docker:backend:db:createsuperuser` | `docker compose exec web python manage.py createsuperuser`                                                                             |
   | Create migrations        | `task docker:backend:db:makemigrations`  | `docker compose exec -T web python manage.py makemigrations`                                                                           |
   | Apply migrations         | `task docker:backend:db:migrate`         | `docker compose exec -T web python manage.py migrate`                                                                                  |
   | Run backend tests        | `task docker:backend:test`               | `docker compose exec -T --workdir /app --env DJANGO_SETTINGS_MODULE=core.settings.dev_pytest web python -m pytest -p no:cacheprovider` |
   | Run frontend type checks | `task docker:frontend:type-check`        | `docker compose run --build --rm --no-deps frontend npm run type-check`                                                                |
   | Run frontend tests       | `task docker:frontend:test`              | `docker compose run --build --rm --no-deps frontend npm test`                                                                          |

3. Keep using [localhost:8000](http://localhost:8000) while developing. Django reloads Python changes, and Vite serves frontend updates on port 5173. Restart Celery with `docker compose restart celery` after worker-code changes. Restart the frontend service after frontend dependency changes; rebuild with either startup command after backend dependency changes. Django admin is at [localhost:8000/admin/](http://localhost:8000/admin/).

The terrain schema has one regenerated initial migration. Existing databases must have all former migrations through `0015_allow_sixteen_plan_workers` applied before switching to this baseline. Fully migrated databases retain their data. For an older database, back it up and finish its migrations with the previous code before updating. Fresh checkouts migrate automatically on startup.
