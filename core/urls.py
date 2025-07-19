from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, SchoolViewSet, ClassViewSet,
    SubjectViewSet, TeacherProfileViewSet,
    StudentProfileViewSet, ParentProfileViewSet,
    EnrollmentViewSet, AttendanceViewSet, GradeViewSet,
    MessageViewSet, AnnouncementViewSet, NotificationViewSet,
    PostViewSet, CommentViewSet,
    ConnectionViewSet, TeacherGroupViewSet,
    AnalyticsViewSet, DashboardViewSet
)


router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'schools', SchoolViewSet)
router.register(r'classes', ClassViewSet)
router.register(r'subjects', SubjectViewSet)
router.register(r'teachers', TeacherProfileViewSet)
router.register(r'students', StudentProfileViewSet)
router.register(r'parents', ParentProfileViewSet)
router.register(r'enrollments', EnrollmentViewSet)
router.register(r'attendance',   AttendanceViewSet)
router.register(r'grades',       GradeViewSet)
router.register(r'messages',       MessageViewSet)
router.register(r'announcements',  AnnouncementViewSet)
router.register(r'notifications',  NotificationViewSet)
router.register(r'posts',    PostViewSet)
router.register(r'comments', CommentViewSet)
router.register(r'connections', ConnectionViewSet)
router.register(r'teacher-groups', TeacherGroupViewSet)
router.register(r'analytics', AnalyticsViewSet, basename='analytics')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')

urlpatterns = router.urls
