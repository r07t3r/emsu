from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import *
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


# User and Profile Serializers
class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'user_type', 'phone_number', 'profile_picture', 
            'is_verified', 'email_verified', 'phone_verified',
            'created_at', 'last_login'
        ]
        read_only_fields = ['id', 'created_at', 'last_login']


class SchoolSerializer(serializers.ModelSerializer):
    total_students = serializers.SerializerMethodField()
    total_teachers = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = [
            'id', 'name', 'email', 'phone', 'address', 'city', 'state',
            'school_type', 'ownership_type', 'website', 'logo',
            'total_students', 'total_teachers', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_total_students(self, obj):
        return StudentProfile.objects.filter(school=obj).count()

    def get_total_teachers(self, obj):
        return TeacherProfile.objects.filter(school=obj).count()


class ClassSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True)
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = Class
        fields = [
            'id', 'name', 'level', 'school', 'school_name',
            'description', 'student_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_student_count(self, obj):
        return Enrollment.objects.filter(class_enrolled=obj, is_active=True).count()


class SubjectSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True)

    class Meta:
        model = Subject
        fields = [
            'id', 'name', 'code', 'description', 'school', 'school_name',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TeacherProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)

    class Meta:
        model = TeacherProfile
        fields = [
            'id', 'user', 'school', 'school_name', 'employee_id',
            'specialization', 'qualifications', 'experience_years',
            'hire_date', 'salary', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            'id', 'user', 'school', 'school_name', 'student_id',
            'admission_year', 'date_of_birth', 'guardian_name',
            'guardian_phone', 'guardian_email', 'address',
            'emergency_contact', 'medical_info', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ParentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    students = StudentProfileSerializer(many=True, read_only=True)

    class Meta:
        model = ParentProfile
        fields = [
            'id', 'user', 'students', 'occupation', 'workplace',
            'relationship_to_student', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PrincipalProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)

    class Meta:
        model = PrincipalProfile
        fields = [
            'id', 'user', 'school', 'school_name', 'employee_id',
            'qualifications', 'experience_years', 'hire_date',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    class_name = serializers.CharField(source='class_enrolled.name', read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            'id', 'student', 'student_name', 'class_enrolled', 'class_name',
            'enrollment_date', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)

    class Meta:
        model = Attendance
        fields = [
            'id', 'student', 'student_name', 'date', 'status',
            'remarks', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class GradeSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)

    class Meta:
        model = Grade
        fields = [
            'id', 'student', 'student_name', 'subject', 'subject_name',
            'teacher', 'teacher_name', 'score', 'max_score', 'grade_type',
            'comments', 'date_recorded', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)

    class Meta:
        model = Message
        fields = [
            'id', 'sender', 'sender_name', 'recipient', 'recipient_name',
            'subject', 'content', 'is_read', 'read_at', 'created_at'
        ]
        read_only_fields = ['id', 'sender', 'is_read', 'read_at', 'created_at']

    def create(self, validated_data):
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)


class AnnouncementSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)

    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'content', 'author', 'author_name',
            'target_audience', 'priority', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'title', 'message', 'notification_type',
            'is_read', 'read_at', 'created_at'
        ]
        read_only_fields = ['id', 'recipient', 'is_read', 'read_at', 'created_at']


class PostSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'author_name', 'content', 'image',
            'post_type', 'visibility', 'likes_count', 'comments_count',
            'is_liked', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_comments_count(self, obj):
        return obj.comments.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False


