from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API Router
router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'schools', views.SchoolViewSet)
router.register(r'classes', views.ClassViewSet)
router.register(r'subjects', views.SubjectViewSet)
router.register(r'teachers', views.TeacherProfileViewSet)
router.register(r'students', views.StudentProfileViewSet)
router.register(r'parents', views.ParentProfileViewSet)
router.register(r'principals', views.PrincipalProfileViewSet)
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
    path('', views.home_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('api/check-email/', views.check_email_availability, name='check_email'),
    path('test/', views.test_view, name='test'),

    # AJAX endpoints
    path('api/check-email/', views.check_email_availability, name='check_email'),
    path('api/schools/', views.get_schools, name='get_schools'),

    # API endpoints
    path('api/', include(router.urls)),
    path('api/dashboard-stats/', views.dashboard_stats, name='dashboard_stats'),
    path('api/public-stats/', views.public_stats, name='public_stats'),
    
    # Advanced messaging endpoints
    path('api/messages/send/', views.send_message, name='send_message'),
    path('api/messages/conversations/', views.get_conversations, name='get_conversations'),
    path('api/messages/conversation/<uuid:user_id>/', views.get_conversation_messages, name='get_conversation_messages'),
    
    # Social features endpoints
    path('api/posts/create/', views.create_post, name='create_post'),
    path('api/posts/<uuid:post_id>/like/', views.like_post, name='like_post'),
    path('api/posts/<uuid:post_id>/comment/', views.add_comment, name='add_comment'),
    
    # School management endpoints
    path('api/schools/create/', views.create_school, name='create_school'),
    path('api/users/search/', views.search_users, name='search_users'),

    # New URLs
    path('reports/generate/', views.generate_report_view, name='generate_report'),
    path('reports/', views.reports_view, name='reports'),
    path('finances/', views.finances_view, name='finances'),
]