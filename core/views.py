from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
import json
import logging

from .models import (
    User, School, StudentProfile, TeacherProfile, 
    ParentProfile, PrincipalProfile, ProprietorProfile,
    Class, Subject, Enrollment, Attendance, Grade, Message,
    Announcement, Notification, Post, Comment, Connection, TeacherGroup
)
from .serializers import *
from .utils.notifications import create_notification
from django.http import HttpResponse

def test_view(request):
    return HttpResponse("<h1>This is a test - if you see this, views are working</h1>")

logger = logging.getLogger(__name__)


def home_view(request):
    """
    Home page view
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/home.html')


def register_view(request):
    """
    Registration page view with enhanced validation
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    # Get all schools for the registration form
    schools = School.objects.filter(is_active=True).order_by('name')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                first_name = request.POST.get('first_name', '').strip()
                last_name = request.POST.get('last_name', '').strip()
                email = request.POST.get('email', '').strip().lower()
                password = request.POST.get('password', '')
                user_type = request.POST.get('user_type', '')
                school_id = request.POST.get('school', '')

                # Comprehensive validation
                errors = []

                if not first_name:
                    errors.append('First name is required')
                elif len(first_name) < 2:
                    errors.append('First name must be at least 2 characters')

                if not last_name:
                    errors.append('Last name is required')
                elif len(last_name) < 2:
                    errors.append('Last name must be at least 2 characters')

                if not email:
                    errors.append('Email is required')
                elif '@' not in email or '.' not in email:
                    errors.append('Please enter a valid email address')
                elif User.objects.filter(email=email).exists():
                    errors.append('A user with this email already exists')

                if not password:
                    errors.append('Password is required')
                else:
                    try:
                        validate_password(password)
                    except ValidationError as e:
                        errors.extend(e.messages)

                if not user_type:
                    errors.append('Please select an account type')
                elif user_type not in dict(User.USER_TYPES).keys():
                    errors.append('Invalid account type selected')

                # School validation for certain user types
                if user_type in ['student', 'teacher', 'principal']:
                    if not school_id:
                        errors.append('Please select a school')
                    elif not School.objects.filter(id=school_id, is_active=True).exists():
                        errors.append('Invalid school selected')

                if errors:
                    for error in errors:
                        messages.error(request, error)
                    context = {
                        'schools': schools,
                        'user_types': User.USER_TYPES,
                        'form_data': request.POST
                    }
                    return render(request, 'core/register.html', context)

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
                    school = get_object_or_404(School, id=school_id, is_active=True)

                if user_type == 'student' and school:
                    StudentProfile.objects.create(
                        user=user,
                        school=school,
                        admission_number=f"STU{user.id.hex[:8].upper()}",
                        date_of_birth=timezone.now().date(),  # Temporary - should be from form
                        gender='male',  # Temporary - should be from form
                        address='',  # Temporary - should be from form
                        state_of_origin='',  # Temporary - should be from form
                        admission_date=timezone.now().date(),
                        guardian_name='',  # Temporary - should be from form
                        guardian_phone='',  # Temporary - should be from form
                        emergency_contact='',  # Temporary - should be from form
                        emergency_phone=''  # Temporary - should be from form
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
                        school=school,
                        employee_id=f"PRI{user.id.hex[:8].upper()}"
                    )
                elif user_type == 'proprietor':
                    ProprietorProfile.objects.create(user=user)

                # Log successful registration
                logger.info(f"New user registered: {user.email} ({user.user_type})")

                messages.success(request, 'Account created successfully! Please log in to continue.')
                return redirect('login')

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            messages.error(request, 'Registration failed. Please try again.')

    context = {
        'schools': schools,
        'user_types': User.USER_TYPES
    }
    return render(request, 'core/register.html', context)


