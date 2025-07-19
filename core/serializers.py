from rest_framework import serializers
from .models import (
    User, School, Class, Subject,
    TeacherProfile, StudentProfile, ParentProfile,
    Enrollment, Attendance, Grade,
    Message, Announcement, Notification,
    Post, Comment,
    Connection, TeacherGroup
)

# 1. User Serializer
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role']

# 2. School Serializer
class SchoolSerializer(serializers.ModelSerializer):
    proprietor = UserSerializer(read_only=True)
    proprietor_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = School
        fields = [
            'id', 'name', 'code', 'address', 'logo',
            'proprietor', 'proprietor_id',
            'created_at', 'updated_at'
        ]

# 3. Class Serializer
class ClassSerializer(serializers.ModelSerializer):
    school = SchoolSerializer(read_only=True)
    school_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Class
        fields = ['id', 'name', 'school', 'school_id', 'created_at', 'updated_at']

# 4. Subject Serializer
class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'title', 'code', 'created_at', 'updated_at']

# 5. TeacherProfile Serializer
class TeacherProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True)
    subjects = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Subject.objects.all()
    )

    class Meta:
        model = TeacherProfile
        fields = ['id', 'user', 'user_id', 'subjects', 'created_at', 'updated_at']

# 6. StudentProfile Serializer
class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True)
    current_class = ClassSerializer(read_only=True)
    current_class_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            'id', 'user', 'user_id',
            'current_class', 'current_class_id',
            'created_at', 'updated_at'
        ]

# 7. ParentProfile Serializer
class ParentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True)
    children = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=StudentProfile.objects.all()
    )

    class Meta:
        model = ParentProfile
        fields = ['id', 'user', 'user_id', 'children', 'created_at', 'updated_at']


class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = [
            'id', 'student', 'class_assigned',
            'start_date', 'end_date',
            'created_at', 'updated_at'
        ]

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = [
            'id', 'enrollment', 'date',
            'present', 'created_at', 'updated_at'
        ]

class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = [
            'id', 'enrollment', 'subject',
            'score', 'remarks',
            'created_at', 'updated_at'
        ]

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    sender_id = serializers.UUIDField(write_only=True)
    recipient = UserSerializer(read_only=True)
    recipient_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Message
        fields = [
            'id', 'sender', 'sender_id',
            'recipient', 'recipient_id',
            'subject', 'body', 'is_read',
            'created_at', 'updated_at'
        ]


class AnnouncementSerializer(serializers.ModelSerializer):
    school = SchoolSerializer(read_only=True)
    school_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'message',
            'school', 'school_id',
            'published_at', 'expires_at',
            'created_at', 'updated_at'
        ]


class NotificationSerializer(serializers.ModelSerializer):
    content_object = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'content_type',
            'object_id', 'content_object',
            'is_read', 'created_at', 'updated_at'
        ]

    def get_content_object(self, obj):
        # Represent nested object minimally
        return str(obj.content_object)
    

class PostSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    author_id = serializers.UUIDField(write_only=True)
    resource_file = serializers.FileField(required=False)

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'author_id',
            'title', 'body',
            'resource_file', 'published',
            'created_at', 'updated_at'
        ]

class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    author_id = serializers.UUIDField(write_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'post', 'author', 'author_id',
            'body', 'parent', 'replies',
            'created_at', 'updated_at'
        ]

    def get_replies(self, obj):
        # Return minimal nested replies
        qs = obj.replies.all()
        return [{'id': c.id, 'body': c.body, 'author': c.author.email} for c in qs]

class ConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Connection
        fields = [
            'id', 'from_student', 'to_student',
            'accepted', 'requested_at', 'responded_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['requested_at', 'responded_at']

class TeacherGroupSerializer(serializers.ModelSerializer):
    members = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=TeacherProfile.objects.all()
    )

    class Meta:
        model = TeacherGroup
        fields = [
            'id', 'name', 'description',
            'members',
            'created_at', 'updated_at'
        ]

class ProprietorDashboardSerializer(serializers.Serializer):
    school_count               = serializers.IntegerField()
    avg_attendance_percent     = serializers.FloatField(allow_null=True)
    avg_grade                  = serializers.FloatField(allow_null=True)
    student_signups_last_7_days= serializers.ListField(
        child=serializers.DictField(child=serializers.IntegerField()),  # {'day': '2025-07-10', 'count': 5}
    )

class PrincipalDashboardSerializer(serializers.Serializer):
    attendance_by_class    = serializers.ListField(
        child=serializers.DictField(child=serializers.FloatField()),  # {'class':'JS1','attendance_rate':95.0}
    )
    avg_score_by_subject   = serializers.ListField(
        child=serializers.DictField(child=serializers.FloatField()),  # {'subject__title':'Math','avg_score':88.5}
    )
    recent_announcements   = serializers.ListField(
        child=serializers.DictField()  # {'id':UUID,'title':str,'published_at':datetime}
    )

class TeacherDashboardSerializer(serializers.Serializer):
    classes                = serializers.ListField(child=serializers.CharField())
    pending_grades         = serializers.ListField(
        child=serializers.DictField()  # {'student':str,'subject':str,'enrollment_id':UUID}
    )
    unread_messages_count  = serializers.IntegerField()

class StudentDashboardSerializer(serializers.Serializer):
    grades                 = serializers.ListField(
        child=serializers.DictField(child=serializers.FloatField())
    )
    attendance             = serializers.DictField(child=serializers.IntegerField())
    recent_announcements   = serializers.ListField(
        child=serializers.DictField()  # {'id':UUID,'title':str}
    )

class ParentDashboardSerializer(serializers.Serializer):
    child_attendance       = serializers.DictField(child=serializers.IntegerField())
    child_grades           = serializers.ListField(
        child=serializers.DictField(child=serializers.FloatField())
    )
    unread_notifications   = serializers.ListField(
        child=serializers.DictField()  # {'id':UUID,'content':str}
    )
