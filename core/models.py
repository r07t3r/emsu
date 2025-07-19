import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class BaseModel(models.Model):
    """
    An abstract base class model that provides:
     - UUID primary key
     - created_at and updated_at timestamps
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Primary key as UUID"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this record was last updated"
    )

    class Meta:
        abstract = True

class User(AbstractUser, BaseModel):
    """
    Extends Django's AbstractUser:
     - Uses email as unique identifier
     - Adds role-based access control
    """
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    email = models.EmailField(
        unique=True,
        help_text="Email address used for login"
    )

    ROLE_CHOICES = [
        ('proprietor', 'Proprietor'),
        ('principal', 'Principal'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('parent', 'Parent'),
    ]
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        help_text="Defines user role for access control"
    )

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    class Meta:
        indexes = [
            models.Index(fields=['email'], name='idx_user_email'),
            models.Index(fields=['role'], name='idx_user_role'),
        ]

class School(BaseModel):
    """
    Represents a primary/secondary school.
    """
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(
        max_length=12,
        unique=True,
        help_text="Short alphanumeric school code"
    )
    address = models.TextField()
    logo = models.ImageField(
        upload_to='school_logos/',
        blank=True,
        null=True
    )
    proprietor = models.ForeignKey(
        'core.User',
        limit_choices_to={'role': 'proprietor'},
        on_delete=models.PROTECT,
        related_name='owned_schools'
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Schools"
        indexes = [
            models.Index(fields=['code'], name='idx_school_code'),
            models.Index(fields=['name'], name='idx_school_name'),
        ]

class TeacherProfile(BaseModel):
    user = models.OneToOneField(
        'core.User',
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'teacher'},
        related_name='teacher_profile'
    )
    subjects = models.ManyToManyField(
        'Subject',
        related_name='teachers'
    )

    def __str__(self):
        return f"Teacher: {self.user.get_full_name()}"


class StudentProfile(BaseModel):
    user = models.OneToOneField(
        'core.User',
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'},
        related_name='student_profile'
    )
    current_class = models.ForeignKey(
        'Class',
        on_delete=models.PROTECT,
        related_name='students'
    )

    def __str__(self):
        return f"Student: {self.user.get_full_name()}"


class ParentProfile(BaseModel):
    user = models.OneToOneField(
        'core.User',
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'parent'},
        related_name='parent_profile'
    )
    children = models.ManyToManyField(
        'StudentProfile',
        related_name='parents'
    )

    def __str__(self):
        return f"Parent: {self.user.get_full_name()}"

class Class(BaseModel):
    """
    Represents a class or form (e.g., JS1, SS2).
    """
    name = models.CharField(max_length=50, unique=True)
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='classes'
    )

    def __str__(self):
        return f"{self.school.code} - {self.name}"

    class Meta:
        unique_together = ('school', 'name')
        indexes = [
            models.Index(fields=['school', 'name'], name='idx_class_school_name'),
        ]


class Subject(BaseModel):
    """
    Represents an academic subject.
    """
    title = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.title

    class Meta:
        indexes = [
            models.Index(fields=['code'], name='idx_subject_code'),
        ]


class Enrollment(BaseModel):
    """
    Records when a StudentProfile joins/leaves a Class.
    """
    student = models.ForeignKey(
        'StudentProfile',
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    class_assigned = models.ForeignKey(
        'Class',
        on_delete=models.PROTECT,
        related_name='enrollments'
    )
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(
        blank=True,
        null=True,
        help_text="Empty if currently enrolled"
    )

    class Meta:
        unique_together = ('student', 'class_assigned', 'start_date')
        indexes = [
            models.Index(fields=['student', 'class_assigned'], name='idx_enrollment_student_class'),
        ]

    def __str__(self):
        return f"{self.student} in {self.class_assigned} from {self.start_date}"

class Attendance(BaseModel):
    """
    Daily attendance record for each Enrollment.
    """
    enrollment = models.ForeignKey(
        'Enrollment',
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )
    date = models.DateField(default=timezone.now)
    present = models.BooleanField(default=True)

    class Meta:
        unique_together = ('enrollment', 'date')
        indexes = [
            models.Index(fields=['date'], name='idx_attendance_date'),
        ]

    def __str__(self):
        status = "Present" if self.present else "Absent"
        return f"{self.enrollment.student} on {self.date}: {status}"

class Grade(BaseModel):
    """
    Stores a grade/score for a student in a subject.
    """
    enrollment = models.ForeignKey(
        'Enrollment',
        on_delete=models.CASCADE,
        related_name='grades'
    )
    subject = models.ForeignKey(
        'Subject',
        on_delete=models.PROTECT,
        related_name='grades'
    )
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Score between 0 and 100"
    )
    remarks = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional comments"
    )

    class Meta:
        indexes = [
            models.Index(fields=['subject'], name='idx_grade_subject'),
        ]

    def __str__(self):
        return f"{self.enrollment.student} – {self.subject.code}: {self.score}"

class Message(BaseModel):
    """
    Direct message between two users.
    """
    sender = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    recipient = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='received_messages'
    )
    subject = models.CharField(max_length=255)
    body = models.TextField()
    is_read = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['sender'], name='idx_msg_sender'),
            models.Index(fields=['recipient'], name='idx_msg_recipient'),
        ]

    def __str__(self):
        return f"From {self.sender} to {self.recipient}: {self.subject}"


class Announcement(BaseModel):
    """
    Broadcast announcement. Optionally tied to a specific school.
    """
    title = models.CharField(max_length=255)
    message = models.TextField()
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='announcements',
        null=True,
        blank=True,
        help_text="Null for system‑wide"
    )
    published_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this announcement should no longer be shown"
    )

    class Meta:
        indexes = [
            models.Index(fields=['published_at'], name='idx_ann_published'),
        ]

    def __str__(self):
        scope = self.school.name if self.school else "System"
        return f"[{scope}] {self.title}"


class Notification(BaseModel):
    """
    Generic notification for a user, tied to a Message or Announcement.
    """
    user = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE
    )
    object_id = models.UUIDField()
    content_object = GenericForeignKey('content_type', 'object_id')
    is_read = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['user'], name='idx_notif_user'),
        ]

    def __str__(self):
        return f"Notification for {self.user} — Read: {self.is_read}"

class Post(BaseModel):
    """
    Educational content posts by users.
    """
    author = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='posts'
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    # Optional rich media attachment
    resource_file = models.FileField(
        upload_to='post_resources/',
        blank=True,
        null=True
    )
    published = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['author'], name='idx_post_author'),
            models.Index(fields=['published'], name='idx_post_published'),
        ]

    def __str__(self):
        return f"{self.title} by {self.author.email}"

class Comment(BaseModel):
    """
    Comments on posts (one‑level thread).
    """
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='comments'
    )
    body = models.TextField()
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='replies',
        null=True,
        blank=True,
        help_text="Null for top‑level comments"
    )

    class Meta:
        indexes = [
            models.Index(fields=['post'], name='idx_comment_post'),
            models.Index(fields=['author'], name='idx_comment_author'),
        ]

    def __str__(self):
        return f"Comment by {self.author.email} on {self.post.title}"

class Connection(BaseModel):
    """
    Represents a bi‑directional “friend” connection between two StudentProfiles.
    """
    from_student = models.ForeignKey(
        'StudentProfile',
        on_delete=models.CASCADE,
        related_name='connections_out'
    )
    to_student = models.ForeignKey(
        'StudentProfile',
        on_delete=models.CASCADE,
        related_name='connections_in'
    )
    accepted = models.BooleanField(default=False)
    requested_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('from_student', 'to_student')
        indexes = [
            models.Index(fields=['from_student'], name='idx_conn_from'),
            models.Index(fields=['to_student'], name='idx_conn_to'),
        ]

    def __str__(self):
        status = "Accepted" if self.accepted else "Pending"
        return f"{self.from_student} → {self.to_student} ({status})"


class TeacherGroup(BaseModel):
    """
    Collaboration groups of teachers across schools.
    """
    name = models.CharField(max_length=255, unique=True)
    members = models.ManyToManyField(
        'TeacherProfile',
        related_name='groups'
    )
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class PrincipalProfile(BaseModel):
    """
    Profile extension for Principals, linking them to exactly one School.
    """
    user = models.OneToOneField(
        'core.User',
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'principal'},
        related_name='principal_profile'
    )
    school = models.OneToOneField(
        'School',
        on_delete=models.PROTECT,
        related_name='principal_profile'
    )

    def __str__(self):
        return f"Principal: {self.user.get_full_name()} @ {self.school.name}"
