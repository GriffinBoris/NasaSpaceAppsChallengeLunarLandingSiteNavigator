from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def index(request):
	if settings.FRONTEND_DEV_URL:
		return render(request, 'core/index_dev.html', {'frontend_dev_url': settings.FRONTEND_DEV_URL})

	if not (settings.FRONTEND_DIST_DIR / 'index.html').is_file():
		raise Http404('Frontend not built. Run task docker:start.')

	return render(request, 'index.html')
