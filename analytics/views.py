from rest_framework import viewsets, permissions
from .models import SystemLog
from .serializers import SystemLogSerializer

class SystemLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Automated logging view: Provides a history of grade changes and course updates.
    """
    queryset = SystemLog.objects.all().order_by('-timestamp')
    serializer_class = SystemLogSerializer
    permission_classes = [permissions.IsAdminUser]
