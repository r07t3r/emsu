from django.shortcuts import render
from rest_framework import viewsets, permissions
from .models import (
    User, School, Class, Subject,
    TeacherProfile, StudentProfile, ParentProfile,
    Enrollment, Attendance, Grade,
    Message, Announcement, Notification,
    Post, Comment,
    Connection, TeacherGroup, PrincipalProfile
)
from .serializers import (
    UserSerializer, SchoolSerializer,
    ClassSerializer, SubjectSerializer,
    TeacherProfileSerializer, StudentProfileSerializer, ParentProfileSerializer,
    EnrollmentSerializer, AttendanceSerializer, GradeSerializer,
    MessageSerializer, AnnouncementSerializer, NotificationSerializer,
    PostSerializer, CommentSerializer,
    ConnectionSerializer, TeacherGroupSerializer, 
    ProprietorDashboardSerializer,
    PrincipalDashboardSerializer,
    TeacherDashboardSerializer,
    StudentDashboardSerializer,
    ParentDashboardSerializer
)
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Avg, Q
from datetime import datetime, timedelta

class AnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def school_stats(self, request):
        """
        Returns per-school:
          - total_students
          - avg_attendance_rate (past 30 days)
          - avg_grade (all subjects)
        """
        from datetime import date, timedelta
        today = date.today()
        start_30 = today - timedelta(days=30)

        data = []
        for school in School.objects.all():
            total_students = StudentProfile.objects.filter(current_class__school=school).count()
            # Attendance rate = present / total records
            attendance_qs = Attendance.objects.filter(
                enrollment__student__current_class__school=school,
                date__gte=start_30
            )
            total_att = attendance_qs.count()
            present_att = attendance_qs.filter(present=True).count()
            rate = (present_att / total_att * 100) if total_att else None
            # Average grade
            avg_grade = Grade.objects.filter(
                enrollment__student__current_class__school=school
            ).aggregate(avg=Avg('score'))['avg']

            data.append({
                'school_id': str(school.id),
                'school_name': school.name,
                'total_students': total_students,
                'attendance_rate_percent': rate,
                'average_grade': avg_grade,
            })
        return Response(data)

    @action(detail=False, methods=['get'])
    def system_metrics(self, request):
        """
        Returns system‑wide counts:
          - total_posts, total_comments, total_connections
        """
        metrics = {
            'total_posts': Post.objects.count(),
            'total_comments': Comment.objects.count(),
            'total_connections': Connection.objects.filter(accepted=True).count(),
        }
        return Response(metrics)

class IsProprietor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'proprietor'

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]  # only admins manage users

class SchoolViewSet(viewsets.ModelViewSet):
    queryset = School.objects.select_related('proprietor').all()
    serializer_class = SchoolSerializer
    permission_classes = [permissions.IsAuthenticated, IsProprietor]

class ClassViewSet(viewsets.ModelViewSet):
    queryset = Class.objects.select_related('school').all()
    serializer_class = ClassSerializer
    permission_classes = [permissions.IsAuthenticated]

class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticated]

class TeacherProfileViewSet(viewsets.ModelViewSet):
    queryset = TeacherProfile.objects.prefetch_related('subjects').all()
    serializer_class = TeacherProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

class StudentProfileViewSet(viewsets.ModelViewSet):
    queryset = StudentProfile.objects.select_related('current_class').all()
    serializer_class = StudentProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

class ParentProfileViewSet(viewsets.ModelViewSet):
    queryset = ParentProfile.objects.prefetch_related('children').all()
    serializer_class = ParentProfileSerializer
    permission_classes = [permissions.IsAuthenticated]


class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.select_related('student', 'class_assigned').all()
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.select_related('enrollment').all()
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]

class GradeViewSet(viewsets.ModelViewSet):
    queryset = Grade.objects.select_related('enrollment', 'subject').all()
    serializer_class = GradeSerializer
    permission_classes = [permissions.IsAuthenticated]

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.select_related('sender', 'recipient').all()
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Force sender to be request.user
        serializer.save(sender=self.request.user)

class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.select_related('school').all()
    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.IsAuthenticated]

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only notifications for this user
        return Notification.objects.filter(user=self.request.user)

class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.select_related('author').all()
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Force author to be request.user
        serializer.save(author=self.request.user)

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.select_related('author', 'post').all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class ConnectionViewSet(viewsets.ModelViewSet):
    """
    Students can request connections; only parties can accept.
    """
    queryset = Connection.objects.select_related('from_student','to_student').all()
    serializer_class = ConnectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # always set from_student = request.user.student_profile
        serializer.save(from_student=self.request.user.student_profile)

    def perform_update(self, serializer):
        # mark responded_at when accepted or declined
        serializer.instance.responded_at = timezone.now()
        return super().perform_update(serializer)


class TeacherGroupViewSet(viewsets.ModelViewSet):
    queryset = TeacherGroup.objects.prefetch_related('members').all()
    serializer_class = TeacherGroupSerializer
    permission_classes = [permissions.IsAuthenticated]


class DashboardViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        """
        Redirect to the correct role endpoint.
        """
        role = request.user.role
        return getattr(self, f"{role}_dashboard")(request)

    @action(detail=False, methods=['get'], url_path='proprietor')
    def proprietor_dashboard(self, request):
        # 1. Total schools owned
        schools = School.objects.filter(proprietor=request.user)
        school_count = schools.count()
        # 2. Average attendance rate across those schools (last 30d)
        start = timezone.now().date() - timedelta(days=30)
        att_qs = Attendance.objects.filter(
            enrollment__student__current_class__school__in=schools,
            date__gte=start
        )
        total = att_qs.count()
        present = att_qs.filter(present=True).count()
        avg_attendance = (present/total*100) if total else None
        # 3. Average grade
        avg_grade = Grade.objects.filter(
            enrollment__student__current_class__school__in=schools
        ).aggregate(avg=Avg('score'))['avg']
        # 4. Recent sign‑ups (students) per day last week
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        signups = StudentProfile.objects.filter(
            created_at__date__gte=week_ago,
            current_class__school__in=schools
        ).extra({
            'day': "date(created_at)"
        }).values('day').annotate(count=Count('id')).order_by('day')

        data = {
            'school_count': school_count,
            'avg_attendance_percent': avg_attendance,
            'avg_grade': avg_grade,
            'student_signups_last_7_days': list(signups),
        }
        serializer = ProprietorDashboardSerializer(data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='principal')
    def principal_dashboard(self, request):
        school = request.user.principal_profile.school
        # 1. Attendance by class (last 30d)
        start = timezone.now().date() - timedelta(days=30)
        classes = Class.objects.filter(school=school)
        attendance = []
        for cls in classes:
            att_qs = Attendance.objects.filter(
                enrollment__student__current_class=cls,
                date__gte=start
            )
            total = att_qs.count()
            present = att_qs.filter(present=True).count()
            rate = (present/total*100) if total else None
            attendance.append({'class': cls.name, 'attendance_rate': rate})

        # 2. Avg score by subject
        subjects = Grade.objects.filter(
            enrollment__student__current_class__school=school
        ).values('subject__title').annotate(avg_score=Avg('score'))

        # 3. Recent announcements
        recent = Announcement.objects.filter(
            school=school
        ).order_by('-published_at')[:5]
        recent_serialized = [
            {'id': a.id, 'title': a.title, 'published_at': a.published_at}
            for a in recent
        ]

        data = {
            'attendance_by_class': attendance,
            'avg_score_by_subject': list(subjects),
            'recent_announcements': recent_serialized,
        }
        serializer = PrincipalDashboardSerializer(data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)
        

    @action(detail=False, methods=['get'], url_path='teacher')
    def teacher_dashboard(self, request):
        # 1. Class list
        teacher = request.user.teacher_profile
        classes = teacher.subjects.values_list('title', flat=True)
        # 2. Pending grades (enrollments needing grading)
        #    Assuming you have a status flag; else list all enrollments
        pending = []
        from .models import Enrollment
        for subj in teacher.subjects.all():
            grades = Grade.objects.filter(subject=subj, remarks='')
            for g in grades:
                pending.append({
                    'student': str(g.enrollment.student.user),
                    'subject': subj.title,
                    'enrollment_id': g.enrollment.id,
                })
        # 3. Unread messages
        unread = Message.objects.filter(
            recipient=request.user, is_read=False
        ).count()

        data = {
            'classes': list(classes),
            'pending_grades': pending,
            'unread_messages_count': unread,
        }
        serializer = TeacherDashboardSerializer(data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='student')
    def student_dashboard(self, request):
        profile = request.user.student_profile
        # 1. Grades per subject
        grades = Grade.objects.filter(
            enrollment__student=profile
        ).values('subject__title', 'score')
        # 2. Attendance summary (present vs absent total)
        atts = Attendance.objects.filter(enrollment__student=profile)
        present = atts.filter(present=True).count()
        absent = atts.filter(present=False).count()
        # 3. Recent posts & announcements
        posts = Message.objects.none()  # replace with Post model import if needed

        data = {
            'grades': list(grades),
            'attendance': {'present': present, 'absent': absent},
            'recent_announcements': [
                {'id': a.id, 'title': a.title}
                for a in Announcement.objects.filter(school=profile.current_class.school).order_by('-published_at')[:5]
            ],
        }
        serializer = StudentDashboardSerializer(data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='parent')
    def parent_dashboard(self, request):
        profile = request.user.parent_profile
        child = profile.children.first()  # support multiple children as needed
        # 1. Child’s attendance & grades
        atts = Attendance.objects.filter(enrollment__student=child)
        present = atts.filter(present=True).count()
        absent = atts.filter(present=False).count()
        grades = Grade.objects.filter(enrollment__student=child) \
                  .values('subject__title', 'score')
        # 2. Notifications
        notifs = request.user.notifications.filter(is_read=False)[:10]
        notifs_data = [{'id': n.id, 'content': str(n.content_object)} for n in notifs]

        data = {
            'child_attendance': {'present': present, 'absent': absent},
            'child_grades': list(grades),
            'unread_notifications': notifs_data,
        }
        serializer = ParentDashboardSerializer(data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)
