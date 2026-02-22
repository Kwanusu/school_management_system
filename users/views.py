from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, RegisterSerializer

# Create your views here.
User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing user instances.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        """
        Professional Logic: 
        - Anyone can register (POST).
        - Only logged-in users can see profiles.
        - Only Admins can delete users.
        """
        if self.action == 'create':
            return [permissions.AllowAny()]
        if self.action in ['list', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        # Use a different serializer for registration
        if self.action == 'create':
            return RegisterSerializer
        return UserSerializer

    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Endpoint: GET /api/users/me/
        Used by Redux to fetch current user data using the JWT token.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


