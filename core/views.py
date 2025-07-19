
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import logging

from .models import *
from .serializers import *
from .utils.notifications import create_notification
from django.http import HttpResponse

def test_view(request):
    return HttpResponse("<h1>This is a test - if you see this, views are working</h1>")
logger = logging.getLogger(__name__)


# API ViewSets
class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users with advanced filtering and permissions
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user_type', 'is_active', 'email_verified']
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['created_at', 'last_login']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]

        return [permission() for permission in permission_classes]

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({'status': 'User activated'})

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({'status': 'User deactivated'})


class SchoolViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing schools
    """
    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['school_type', 'ownership_type', 'state']
    search_fields = ['name', 'city', 'state']

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'proprietor':
            return School.objects.filter(proprietorprofile__user=user)
        elif user.user_type == 'principal':
            return School.objects.filter(principalprofile__user=user)
        return School.objects.all()


class ClassViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing classes
    """
    queryset = Class.objects.all()
    serializer_class = ClassSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['school', 'level']
    search_fields = ['name', 'level']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ['proprietor', 'principal']:
            # Get schools associated with user
            if hasattr(user, 'proprietorprofile'):
                schools = user.proprietorprofile.schools.all()
            elif hasattr(user, 'principalprofile'):
                schools = [user.principalprofile.school]
            else:
                schools = []
            return Class.objects.filter(school__in=schools)
        elif user.user_type == 'teacher':
            return Class.objects.filter(teacherprofile__user=user)
        return Class.objects.all()


class SubjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing subjects
    """
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['school', 'code']
    search_fields = ['name', 'code']


class TeacherProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing teacher profiles
    """
    queryset = TeacherProfile.objects.all()
    serializer_class = TeacherProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['school', 'specialization']
    search_fields = ['user__first_name', 'user__last_name', 'specialization']

    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        teacher = self.get_object()
        enrollments = Enrollment.objects.filter(
            class_enrolled__teacherprofile=teacher
        ).select_related('student__user')

        students = [enrollment.student for enrollment in enrollments]
        serializer = StudentProfileSerializer(students, many=True)
        return Response(serializer.data)


class StudentProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing student profiles
    """
    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['school', 'admission_year']
    search_fields = ['user__first_name', 'user__last_name', 'student_id']

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'student':
            return StudentProfile.objects.filter(user=user)
        elif user.user_type == 'parent':
            return StudentProfile.objects.filter(parentprofile__user=user)
        return StudentProfile.objects.all()

    @action(detail=True, methods=['get'])
    def grades(self, request, pk=None):
        student = self.get_object()
        grades = Grade.objects.filter(student=student).select_related('subject')
        serializer = GradeSerializer(grades, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def attendance(self, request, pk=None):
        student = self.get_object()
        attendance = Attendance.objects.filter(student=student)
        serializer = AttendanceSerializer(attendance, many=True)
        return Response(serializer.data)


class ParentProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing parent profiles
    """
    queryset = ParentProfile.objects.all()
    serializer_class = ParentProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['user__first_name', 'user__last_name']

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'parent':
            return ParentProfile.objects.filter(user=user)
        return ParentProfile.objects.all()


class PrincipalProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing principal profiles
    """
    queryset = PrincipalProfile.objects.all()
    serializer_class = PrincipalProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['user__first_name', 'user__last_name']


class EnrollmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing enrollments
    """
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['class_enrolled', 'enrollment_date', 'is_active']
    search_fields = ['student__user__first_name', 'student__user__last_name']

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'student':
            return Enrollment.objects.filter(student__user=user)
        elif user.user_type == 'parent':
            return Enrollment.objects.filter(student__parentprofile__user=user)
        return Enrollment.objects.all()


class AttendanceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing attendance
    """
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['student', 'date', 'status']
    search_fields = ['student__user__first_name', 'student__user__last_name']

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'student':
            return Attendance.objects.filter(student__user=user)
        elif user.user_type == 'teacher':
            return Attendance.objects.filter(
                student__enrollment__class_enrolled__teacherprofile__user=user
            )
        return Attendance.objects.all()

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Bulk create attendance records"""
        serializer = AttendanceSerializer(data=request.data, many=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GradeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing grades
    """
    queryset = Grade.objects.all()
    serializer_class = GradeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['student', 'subject', 'grade_type']
    search_fields = ['student__user__first_name', 'student__user__last_name']

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'student':
            return Grade.objects.filter(student__user=user)
        elif user.user_type == 'parent':
            return Grade.objects.filter(student__parentprofile__user=user)
        elif user.user_type == 'teacher':
            return Grade.objects.filter(teacher__user=user)
        return Grade.objects.all()


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages
    """
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_read', 'created_at']
    search_fields = ['subject', 'content']

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(
            Q(sender=user) | Q(recipient=user)
        ).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        message = self.get_object()
        if message.recipient == request.user:
            message.is_read = True
            message.read_at = timezone.now()
            message.save()
            return Response({'status': 'Message marked as read'})
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)


class AnnouncementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing announcements
    """
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['target_audience', 'priority', 'is_active']
    search_fields = ['title', 'content']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        return Announcement.objects.filter(
            Q(target_audience='all') | Q(target_audience=user.user_type),
            is_active=True
        )


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notifications
    """
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_read', 'notification_type']
    search_fields = ['title', 'message']
    ordering = ['-created_at']

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        return Response({'status': 'Notification marked as read'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        Notification.objects.filter(
            recipient=request.user, 
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        return Response({'status': 'All notifications marked as read'})


class PostViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing social posts
    """
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['post_type', 'visibility']
    search_fields = ['content']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        return Post.objects.filter(
            Q(visibility='public') | 
            Q(author=user) |
            Q(visibility='friends', author__in=user.friends.all())
        )

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        post = self.get_object()
        if request.user in post.likes.all():
            post.likes.remove(request.user)
            liked = False
        else:
            post.likes.add(request.user)
            liked = True

        return Response({
            'liked': liked,
            'likes_count': post.likes.count()
        })


class CommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing comments
    """
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['post']
    ordering = ['created_at']

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class ConnectionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user connections
    """
    queryset = Connection.objects.all()
    serializer_class = ConnectionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']

    def get_queryset(self):
        user = self.request.user
        return Connection.objects.filter(
            Q(from_user=user) | Q(to_user=user)
        )

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        connection = self.get_object()
        if connection.to_user == request.user:
            connection.status = 'accepted'
            connection.save()
            return Response({'status': 'Connection accepted'})
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        connection = self.get_object()
        if connection.to_user == request.user:
            connection.status = 'rejected'
            connection.save()
            return Response({'status': 'Connection rejected'})
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)


class TeacherGroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing teacher groups
    """
    queryset = TeacherGroup.objects.all()
    serializer_class = TeacherGroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'teacher':
            return TeacherGroup.objects.filter(members__user=user)
        return TeacherGroup.objects.all()


# Template Views
def home(request):
    """
    Landing page view - accessible to everyone
    """
    # Get some basic statistics for the landing page
    stats = {
        'total_schools': School.objects.filter(is_active=True).count(),
        'total_students': User.objects.filter(user_type='student').count(),
        'total_teachers': User.objects.filter(user_type='teacher').count(),
    }
    
    # Get recent announcements for public display
    recent_announcements = Announcement.objects.filter(
        target_audience='all',
        is_published=True
    ).order_by('-created_at')[:3]
    
    context = {
        'title': 'EMSU - Educational Management System',
        'description': 'Comprehensive educational management platform',
        'stats': stats,
        'recent_announcements': recent_announcements,
        'is_landing_page': True
    }
    return render(request, 'core/home.html', context)


@login_required
def dashboard(request):
    """
    Dashboard view based on user type
    """
    user = request.user
    context = {'user': user}

    try:
        if user.user_type == 'student':
            student_profile = user.studentprofile
            recent_grades = Grade.objects.filter(student=student_profile).order_by('-created_at')[:5]
            attendance_stats = Attendance.objects.filter(
                student=student_profile
            ).aggregate(
                total=Count('id'),
                present=Count('id', filter=Q(status='present'))
            )
            
            # Calculate attendance percentage
            attendance_rate = 0
            if attendance_stats['total'] > 0:
                attendance_rate = (attendance_stats['present'] / attendance_stats['total']) * 100

            context.update({
                'student_profile': student_profile,
                'recent_grades': recent_grades,
                'attendance_stats': attendance_stats,
                'attendance_rate': round(attendance_rate, 1)
            })
            return render(request, 'core/dashboard_student.html', context)

        elif user.user_type == 'teacher':
            teacher_profile = user.teacherprofile
            my_classes = Class.objects.filter(teacherprofile=teacher_profile)
            total_students = StudentProfile.objects.filter(
                enrollment__class_enrolled__in=my_classes
            ).distinct().count()
            
            context.update({
                'teacher_profile': teacher_profile,
                'my_classes': my_classes,
                'total_students': total_students
            })
            return render(request, 'core/dashboard_teacher.html', context)

        elif user.user_type == 'parent':
            parent_profile = user.parentprofile
            children = parent_profile.students.all()
            context.update({
                'parent_profile': parent_profile,
                'children': children
            })
            return render(request, 'core/dashboard_parent.html', context)

        elif user.user_type == 'principal':
            principal_profile = user.principalprofile
            school = principal_profile.school
            total_students = StudentProfile.objects.filter(school=school).count()
            total_teachers = TeacherProfile.objects.filter(school=school).count()
            
            context.update({
                'principal_profile': principal_profile,
                'school': school,
                'total_students': total_students,
                'total_teachers': total_teachers
            })
            return render(request, 'core/dashboard_principal.html', context)

    except Exception as e:
        logger.error(f"Dashboard error for user {user.email}: {str(e)}")
        messages.error(request, 'Unable to load dashboard. Please complete your profile setup.')

    # Fallback to home if no specific dashboard
    return redirect('home')


def login_view(request):
    """
    Login page view
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        if email and password:
            user = authenticate(request, email=email, password=password)
            if user:
                login(request, user)
                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid email or password')
        else:
            messages.error(request, 'Please enter both email and password')

    return render(request, 'core/login.html')


def register_view(request):
    """
    Registration page view
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    # Get all schools for the registration form
    schools = School.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST':
        try:
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            password = request.POST.get('password')
            user_type = request.POST.get('user_type')
            school_id = request.POST.get('school')
            
            # Basic validation
            if not all([first_name, last_name, email, password, user_type]):
                messages.error(request, 'All fields are required')
                return render(request, 'core/register.html', {'schools': schools})
            
            # Check if user already exists
            if User.objects.filter(email=email).exists():
                messages.error(request, 'A user with this email already exists')
                return render(request, 'core/register.html', {'schools': schools})
            
            # Create the user
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                user_type=user_type
            )
            
            # Create profile based on user type
            school = None
            if school_id:
                school = get_object_or_404(School, id=school_id)
            
            if user_type == 'student' and school:
                StudentProfile.objects.create(
                    user=user,
                    school=school,
                    student_id=f"STU{user.id.hex[:8].upper()}"
                )
            elif user_type == 'teacher' and school:
                TeacherProfile.objects.create(
                    user=user,
                    school=school,
                    employee_id=f"TCH{user.id.hex[:8].upper()}"
                )
            elif user_type == 'parent':
                ParentProfile.objects.create(user=user)
            elif user_type == 'principal' and school:
                PrincipalProfile.objects.create(
                    user=user,
                    school=school
                )
            
            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('login')
            
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            messages.error(request, 'Registration failed. Please try again.')
    
    context = {
        'schools': schools,
        'user_types': User.USER_TYPES
    }
    return render(request, 'core/register.html', context)


@login_required
def profile(request):
    """
    User profile view
    """
    context = {'user': request.user}
    return render(request, 'core/profile.html', context)


# API Views
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_stats(request):
    """
    API endpoint for dashboard statistics
    """
    user = request.user
    stats = {}

    try:
        if user.user_type == 'student':
            student = user.studentprofile
            stats = {
                'total_subjects': student.enrollment_set.count(),
                'average_grade': Grade.objects.filter(student=student).aggregate(
                    avg=Avg('score')
                )['avg'] or 0,
                'attendance_rate': Attendance.objects.filter(
                    student=student,
                    status='present'
                ).count() / max(Attendance.objects.filter(student=student).count(), 1) * 100
            }
        elif user.user_type == 'teacher':
            teacher = user.teacherprofile
            stats = {
                'total_classes': teacher.classes.count(),
                'total_students': StudentProfile.objects.filter(
                    enrollment__class_enrolled__in=teacher.classes.all()
                ).distinct().count()
            }
    except Exception as e:
        stats = {'error': str(e)}

    return Response(stats)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def public_stats(request):
    """
    Public API endpoint for general statistics
    """
    stats = {
        'total_schools': School.objects.filter(is_active=True).count(),
        'total_students': User.objects.filter(user_type='student').count(),
        'total_teachers': User.objects.filter(user_type='teacher').count(),
        'total_users': User.objects.filter(is_active=True).count()
    }
    return Response(stats)