def login_view(request):
    """
    Login page view with enhanced security
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember')

        if not email or not password:
            messages.error(request, 'Please enter both email and password')
            return render(request, 'core/login.html')

        try:
            user = authenticate(request, email=email, password=password)
            if user:
                if not user.is_active:
                    messages.error(request, 'Your account is disabled. Please contact support.')
                    return render(request, 'core/login.html')

                login(request, user)

                # Set session expiry based on remember me
                if not remember_me:
                    request.session.set_expiry(0)  # Session expires when browser closes
                else:
                    request.session.set_expiry(1209600)  # 2 weeks

                # Log successful login
                logger.info(f"User logged in: {user.email}")

                # Redirect to next URL or dashboard
                next_url = request.GET.get('next', 'dashboard')
                messages.success(request, f'Welcome back, {user.get_full_name()}!')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid email or password. Please try again.')
                logger.warning(f"Failed login attempt for email: {email}")

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            messages.error(request, 'Login failed. Please try again.')

    return render(request, 'core/login.html')


def logout_view(request):
    """
    Enhanced logout view
    """
    user_name = request.user.get_full_name() if request.user.is_authenticated else 'User'
    logout(request)
    messages.success(request, f'Goodbye {user_name}! You have been logged out successfully.')
    return redirect('home')


@login_required
def dashboard_view(request):
    """
    Main dashboard view that routes users based on their type
    """
    user = request.user

    if user.user_type == 'student':
        return render(request, 'core/dashboard_student.html')
    elif user.user_type == 'teacher':
        return render(request, 'core/dashboard_teacher.html')
    elif user.user_type == 'parent':
        return render(request, 'core/dashboard_parent.html')
    elif user.user_type == 'principal':
        return render(request, 'core/dashboard_principal.html')
    elif user.user_type == 'proprietor':
        return render(request, 'core/dashboard_proprietor.html')
    else:
        messages.error(request, 'Invalid user type. Please contact support.')
        return redirect('home')


@login_required
def profile_view(request):
    """
    User profile view with edit capabilities
    """
    if request.method == 'POST':
        try:
            user = request.user
            user.first_name = request.POST.get('first_name', '').strip()
            user.last_name = request.POST.get('last_name', '').strip()

            if request.FILES.get('profile_picture'):
                user.profile_picture = request.FILES['profile_picture']

            user.save()
            messages.success(request, 'Profile updated successfully!')

        except Exception as e:
            logger.error(f"Profile update error: {str(e)}")
            messages.error(request, 'Failed to update profile. Please try again.')

    return render(request, 'core/profile.html')


# AJAX endpoints for enhanced UX
@csrf_exempt
@require_http_methods(["POST"])
def check_email_availability(request):
    """
    Check if email is available for registration
    """
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()

        if not email:
            return JsonResponse({'available': False, 'message': 'Email is required'})

        if '@' not in email or '.' not in email:
            return JsonResponse({'available': False, 'message': 'Invalid email format'})

        exists = User.objects.filter(email=email).exists()

        return JsonResponse({
            'available': not exists,
            'message': 'Email is already taken' if exists else 'Email is available'
        })

    except Exception as e:
        logger.error(f"Email check error: {str(e)}")
        return JsonResponse({'available': False, 'message': 'Error checking email'})


@require_http_methods(["GET"])
def get_schools(request):
    """
    Get schools list for dynamic loading
    """
    try:
        schools = School.objects.filter(is_active=True).values('id', 'name', 'city', 'state')
        return JsonResponse({'schools': list(schools)})
    except Exception as e:
        logger.error(f"Schools fetch error: {str(e)}")
        return JsonResponse({'schools': []})

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


# Advanced API Views
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_stats(request):
    """
    API endpoint for dashboard statistics
    """
    user = request.user
    stats = {}

    try:
        if user.user_type == 'proprietor':
            # Get proprietor's schools
            proprietor_profile = getattr(user, 'proprietor_profile', None)
            if proprietor_profile:
                schools = proprietor_profile.schools.all()
                total_students = StudentProfile.objects.filter(school__in=schools).count()
                total_teachers = TeacherProfile.objects.filter(school__in=schools).count()
                stats = {
                    'total_schools': schools.count(),
                    'total_students': total_students,
                    'total_teachers': total_teachers,
                }
        elif user.user_type == 'principal':
            principal_profile = getattr(user, 'principal_profile', None)
            if principal_profile:
                school = principal_profile.school
                stats = {
                    'total_students': StudentProfile.objects.filter(school=school).count(),
                    'total_teachers': TeacherProfile.objects.filter(school=school).count(),
                    'total_classes': Class.objects.filter(school=school).count(),
                    'attendance_rate': get_school_attendance_rate(school),
                    'academic_performance': get_school_performance(school),
                }
        elif user.user_type == 'student':
            student = user.student_profile
            stats = {
                'total_subjects': student.enrollments.count(),
                'average_grade': Grade.objects.filter(student=student).aggregate(
                    avg=Avg('score')
                )['avg'] or 0,
                'attendance_rate': Attendance.objects.filter(
                    student=student,
                    status='present'
                ).count() / max(Attendance.objects.filter(student=student).count(), 1) * 100,
                'recent_grades': get_recent_grades(student),
                'upcoming_events': get_upcoming_events(student.school)
            }
        elif user.user_type == 'teacher':
            teacher = user.teacher_profile
            stats = {
                'total_classes': teacher.classes.count(),
                'total_students': StudentProfile.objects.filter(
                    enrollments__class_enrolled__in=teacher.classes.all()
                ).distinct().count(),
                'grading_progress': get_grading_progress(teacher),
                'class_performance': get_class_performance(teacher)
            }
        elif user.user_type == 'parent':
            parent = user.parent_profile
            children = parent.children.all()
            stats = {
                'children_count': children.count(),
                'overall_attendance': get_children_attendance(children),
                'academic_summary': get_children_performance(children),
            }
    except Exception as e:
        logger.error(f"Dashboard stats error: {str(e)}")
        stats = {'error': str(e)}

    return Response(stats)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_message(request):
    """
    Send a message to multiple recipients
    """
    try:
        recipient_ids = request.data.get('recipients', [])
        subject = request.data.get('subject', '')
        body = request.data.get('body', '')
        message_type = request.data.get('message_type', 'private')
        is_urgent = request.data.get('is_urgent', False)
        
        if not recipient_ids or not body:
            return Response({
                'error': 'Recipients and message body are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create message
        message = Message.objects.create(
            sender=request.user,
            subject=subject,
            body=body,
            message_type=message_type,
            is_urgent=is_urgent
        )
        
        # Add recipients
        recipients = User.objects.filter(id__in=recipient_ids)
        for recipient in recipients:
            MessageRecipient.objects.create(
                message=message,
                recipient=recipient
            )
            
            # Send real-time notification
            if is_urgent:
                create_notification(
                    recipient=recipient,
                    title=f"Urgent Message from {request.user.get_full_name()}",
                    message=subject or body[:50] + "...",
                    notification_type="warning"
                )
        
        return Response({
            'message': 'Message sent successfully',
            'message_id': str(message.id)
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Send message error: {str(e)}")
        return Response({
            'error': 'Failed to send message'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_conversations(request):
    """
    Get user's conversations
    """
    try:
        # Get messages where user is sender or recipient
        sent_messages = Message.objects.filter(sender=request.user)
        received_messages = Message.objects.filter(
            recipients=request.user
        ).distinct()
        
        # Combine and get unique conversations
        all_messages = sent_messages.union(received_messages).order_by('-created_at')
        
        conversations = {}
        for message in all_messages:
            # Get other participants
            if message.sender == request.user:
                participants = message.recipients.exclude(id=request.user.id)
            else:
                participants = [message.sender]
            
            for participant in participants:
                conv_key = str(participant.id)
                if conv_key not in conversations:
                    conversations[conv_key] = {
                        'participant': {
                            'id': str(participant.id),
                            'name': participant.get_full_name(),
                            'email': participant.email,
                            'profile_picture': participant.profile_picture.url if participant.profile_picture else None
                        },
                        'last_message': {
                            'id': str(message.id),
                            'subject': message.subject,
                            'body': message.body[:100] + '...' if len(message.body) > 100 else message.body,
                            'is_urgent': message.is_urgent,
                            'created_at': message.created_at.isoformat(),
                            'is_read': MessageRecipient.objects.filter(
                                message=message,
                                recipient=request.user,
                                is_read=True
                            ).exists() if message.sender != request.user else True
                        },
                        'unread_count': MessageRecipient.objects.filter(
                            message__sender=participant,
                            recipient=request.user,
                            is_read=False
                        ).count()
                    }
        
        return Response(list(conversations.values()), status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Get conversations error: {str(e)}")
        return Response({
            'error': 'Failed to load conversations'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_conversation_messages(request, user_id):
    """
    Get messages in a conversation with specific user
    """
    try:
        other_user = get_object_or_404(User, id=user_id)
        
        # Get messages between users
        messages = Message.objects.filter(
            models.Q(sender=request.user, recipients=other_user) |
            models.Q(sender=other_user, recipients=request.user)
        ).distinct().order_by('created_at')
        
        # Mark messages as read
        MessageRecipient.objects.filter(
            message__sender=other_user,
            recipient=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        
        # Serialize messages
        message_data = []
        for message in messages:
            message_data.append({
                'id': str(message.id),
                'sender': {
                    'id': str(message.sender.id),
                    'name': message.sender.get_full_name(),
                    'email': message.sender.email
                },
                'subject': message.subject,
                'body': message.body,
                'is_urgent': message.is_urgent,
                'created_at': message.created_at.isoformat(),
                'is_own': message.sender == request.user
            })
        
        return Response(message_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Get conversation messages error: {str(e)}")
        return Response({
            'error': 'Failed to load messages'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_post(request):
    """
    Create a new social post
    """
    try:
        title = request.data.get('title', '')
        content = request.data.get('content', '')
        post_type = request.data.get('post_type', 'general')
        visibility = request.data.get('visibility', 'public')
        tags = request.data.get('tags', [])
        
        if not content:
            return Response({
                'error': 'Post content is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user's school if applicable
        school = None
        if hasattr(request.user, 'student_profile'):
            school = request.user.student_profile.school
        elif hasattr(request.user, 'teacher_profile'):
            school = request.user.teacher_profile.school
        elif hasattr(request.user, 'principal_profile'):
            school = request.user.principal_profile.school
        
        post = Post.objects.create(
            author=request.user,
            school=school,
            title=title,
            content=content,
            post_type=post_type,
            visibility=visibility,
            tags=tags
        )
        
        # Handle file upload
        if 'image' in request.FILES:
            post.image = request.FILES['image']
            post.save()
        
        return Response({
            'message': 'Post created successfully',
            'post_id': str(post.id)
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Create post error: {str(e)}")
        return Response({
            'error': 'Failed to create post'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def like_post(request, post_id):
    """
    Like or unlike a post
    """
    try:
        post = get_object_or_404(Post, id=post_id)
        
        like, created = PostLike.objects.get_or_create(
            post=post,
            user=request.user
        )
        
        if not created:
            like.delete()
            liked = False
        else:
            liked = True
        
        # Update likes count
        post.likes_count = post.likes.count()
        post.save()
        
        return Response({
            'liked': liked,
            'likes_count': post.likes_count
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Like post error: {str(e)}")
        return Response({
            'error': 'Failed to process like'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_comment(request, post_id):
    """
    Add a comment to a post
    """
    try:
        post = get_object_or_404(Post, id=post_id)
        content = request.data.get('content', '')
        parent_id = request.data.get('parent_id')
        
        if not content:
            return Response({
                'error': 'Comment content is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        parent = None
        if parent_id:
            parent = get_object_or_404(Comment, id=parent_id)
        
        comment = Comment.objects.create(
            post=post,
            author=request.user,
            parent=parent,
            content=content
        )
        
        # Update comments count
        post.comments_count = post.comments.count()
        post.save()
        
        # Notify post author
        if post.author != request.user:
            create_notification(
                recipient=post.author,
                title="New Comment",
                message=f"{request.user.get_full_name()} commented on your post",
                notification_type="info"
            )
        
        return Response({
            'message': 'Comment added successfully',
            'comment_id': str(comment.id)
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Add comment error: {str(e)}")
        return Response({
            'error': 'Failed to add comment'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_school(request):
    """
    Create a new school (proprietors only)
    """
    if request.user.user_type != 'proprietor':
        return Response({
            'error': 'Only proprietors can create schools'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        school_data = request.data
        
        # Validate required fields
        required_fields = ['name', 'email', 'phone', 'address', 'city', 'state', 'school_type', 'ownership_type']
        for field in required_fields:
            if not school_data.get(field):
                return Response({
                    'error': f'{field} is required'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        school = School.objects.create(
            name=school_data['name'],
            email=school_data['email'],
            phone=school_data['phone'],
            address=school_data['address'],
            city=school_data['city'],
            state=school_data['state'],
            school_type=school_data['school_type'],
            ownership_type=school_data['ownership_type'],
            establishment_date=school_data.get('establishment_date'),
            motto=school_data.get('motto', ''),
            vision=school_data.get('vision', ''),
            mission=school_data.get('mission', ''),
            website=school_data.get('website', ''),
            registration_number=school_data.get('registration_number', '')
        )
        
        # Add to proprietor's schools
        proprietor_profile, created = ProprietorProfile.objects.get_or_create(
            user=request.user
        )
        proprietor_profile.schools.add(school)
        
        # Create notification
        create_notification(
            recipient=request.user,
            title="School Created",
            message=f"School '{school.name}' has been created successfully",
            notification_type="success"
        )
        
        return Response({
            'message': 'School created successfully',
            'school_id': str(school.id),
            'school': SchoolSerializer(school).data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Create school error: {str(e)}")
        return Response({
            'error': 'Failed to create school'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def search_users(request):
    """
    Search for users across the platform
    """
    try:
        query = request.GET.get('q', '')
        user_type = request.GET.get('type', '')
        school_id = request.GET.get('school')
        
        if len(query) < 2:
            return Response({
                'error': 'Search query must be at least 2 characters'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        users = User.objects.filter(
            models.Q(first_name__icontains=query) |
            models.Q(last_name__icontains=query) |
            models.Q(email__icontains=query),
            is_active=True
        ).exclude(id=request.user.id)
        
        if user_type:
            users = users.filter(user_type=user_type)
        
        if school_id:
            users = users.filter(
                models.Q(student_profile__school_id=school_id) |
                models.Q(teacher_profile__school_id=school_id) |
                models.Q(principal_profile__school_id=school_id)
            )
        
        # Limit results
        users = users[:20]
        
        results = []
        for user in users:
            user_data = {
                'id': str(user.id),
                'name': user.get_full_name(),
                'email': user.email,
                'user_type': user.get_user_type_display(),
                'profile_picture': user.profile_picture.url if user.profile_picture else None
            }
            
            # Add school info if applicable
            if hasattr(user, 'student_profile'):
                user_data['school'] = user.student_profile.school.name
            elif hasattr(user, 'teacher_profile'):
                user_data['school'] = user.teacher_profile.school.name
            elif hasattr(user, 'principal_profile'):
                user_data['school'] = user.principal_profile.school.name
            
            results.append(user_data)
        
        return Response(results, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Search users error: {str(e)}")
        return Response({
            'error': 'Search failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Helper functions for dashboard stats


def get_top_performing_schools(schools):
    """Get top performing schools based on various metrics"""
    school_stats = []
    for school in schools:
        avg_grade = Grade.objects.filter(
            student__school=school
        ).aggregate(avg=Avg('score'))['avg'] or 0
        
        attendance_rate = Attendance.objects.filter(
            student__school=school,
            status='present'
        ).count() / max(
            Attendance.objects.filter(student__school=school).count(), 1
        ) * 100
        
        school_stats.append({
            'name': school.name,
            'avg_grade': round(avg_grade, 2),
            'attendance_rate': round(attendance_rate, 2),
            'total_students': school.students.count()
        })
    
    return sorted(school_stats, key=lambda x: x['avg_grade'], reverse=True)[:5]


def get_school_attendance_rate(school):
    """Get school attendance rate"""
    total = Attendance.objects.filter(student__school=school).count()
    present = Attendance.objects.filter(
        student__school=school,
        status='present'
    ).count()
    return (present / max(total, 1)) * 100


def get_school_performance(school):
    """Get school academic performance"""
    avg_grade = Grade.objects.filter(
        student__school=school
    ).aggregate(avg=Avg('score'))['avg'] or 0
    
    grade_distribution = Grade.objects.filter(
        student__school=school
    ).values('letter_grade').annotate(count=Count('id'))
    
    return {
        'average_grade': round(avg_grade, 2),
        'grade_distribution': list(grade_distribution)
    }




def get_recent_grades(student):
    """Get recent grades for student"""
    grades = Grade.objects.filter(
        student=student
    ).select_related('subject').order_by('-date_recorded')[:5]
    
    return [{
        'subject': grade.subject.name,
        'score': grade.score,
        'letter_grade': grade.letter_grade,
        'date': grade.date_recorded.isoformat()
    } for grade in grades]


def get_upcoming_events(school):
    """Get upcoming events for school"""
    events = Event.objects.filter(
        school=school,
        start_date__gte=timezone.now()
    ).order_by('start_date')[:5]
    
    return [{
        'title': event.title,
        'start_date': event.start_date.isoformat(),
        'event_type': event.event_type
    } for event in events]


def get_grading_progress(teacher):
    """Get grading progress for teacher"""
    total_students = StudentProfile.objects.filter(
        enrollments__class_enrolled__in=teacher.classes.all()
    ).distinct().count()
    
    graded = Grade.objects.filter(teacher=teacher).count()
    
    return {
        'total_students': total_students,
        'graded': graded,
        'progress': (graded / max(total_students, 1)) * 100
    }


def get_class_performance(teacher):
    """Get class performance for teacher"""
    performance = []
    for class_obj in teacher.classes.all():
        avg_grade = Grade.objects.filter(
            class_taken=class_obj,
            teacher=teacher
        ).aggregate(avg=Avg('score'))['avg'] or 0
        
        performance.append({
            'class_name': class_obj.name,
            'average_grade': round(avg_grade, 2)
        })
    
    return performance


def get_children_attendance(children):
    """Get attendance rate for parent's children"""
    if not children:
        return 0
    
    total = sum(
        Attendance.objects.filter(student=child).count()
        for child in children
    )
    present = sum(
        Attendance.objects.filter(student=child, status='present').count()
        for child in children
    )
    
    return (present / max(total, 1)) * 100


def get_children_performance(children):
    """Get academic performance for parent's children"""
    performance = []
    for child in children:
        avg_grade = Grade.objects.filter(
            student=child
        ).aggregate(avg=Avg('score'))['avg'] or 0
        
        performance.append({
            'name': child.user.get_full_name(),
            'average_grade': round(avg_grade, 2)
        })
    
    return performance




@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def public_stats(request):
    """
    Public API endpoint for general statistics    """
    stats = {
        'total_schools': School.objects.filter(is_active=True).count(),
        'total_students': User.objects.filter(user_type='student').count(),
        'total_teachers': User.objects.filter(user_type='teacher').count(),
        'total_users': User.objects.filter(is_active=True).count()
    }
    return Response(stats)


@login_required
def reports_view(request):
    """
    Placeholder view for reports
    """
    return render(request, 'core/reports.html')


@login_required
def generate_report_view(request):
    """
    Placeholder view for generating reports
    """
    return render(request, 'core/generate_report.html')


@login_required
def finances_view(request):
    """
    Placeholder view for finances
    """
    return render(request, 'core/finances.html')