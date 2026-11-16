from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView


@method_decorator(csrf_protect, name='dispatch')
class ProjectBaseAPIView(APIView):
	authentication_classes = ()
	permission_classes = (AllowAny,)