class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)

    class Meta:
        model = Comment
        fields = [
            'id', 'post', 'author', 'author_name', 'content',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']


class ConnectionSerializer(serializers.ModelSerializer):
    from_user_name = serializers.CharField(source='from_user.get_full_name', read_only=True)
    to_user_name = serializers.CharField(source='to_user.get_full_name', read_only=True)

    class Meta:
        model = Connection
        fields = [
            'id', 'from_user', 'from_user_name', 'to_user', 'to_user_name',
            'status', 'created_at'
        ]
        read_only_fields = ['id', 'from_user', 'created_at']

    def create(self, validated_data):
        validated_data['from_user'] = self.context['request'].user
        return super().create(validated_data)


class TeacherGroupSerializer(serializers.ModelSerializer):
    members = TeacherProfileSerializer(many=True, read_only=True)
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = TeacherGroup
        fields = [
            'id', 'name', 'description', 'members', 'members_count',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_members_count(self, obj):
        return obj.members.count()


class SchoolSerializer(serializers.ModelSerializer):
    total_users = serializers.SerializerMethodField()
    statistics = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = [
            'id', 'name', 'slug', 'address', 'city', 'state', 'country',
            'phone', 'email', 'website', 'school_type', 'ownership_type',
            'logo', 'banner_image', 'motto', 'vision', 'mission',
            'total_students', 'total_teachers', 'total_users', 'statistics',
            'is_active', 'is_verified', 'created_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'is_verified']

    def get_total_users(self, obj):
        return obj.students.count() + obj.teachers.count()
    
    def get_statistics(self, obj):
        current_session = obj.sessions.filter(is_current=True).first()
        if not current_session:
            return {}
        
        return {
            'classes_count': obj.classes.filter(is_active=True).count(),
            'subjects_count': Subject.objects.count(),
            'enrollments_count': Enrollment.objects.filter(
                class_enrolled__school=obj,
                session=current_session,
                is_active=True
            ).count(),
            'posts_count': obj.posts.filter(is_published=True).count(),
            'events_count': obj.events.filter(
                start_date__gte=timezone.now()
            ).count(),
        }


class AcademicSessionSerializer(serializers.ModelSerializer):
    terms = serializers.SerializerMethodField()

    class Meta:
        model = AcademicSession
        fields = ['id', 'name', 'start_date', 'end_date', 'is_current', 'terms', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_terms(self, obj):
        return TermSerializer(obj.terms.all(), many=True).data


class TermSerializer(serializers.ModelSerializer):
    session_name = serializers.CharField(source='session.name', read_only=True)

    class Meta:
        model = Term
        fields = ['id', 'name', 'start_date', 'end_date', 'is_current', 'session_name', 'created_at']
        read_only_fields = ['id', 'created_at']


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name', 'code', 'description', 'category', 'credit_units',
            'is_core', 'applicable_levels', 'created_at']
        read_only_fields = ['id', 'created_at']


class ClassSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True)
    class_teacher_name = serializers.CharField(source='class_teacher.user.get_full_name', read_only=True)
    enrollment_count = serializers.SerializerMethodField()
    students_count = serializers.SerializerMethodField()
    subjects = serializers.SerializerMethodField()

    class Meta:
        model = Class
        fields = [
            'id', 'name', 'level', 'arm', 'school', 'school_name',
            'class_teacher', 'class_teacher_name', 'capacity', 'current_students',
            'students_count', 'classroom_number', 'subjects', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'current_students']

    def get_enrollment_count(self, obj):
        return obj.enrollments.filter(is_active=True).count()
    
    def get_students_count(self, obj):
        current_session = obj.school.sessions.filter(is_current=True).first()
        if current_session:
            return obj.enrollments.filter(session=current_session, is_active=True).count()
        return 0
    
    def get_subjects(self, obj):
        current_session = obj.school.sessions.filter(is_current=True).first()
        if current_session:
            teacher_classes = TeacherClass.objects.filter(
                class_assigned=obj, session=current_session, is_active=True
            ).select_related('subject', 'teacher__user')
            return [
                {
                    'subject': SubjectSerializer(tc.subject).data,
                    'teacher': tc.teacher.user.get_full_name()
                } for tc in teacher_classes
            ]
        return []


# Profile Serializers
class ProprietorProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    schools_count = serializers.SerializerMethodField()
    schools_data = serializers.SerializerMethodField()

    class Meta:
        model = ProprietorProfile
        fields = [
            'user', 'schools', 'schools_count', 'schools_data',
            'business_license', 'years_experience', 'bio', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_schools_count(self, obj):
        return obj.schools.count()
    
    def get_schools_data(self, obj):
        return SchoolSerializer(obj.schools.all(), many=True).data


class PrincipalProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)

    class Meta:
        model = PrincipalProfile
        fields = [
            'user', 'school', 'school_name', 'employee_id', 'qualification',
            'years_experience', 'appointment_date', 'bio', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TeacherProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    subjects_taught = serializers.SerializerMethodField()
    classes_taught = serializers.SerializerMethodField()
    subjects_taught = serializers.SerializerMethodField()
    classes_assigned = serializers.SerializerMethodField()
    teaching_load = serializers.SerializerMethodField()

    class Meta:
        model = TeacherProfile
        fields = [
            'user', 'school', 'school_name', 'employee_id', 'subjects_taught',
            'classes_assigned', 'teaching_load', 'qualification', 'specialization',
            'years_experience', 'employment_type', 'employment_date',
            'emergency_contact', 'emergency_phone', 'bio', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_subjects_taught(self, obj):
        current_session = AcademicSession.objects.filter(
            school=obj.school, is_current=True
        ).first()
        if current_session:
            return obj.subjects.filter(
                teachersubject__session=current_session,
                teachersubject__is_active=True
            ).values_list('name', flat=True)
        return []

    def get_classes_taught(self, obj):
        current_session = AcademicSession.objects.filter(
            school=obj.school, is_current=True
        ).first()
        if current_session:
            return obj.teacherclass_set.filter(
                session=current_session, is_active=True
            ).values_list('class_assigned__name', flat=True).distinct()
        return []
    
    def get_subjects_taught(self, obj):
        current_session = obj.school.sessions.filter(is_current=True).first()
        if current_session:
            subjects = Subject.objects.filter(
                teachersubject__teacher=obj,
                teachersubject__session=current_session,
                teachersubject__is_active=True
            ).distinct()
            return SubjectSerializer(subjects, many=True).data
        return []
    
    def get_classes_assigned(self, obj):
        current_session = obj.school.sessions.filter(is_current=True).first()
        if current_session:
            classes = Class.objects.filter(
                teacherclass__teacher=obj,
                teacherclass__session=current_session,
                teacherclass__is_active=True
            ).distinct()
            return ClassSerializer(classes, many=True).data
        return []
    
    def get_teaching_load(self, obj):
        current_session = obj.school.sessions.filter(is_current=True).first()
        if current_session:
            return TeacherClass.objects.filter(
                teacher=obj, session=current_session, is_active=True
            ).count()
        return 0


class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    current_class_name = serializers.CharField(source='current_class.name', read_only=True)
    age = serializers.ReadOnlyField()
    class_name = serializers.CharField(source='current_class.name', read_only=True)
    academic_performance = serializers.SerializerMethodField()
    attendance_summary = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = [
            'user', 'school', 'school_name', 'admission_number', 'date_of_birth',
            'age', 'gender', 'blood_group', 'address', 'state_of_origin',
            'nationality', 'religion', 'current_class', 'class_name',
            'guardian_name', 'guardian_phone', 'guardian_email',
            'emergency_contact', 'emergency_phone', 'medical_conditions',
            'allergies', 'academic_performance', 'attendance_summary',
            'is_active', 'admission_date', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'admission_number']

    def get_academic_performance(self, obj):
        current_term = Term.objects.filter(
            session__school=obj.school,
            session__is_current=True,
            is_current=True
        ).first()
        
        if current_term:
            grades = Grade.objects.filter(
                student=obj, term=current_term
            ).values('subject__name').annotate(avg_score=Avg('score'))
            
            return {
                'current_term_average': grades.aggregate(
                    overall_avg=Avg('avg_score')
                )['overall_avg'] or 0,
                'subjects_performance': list(grades)
            }
        return {'current_term_average': 0, 'subjects_performance': []}
    
    def get_attendance_summary(self, obj):
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        attendances = Attendance.objects.filter(
            student=obj, date__gte=thirty_days_ago
        )
        
        total_days = attendances.count()
        present_days = attendances.filter(status='present').count()
        attendance_rate = (present_days / total_days * 100) if total_days > 0 else 0
        
        return {
            'total_days': total_days,
            'present_days': present_days,
            'attendance_rate': round(attendance_rate, 2)
        }


class ParentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    children_count = serializers.SerializerMethodField()
    children_details = serializers.SerializerMethodField()
    children_data = serializers.SerializerMethodField()

    class Meta:
        model = ParentProfile
        fields = [
            'user', 'children', 'children_count', 'children_data',
            'relationship', 'occupation', 'workplace', 'work_phone',
            'address', 'emergency_contact', 'emergency_phone',
            'can_pickup_child', 'authorized_pickup_persons', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_children_count(self, obj):
        return obj.children.count()

    def get_children_details(self, obj):
        return obj.children.values(
            'user__first_name', 'user__last_name', 
            'admission_number', 'current_class__name'
        )
    
    def get_children_data(self, obj):
        return StudentProfileSerializer(obj.children.all(), many=True).data


# Academic Serializers
class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    class_name = serializers.CharField(source='class_enrolled.name', read_only=True)
    session_name = serializers.CharField(source='session.name', read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            'id', 'student', 'student_name', 'class_enrolled', 'class_name',
            'session', 'session_name', 'enrollment_date', 'is_active',
            'withdrawal_date', 'withdrawal_reason'
        ]
        read_only_fields = ['id', 'enrollment_date']


class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    class_name = serializers.CharField(source='class_attended.name', read_only=True)
    marked_by_name = serializers.CharField(source='marked_by.user.get_full_name', read_only=True)

    class Meta:
        model = Attendance
        fields = [
            'id', 'student', 'student_name', 'class_attended', 'class_name',
            'date', 'status', 'time_in', 'time_out', 'remarks',
            'marked_by', 'marked_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class GradeSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    class_name = serializers.CharField(source='class_taken.name', read_only=True)
    term_name = serializers.CharField(source='term.get_name_display', read_only=True)
    teacher_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)
    percentage = serializers.ReadOnlyField()
    letter_grade = serializers.ReadOnlyField()

    class Meta:
        model = Grade
        fields = [
            'id', 'student', 'student_name', 'subject', 'subject_name',
            'class_taken', 'class_name', 'term', 'term_name',
            'assessment_type', 'score', 'total_marks', 'percentage',
            'letter_grade', 'teacher', 'teacher_name', 'comments',
            'date_recorded'
        ]
        read_only_fields = ['id', 'date_recorded']


# Communication Serializers
class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    recipient_count = serializers.SerializerMethodField()
    recipients_data = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'sender', 'sender_name', 'recipients', 'recipients_data',
            'subject', 'body', 'message_type', 'attachments', 'is_urgent',
            'read_receipt_required', 'unread_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_recipient_count(self, obj):
        return obj.recipients.count()
    
    def get_recipients_data(self, obj):
        recipients = MessageRecipient.objects.filter(message=obj).select_related('recipient')
        return [
            {
                'user': UserSerializer(mr.recipient).data,
                'is_read': mr.is_read,
                'read_at': mr.read_at
            } for mr in recipients
        ]
    
    def get_unread_count(self, obj):
        return MessageRecipient.objects.filter(message=obj, is_read=False).count()


class MessageRecipientSerializer(serializers.ModelSerializer):
    message_subject = serializers.CharField(source='message.subject', read_only=True)
    sender_name = serializers.CharField(source='message.sender.get_full_name', read_only=True)

    class Meta:
        model = MessageRecipient
        fields = '__all__'


class AnnouncementSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True)
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)

    class Meta:
        model = Announcement
        fields = [
            'id', 'school', 'school_name', 'title', 'content',
            'announcement_type', 'target_audience', 'author', 'author_name',
            'is_published', 'publish_date', 'expire_date', 'is_pinned',
            'attachments', 'views_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'views_count', 'created_at', 'updated_at']


class NotificationSerializer(serializers.ModelSerializer):
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'recipient_name', 'title', 'message',
            'notification_type', 'is_read', 'read_at', 'action_url',
            'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# Social Serializers
class PostSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    is_liked = serializers.SerializerMethodField()
    author_profile_picture = serializers.ImageField(source='author.profile_picture', read_only=True)
    comments_data = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'author_name', 'author_profile_picture',
            'school', 'school_name', 'title', 'content', 'post_type',
            'visibility', 'tags', 'attachments', 'image',
            'likes_count', 'comments_count', 'shares_count', 'views_count',
            'is_liked', 'comments_data', 'is_pinned', 'is_featured',
            'is_published', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'likes_count', 'comments_count', 'shares_count', 
            'views_count', 'created_at', 'updated_at'
        ]

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False
    
    def get_comments_data(self, obj):
        comments = obj.comments.filter(parent__isnull=True)[:5]
        return CommentSerializer(comments, many=True, context=self.context).data


class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    replies_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    author_profile_picture = serializers.ImageField(source='author.profile_picture', read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'post', 'author', 'author_name', 'author_profile_picture',
            'parent', 'content', 'likes_count', 'is_liked',
            'replies', 'is_approved', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'likes_count', 'created_at', 'updated_at']

    def get_replies_count(self, obj):
        return obj.replies.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False
    
    def get_replies(self, obj):
        if obj.replies.exists():
            return CommentSerializer(obj.replies.all()[:3], many=True, context=self.context).data
        return []


class ConnectionSerializer(serializers.ModelSerializer):
    from_user_name = serializers.CharField(source='from_user.get_full_name', read_only=True)
    to_user_name = serializers.CharField(source='to_user.get_full_name', read_only=True)
    from_user_profile_picture = serializers.ImageField(source='from_user.profile_picture', read_only=True)
    to_user_profile_picture = serializers.ImageField(source='to_user.profile_picture', read_only=True)

    class Meta:
        model = Connection
        fields = [
            'id', 'from_user', 'from_user_name', 'from_user_profile_picture',
            'to_user', 'to_user_name', 'to_user_profile_picture',
            'connection_type', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TeacherGroupSerializer(serializers.ModelSerializer):
    creator_name = serializers.CharField(source='creator.user.get_full_name', read_only=True)
    member_count = serializers.SerializerMethodField()
    school_name = serializers.CharField(source='school.name', read_only=True)
    members_count = serializers.SerializerMethodField()
    members_data = serializers.SerializerMethodField()

    class Meta:
        model = TeacherGroup
        fields = [
            'id', 'name', 'description', 'creator', 'creator_name',
            'members', 'members_count', 'members_data', 'school',
            'school_name', 'is_public', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_member_count(self, obj):
        return obj.members.count()
    
    def get_members_count(self, obj):
        return obj.members.count()
    
    def get_members_data(self, obj):
        return TeacherProfileSerializer(obj.members.all()[:10], many=True).data


# Financial Serializers
class FeeStructureSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True)
    session_name = serializers.CharField(source='session.name', read_only=True)
    class_name = serializers.CharField(source='class_level.name', read_only=True)

    class Meta:
        model = FeeStructure
        fields = [
            'id', 'school', 'school_name', 'session', 'session_name',
            'class_level', 'class_name', 'fee_type', 'amount',
            'is_mandatory', 'due_date', 'description', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class FeePaymentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    fee_type = serializers.CharField(source='fee_structure.get_fee_type_display', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)

    class Meta:
        model = FeePayment
        fields = [
            'id', 'student', 'student_name', 'fee_structure', 'fee_type',
            'amount_paid', 'payment_date', 'payment_method', 'reference_number',
            'status', 'receipt_number', 'notes', 'recorded_by', 'recorded_by_name'
        ]
        read_only_fields = ['id', 'payment_date']


# Schedule Serializers
class TimetableSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True)
    class_name = serializers.CharField(source='class_assigned.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)
    session_name = serializers.CharField(source='session.name', read_only=True)

    class Meta:
        model = Timetable
        fields = [
            'id', 'school', 'school_name', 'class_assigned', 'class_name',
            'subject', 'subject_name', 'teacher', 'teacher_name',
            'day_of_week', 'start_time', 'end_time', 'room_number',
            'session', 'session_name', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# Event Serializers
class EventSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True)
    organizer_name = serializers.CharField(source='organizer.get_full_name', read_only=True)
    attendees_count = serializers.SerializerMethodField()
    is_attending = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'school', 'school_name', 'title', 'description',
            'event_type', 'start_date', 'end_date', 'location',
            'organizer', 'organizer_name', 'attendees_count',
            'is_attending', 'is_public', 'max_attendees',
            'registration_required', 'registration_deadline', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_attendees_count(self, obj):
        return obj.attendees.count()

    def get_is_attending(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.attendees.filter(id=request.user.id).exists()
        return False


class EventAttendanceSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source='event.title', read_only=True)
    attendee_name = serializers.CharField(source='attendee.get_full_name', read_only=True)

    class Meta:
        model = EventAttendance
        fields = [
            'id', 'event', 'event_title', 'attendee', 'attendee_name', 'status', 'registered_at'
        ]
        read_only_fields = ['id', 'registered_at']


# Resource Serializers
class ResourceSerializer(serializers.ModelSerializer):
    uploader_name = serializers.CharField(source='uploader.get_full_name', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    class_name = serializers.CharField(source='class_level.name', read_only=True)
    file_size_mb = serializers.SerializerMethodField()

    class Meta:
        model = Resource
        fields = [
            'id', 'title', 'description', 'resource_type', 'file', 'url',
            'uploader', 'uploader_name', 'school', 'school_name',
            'subject', 'subject_name', 'class_level', 'class_name',
            'access_level', 'tags', 'download_count', 'file_size',
            'file_size_mb', 'is_featured', 'is_approved', 'created_at'
        ]
        read_only_fields = ['id', 'download_count', 'file_size', 'created_at']

    def get_file_size_mb(self, obj):
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return None


# Nested Serializers for detailed views
class StudentDetailSerializer(StudentProfileSerializer):
    enrollments = EnrollmentSerializer(many=True, read_only=True)
    recent_grades = serializers.SerializerMethodField()
    recent_attendance = serializers.SerializerMethodField()

    def get_recent_grades(self, obj):
        recent_grades = obj.grades.select_related('subject', 'term').order_by('-date_recorded')[:5]
        return GradeSerializer(recent_grades, many=True).data

    def get_recent_attendance(self, obj):
        recent_attendance = obj.attendances.select_related('class_attended').order_by('-date')[:10]
        return AttendanceSerializer(recent_attendance, many=True).data


class TeacherDetailSerializer(TeacherProfileSerializer):
    recent_grades_given = serializers.SerializerMethodField()
    classes_stats = serializers.SerializerMethodField()

    def get_recent_grades_given(self, obj):
        recent_grades = obj.grades_given.select_related('student', 'subject').order_by('-date_recorded')[:10]
        return GradeSerializer(recent_grades, many=True).data

    def get_classes_stats(self, obj):
        current_session = AcademicSession.objects.filter(
            school=obj.school, is_current=True
        ).first()

        if current_session:
            classes = obj.teacherclass_set.filter(
                session=current_session, is_active=True
            ).select_related('class_assigned')

            stats = []
            for teacher_class in classes:
                class_obj = teacher_class.class_assigned
                stats.append({
                    'class_name': class_obj.name,
                    'student_count': class_obj.enrollments.filter(is_active=True).count(),
                    'subject': teacher_class.subject.name
                })
            return stats
        return []


class SchoolDetailSerializer(SchoolSerializer):
    principals = PrincipalProfileSerializer(many=True, read_only=True)
    recent_announcements = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()

    def get_recent_announcements(self, obj):
        recent_announcements = obj.announcements.filter(is_published=True).order_by('-publish_date')[:5]
        return AnnouncementSerializer(recent_announcements, many=True).data

    def get_stats(self, obj):
        return {
            'total_students': obj.students.filter(is_active=True).count(),
            'total_teachers': obj.teachers.filter(is_active=True).count(),
            'total_classes': obj.classes.filter(is_active=True).count(),
            'total_subjects': Subject.objects.count(),
        }

# Dashboard Serializers
class ProprietorDashboardSerializer(serializers.Serializer):
    total_schools = serializers.IntegerField()
    total_students = serializers.IntegerField()
    total_teachers = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    monthly_revenue = serializers.ListField()
    recent_payments = serializers.ListField()
    top_performing_schools = serializers.ListField()
    school_statistics = serializers.ListField()


class PrincipalDashboardSerializer(serializers.Serializer):
    total_students = serializers.IntegerField()
    total_teachers = serializers.IntegerField()
    total_classes = serializers.IntegerField()
    attendance_rate = serializers.FloatField()
    academic_performance = serializers.DictField()
    recent_announcements = serializers.ListField()
    upcoming_events = serializers.ListField()
    fee_collection_status = serializers.DictField()
    teacher_performance = serializers.ListField()


class TeacherDashboardSerializer(serializers.Serializer):
    total_students = serializers.IntegerField()
    total_classes = serializers.IntegerField()
    total_subjects = serializers.IntegerField()
    attendance_summary = serializers.DictField()
    grading_progress = serializers.DictField()
    upcoming_classes = serializers.ListField()
    recent_posts = serializers.ListField()
    class_performance = serializers.ListField()


class StudentDashboardSerializer(serializers.Serializer):
    current_class = serializers.CharField()
    attendance_rate = serializers.FloatField()
    academic_performance = serializers.DictField()
    upcoming_events = serializers.ListField()
    recent_grades = serializers.ListField()
    assignments = serializers.ListField()
    notifications = serializers.ListField()
    classmates_count = serializers.IntegerField()


class ParentDashboardSerializer(serializers.Serializer):
    children_count = serializers.IntegerField()
    children_data = serializers.ListField()
    overall_attendance = serializers.FloatField()
    academic_summary = serializers.DictField()
    fee_status = serializers.ListField()
    upcoming_events = serializers.ListField()
    recent_communications = serializers.ListField()