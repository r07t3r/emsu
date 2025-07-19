
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'schools', views.SchoolViewSet)
router.register(r'classes', views.ClassViewSet)
router.register(r'subjects', views.SubjectViewSet)
router.register(r'teacher-profiles', views.TeacherProfileViewSet)
router.register(r'student-profiles', views.StudentProfileViewSet)
router.register(r'parent-profiles', views.ParentProfileViewSet)
router.register(r'principal-profiles', views.PrincipalProfileViewSet)
router.register(r'enrollments', views.EnrollmentViewSet)
router.register(r'attendance', views.AttendanceViewSet)
router.register(r'grades', views.GradeViewSet)
router.register(r'messages', views.MessageViewSet)
router.register(r'announcements', views.AnnouncementViewSet)
router.register(r'notifications', views.NotificationViewSet)
router.register(r'posts', views.PostViewSet)
router.register(r'comments', views.CommentViewSet)
router.register(r'connections', views.ConnectionViewSet)
router.register(r'teacher-groups', views.TeacherGroupViewSet)

urlpatterns = [
    # API routes
    path('api/', include(router.urls)),
    path('api/dashboard-stats/', views.dashboard_stats, name='dashboard-stats'),
    path('api/public-stats/', views.public_stats, name='public-stats'),
    
    # Template routes
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile, name='profile'),
    path('test/', views.test_view, name='test'),
]
