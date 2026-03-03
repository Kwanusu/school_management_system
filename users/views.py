from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer, RegisterSerializer
from core.models import Course, TaskSubmission
from core.serializers import CourseSerializer, TaskSubmissionSerializer
from rest_framework.exceptions import PermissionDenied

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action in ['register', 'create', 'login']:
            return [permissions.AllowAny()]
        if self.action in ['list', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """
        Endpoint: /api/users/me/
        Returns the logged-in user's details for Redux initialization.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    def get_serializer_class(self):
        if self.action == 'create':
            return RegisterSerializer
        return UserSerializer
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register(self, request):
        """
        Endpoint: POST /api/auth/register/
        Explicitly defined to match React frontend calls.
        """
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                "user": UserSerializer(user).data,
                "token": str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def login(self, request):
        """
        Endpoint: POST /api/users/login/
        """
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)

        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'token': str(refresh.access_token),
                'user': UserSerializer(user).data
            }, status=status.HTTP_200_OK)
        
        return Response({'error': 'Invalid Credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class InstructorCourseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Professional Logic: Only return courses where the current user is the teacher
        return Course.objects.filter(teacher=self.request.user)
    
    def perform_update(self, serializer):
        # Ensure the person grading is the teacher assigned to the course
        submission = self.get_object()
        if submission.task.course.teacher != self.request.user:
            raise PermissionDenied("You can only grade your own students.")
        serializer.save()
        
class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # This automatically sets the teacher to the logged-in user
        # 'self.request.user' is populated by DRF's authentication
        serializer.save(teacher=self.request.user)
        

class SubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Complex Query: Get submissions for all courses taught by this user
        # This uses the 'double underscore' notation to reach across the relationship
        return TaskSubmission.objects.filter(task__course__teacher=self.request.user)    

   