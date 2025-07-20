
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse
from PIL import Image
import uuid
import os


class UserManager(BaseUserManager):
    """Custom user manager that uses email instead of username"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'proprietor')  # Default superuser type
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    USER_TYPES = (
        ('proprietor', 'School Proprietor'),
        ('principal', 'Principal/Head Teacher'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('parent', 'Parent/Guardian'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPES)
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$')],
        blank=True, null=True
    )
    profile_picture = models.ImageField(
        upload_to='profiles/', blank=True, null=True,
        help_text="Profile picture (max 2MB)"
    )
    is_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    account_locked_until = models.DateTimeField(blank=True, null=True)
    
    username = None
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'user_type']
    
    objects = UserManager()
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['user_type']),
            models.Index(fields=['is_active', 'user_type']),
        ]
    
    def save(self, *args, **kwargs):
        if self.profile_picture:
            self.compress_image()
        super().save(*args, **kwargs)
    
    def compress_image(self):
        if self.profile_picture:
            img = Image.open(self.profile_picture.path)
            if img.height > 300 or img.width > 300:
                output_size = (300, 300)
                img.thumbnail(output_size)
                img.save(self.profile_picture.path)
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"


class School(models.Model):
    SCHOOL_TYPES = (
        ('primary', 'Primary School'),
        ('secondary', 'Secondary School'),
        ('both', 'Primary & Secondary'),
    )
    
    OWNERSHIP_TYPES = (
        ('private', 'Private'),
        ('public', 'Public'),
        ('mission', 'Mission'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='Nigeria')
    postal_code = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    website = models.URLField(blank=True)
    school_type = models.CharField(max_length=20, choices=SCHOOL_TYPES)
    ownership_type = models.CharField(max_length=20, choices=OWNERSHIP_TYPES)
    establishment_date = models.DateField(blank=True, null=True)
    registration_number = models.CharField(max_length=100, unique=True, blank=True)
    logo = models.ImageField(upload_to='school_logos/', blank=True, null=True)
    banner_image = models.ImageField(upload_to='school_banners/', blank=True, null=True)
    motto = models.CharField(max_length=200, blank=True)
    vision = models.TextField(blank=True)
    mission = models.TextField(blank=True)
    total_students = models.PositiveIntegerField(default=0)
    total_teachers = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    subscription_plan = models.CharField(max_length=50, default='basic')
    subscription_expires = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'schools'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active', 'is_verified']),
            models.Index(fields=['city', 'state']),
        ]
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('school_detail', kwargs={'slug': self.slug})
    
    def __str__(self):
        return self.name


class AcademicSession(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='sessions')
    name = models.CharField(max_length=100)  # e.g., "2023/2024"
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'academic_sessions'
        unique_together = ['school', 'name']
        ordering = ['-start_date']
    
    def save(self, *args, **kwargs):
        if self.is_current:
            # Ensure only one current session per school
            AcademicSession.objects.filter(
                school=self.school, is_current=True
            ).update(is_current=False)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.school.name} - {self.name}"


class Term(models.Model):
    TERM_CHOICES = (
        ('first', 'First Term'),
        ('second', 'Second Term'),
        ('third', 'Third Term'),
    )
    
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, related_name='terms')
    name = models.CharField(max_length=20, choices=TERM_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'terms'
        unique_together = ['session', 'name']
        ordering = ['session', 'name']
    
    def save(self, *args, **kwargs):
        if self.is_current:
            # Ensure only one current term per session
            Term.objects.filter(
                session=self.session, is_current=True
            ).update(is_current=False)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.session.name} - {self.get_name_display()}"


class Class(models.Model):
    CLASS_LEVELS = (
        ('nursery1', 'Nursery 1'),
        ('nursery2', 'Nursery 2'),
        ('reception', 'Reception'),
        ('primary1', 'Primary 1'),
        ('primary2', 'Primary 2'),
        ('primary3', 'Primary 3'),
        ('primary4', 'Primary 4'),
        ('primary5', 'Primary 5'),
        ('primary6', 'Primary 6'),
        ('jss1', 'JSS 1'),
        ('jss2', 'JSS 2'),
        ('jss3', 'JSS 3'),
        ('ss1', 'SS 1'),
        ('ss2', 'SS 2'),
        ('ss3', 'SS 3'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='classes')
    name = models.CharField(max_length=100)  # e.g., "JSS 1A"
    level = models.CharField(max_length=20, choices=CLASS_LEVELS)
    arm = models.CharField(max_length=10, default='A')  # A, B, C, etc.
    class_teacher = models.ForeignKey(
        'TeacherProfile', on_delete=models.SET_NULL, 
        blank=True, null=True, related_name='managed_classes'
    )
    capacity = models.PositiveIntegerField(default=30)
    current_students = models.PositiveIntegerField(default=0)
    classroom_number = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'classes'
        unique_together = ['school', 'level', 'arm']
        indexes = [
            models.Index(fields=['school', 'level']),
            models.Index(fields=['is_active']),
        ]
        ordering = ['level', 'arm']
    
    def __str__(self):
        return f"{self.school.name} - {self.name}"


class Subject(models.Model):
    SUBJECT_CATEGORIES = (
        ('core', 'Core Subject'),
        ('elective', 'Elective Subject'),
        ('vocational', 'Vocational Subject'),
        ('extracurricular', 'Extra-curricular'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=SUBJECT_CATEGORIES, default='core')
    credit_units = models.PositiveIntegerField(default=1)
    is_core = models.BooleanField(default=True)
    applicable_levels = models.JSONField(default=list)  # List of class levels
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'subjects'
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['category']),
        ]
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


# Profile Models
class ProprietorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='proprietor_profile')
    schools = models.ManyToManyField(School, related_name='proprietors')
    business_license = models.CharField(max_length=100, blank=True)
    years_experience = models.PositiveIntegerField(blank=True, null=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'proprietor_profiles'
    
    def __str__(self):
        return f"Proprietor: {self.user.get_full_name()}"


class PrincipalProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='principal_profile')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='principals')
    employee_id = models.CharField(max_length=50, unique=True)
    qualification = models.CharField(max_length=200, blank=True)
    years_experience = models.PositiveIntegerField(blank=True, null=True)
    appointment_date = models.DateField(blank=True, null=True)
    bio = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'principal_profiles'
        unique_together = ['school', 'employee_id']
    
    def __str__(self):
        return f"Principal: {self.user.get_full_name()} - {self.school.name}"


class TeacherProfile(models.Model):
    EMPLOYMENT_TYPES = (
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('substitute', 'Substitute'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='teachers')
    employee_id = models.CharField(max_length=50)
    subjects = models.ManyToManyField(Subject, through='TeacherSubject')
    classes = models.ManyToManyField(Class, through='TeacherClass')
    qualification = models.CharField(max_length=200, blank=True)
    specialization = models.CharField(max_length=100, blank=True)
    years_experience = models.PositiveIntegerField(blank=True, null=True)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPES, default='full_time')
    employment_date = models.DateField(blank=True, null=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    bank_account = models.CharField(max_length=20, blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'teacher_profiles'
        unique_together = ['school', 'employee_id']
        indexes = [
            models.Index(fields=['school', 'is_active']),
            models.Index(fields=['employee_id']),
        ]
    
    def __str__(self):
        return f"Teacher: {self.user.get_full_name()} - {self.school.name}"


class StudentProfile(models.Model):
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
    )
    
    BLOOD_GROUP_CHOICES = (
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='students')
    admission_number = models.CharField(max_length=50)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUP_CHOICES, blank=True)
    address = models.TextField()
    state_of_origin = models.CharField(max_length=100)
    nationality = models.CharField(max_length=100, default='Nigerian')
    religion = models.CharField(max_length=50, blank=True)
    previous_school = models.CharField(max_length=200, blank=True)
    admission_date = models.DateField()
    current_class = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True, blank=True)
    guardian_name = models.CharField(max_length=200)
    guardian_phone = models.CharField(max_length=20)
    guardian_email = models.EmailField(blank=True)
    guardian_address = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=200)
    emergency_phone = models.CharField(max_length=20)
    medical_conditions = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    graduation_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'student_profiles'
        unique_together = ['school', 'admission_number']
        indexes = [
            models.Index(fields=['school', 'is_active']),
            models.Index(fields=['admission_number']),
            models.Index(fields=['current_class']),
        ]
    
    @property
    def age(self):
        today = timezone.now().date()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    def __str__(self):
        return f"Student: {self.user.get_full_name()} - {self.admission_number}"


class ParentProfile(models.Model):
    RELATIONSHIP_CHOICES = (
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('guardian', 'Guardian'),
        ('relative', 'Relative'),
        ('other', 'Other'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='parent_profile')
    children = models.ManyToManyField(StudentProfile, related_name='parents')
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    occupation = models.CharField(max_length=100, blank=True)
    workplace = models.CharField(max_length=200, blank=True)
    work_phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=200, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    can_pickup_child = models.BooleanField(default=True)
    authorized_pickup_persons = models.TextField(blank=True, help_text="Comma-separated names")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'parent_profiles'
        indexes = [
            models.Index(fields=['relationship']),
        ]
    
    def __str__(self):
        return f"Parent: {self.user.get_full_name()}"


# Enrollment and Academic Models
class Enrollment(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='enrollments')
    class_enrolled = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='enrollments')
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, related_name='enrollments')
    enrollment_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    withdrawal_date = models.DateField(blank=True, null=True)
    withdrawal_reason = models.TextField(blank=True)
    
    class Meta:
        db_table = 'enrollments'
        unique_together = ['student', 'session']
        indexes = [
            models.Index(fields=['student', 'is_active']),
            models.Index(fields=['class_enrolled', 'session']),
        ]
    
    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.class_enrolled.name}"


class TeacherSubject(models.Model):
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'teacher_subjects'
        unique_together = ['teacher', 'subject', 'session']


class TeacherClass(models.Model):
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE)
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'teacher_classes'
        unique_together = ['teacher', 'class_assigned', 'subject', 'session']


class Attendance(models.Model):
    ATTENDANCE_STATUS = (
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    )
    
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='attendances')
    class_attended = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    status = models.CharField(max_length=10, choices=ATTENDANCE_STATUS)
    time_in = models.TimeField(blank=True, null=True)
    time_out = models.TimeField(blank=True, null=True)
    remarks = models.TextField(blank=True)
    marked_by = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'attendances'
        unique_together = ['student', 'date']
        indexes = [
            models.Index(fields=['student', 'date']),
            models.Index(fields=['class_attended', 'date']),
            models.Index(fields=['date', 'status']),
        ]
    
    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.date} ({self.status})"


class Grade(models.Model):
    ASSESSMENT_TYPES = (
        ('ca1', 'Continuous Assessment 1'),
        ('ca2', 'Continuous Assessment 2'),
        ('ca3', 'Continuous Assessment 3'),
        ('ca4', 'Continuous Assessment 4'),
        ('exam', 'Examination'),
        ('project', 'Project'),
        ('practical', 'Practical'),
    )
    
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='grades')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='grades')
    class_taken = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='grades')
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='grades')
    assessment_type = models.CharField(max_length=20, choices=ASSESSMENT_TYPES)
    score = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    total_marks = models.PositiveIntegerField(default=100)
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, related_name='grades_given')
    date_recorded = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True)
    
    class Meta:
        db_table = 'grades'
        unique_together = ['student', 'subject', 'term', 'assessment_type']
        indexes = [
            models.Index(fields=['student', 'term']),
            models.Index(fields=['subject', 'term']),
            models.Index(fields=['class_taken', 'term']),
        ]
    
    @property
    def percentage(self):
        return (self.score / self.total_marks) * 100
    
    @property
    def letter_grade(self):
        percentage = self.percentage
        if percentage >= 90:
            return 'A+'
        elif percentage >= 80:
            return 'A'
        elif percentage >= 70:
            return 'B'
        elif percentage >= 60:
            return 'C'
        elif percentage >= 50:
            return 'D'
        elif percentage >= 40:
            return 'E'
        else:
            return 'F'
    
    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.subject.name} ({self.score})"


# Communication Models
class Message(models.Model):
    MESSAGE_TYPES = (
        ('private', 'Private Message'),
        ('group', 'Group Message'),
        ('announcement', 'Announcement'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipients = models.ManyToManyField(User, through='MessageRecipient', related_name='received_messages')
    subject = models.CharField(max_length=200)
    body = models.TextField()
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='private')
    attachments = models.FileField(upload_to='message_attachments/', blank=True, null=True)
    is_urgent = models.BooleanField(default=False)
    read_receipt_required = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'messages'
        indexes = [
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['message_type']),
            models.Index(fields=['is_urgent']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.sender.get_full_name()}: {self.subject}"


class MessageRecipient(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    is_archived = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'message_recipients'
        unique_together = ['message', 'recipient']


class Announcement(models.Model):
    ANNOUNCEMENT_TYPES = (
        ('general', 'General'),
        ('academic', 'Academic'),
        ('event', 'Event'),
        ('emergency', 'Emergency'),
        ('holiday', 'Holiday'),
    )
    
    TARGET_AUDIENCES = (
        ('all', 'All Users'),
        ('students', 'Students Only'),
        ('teachers', 'Teachers Only'),
        ('parents', 'Parents Only'),
        ('staff', 'Staff Only'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='announcements')
    title = models.CharField(max_length=200)
    content = models.TextField()
    announcement_type = models.CharField(max_length=20, choices=ANNOUNCEMENT_TYPES, default='general')
    target_audience = models.CharField(max_length=20, choices=TARGET_AUDIENCES, default='all')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='announcements')
    is_published = models.BooleanField(default=False)
    publish_date = models.DateTimeField(blank=True, null=True)
    expire_date = models.DateTimeField(blank=True, null=True)
    is_pinned = models.BooleanField(default=False)
    attachments = models.FileField(upload_to='announcement_attachments/', blank=True, null=True)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'announcements'
        indexes = [
            models.Index(fields=['school', 'is_published']),
            models.Index(fields=['target_audience']),
            models.Index(fields=['publish_date']),
            models.Index(fields=['is_pinned']),
        ]
        ordering = ['-is_pinned', '-publish_date']
    
    def __str__(self):
        return f"{self.school.name}: {self.title}"


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('success', 'Success'),
        ('error', 'Error'),
        ('reminder', 'Reminder'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    action_url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications'
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['created_at']),
            models.Index(fields=['notification_type']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.recipient.get_full_name()}: {self.title}"


# Social and Content Models
class Post(models.Model):
    POST_TYPES = (
        ('general', 'General'),
        ('educational', 'Educational'),
        ('announcement', 'Announcement'),
        ('question', 'Question'),
        ('resource', 'Resource'),
        ('achievement', 'Achievement'),
    )
    
    VISIBILITY_CHOICES = (
        ('public', 'Public'),
        ('school', 'School Only'),
        ('class', 'Class Only'),
        ('teachers', 'Teachers Only'),
        ('private', 'Private'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='posts', blank=True, null=True)
    title = models.CharField(max_length=200)
    content = models.TextField()
    post_type = models.CharField(max_length=20, choices=POST_TYPES, default='general')
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    tags = models.JSONField(default=list, blank=True)
    attachments = models.FileField(upload_to='post_attachments/', blank=True, null=True)
    image = models.ImageField(upload_to='post_images/', blank=True, null=True)
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    views_count = models.PositiveIntegerField(default=0)
    is_pinned = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'posts'
        indexes = [
            models.Index(fields=['author', 'created_at']),
            models.Index(fields=['school', 'visibility']),
            models.Index(fields=['post_type']),
            models.Index(fields=['is_published', 'created_at']),
            models.Index(fields=['is_featured']),
        ]
        ordering = ['-is_pinned', '-created_at']
    
    def __str__(self):
        return f"{self.author.get_full_name()}: {self.title}"


class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='replies')
    content = models.TextField()
    likes_count = models.PositiveIntegerField(default=0)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'comments'
        indexes = [
            models.Index(fields=['post', 'created_at']),
            models.Index(fields=['author']),
            models.Index(fields=['parent']),
        ]
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.author.get_full_name()} on {self.post.title}"


class PostLike(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'post_likes'
        unique_together = ['post', 'user']


class CommentLike(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comment_likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'comment_likes'
        unique_together = ['comment', 'user']


# Social Connection Models
class Connection(models.Model):
    CONNECTION_TYPES = (
        ('friend', 'Friend'),
        ('follow', 'Follow'),
        ('classmate', 'Classmate'),
        ('colleague', 'Colleague'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('blocked', 'Blocked'),
    )
    
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='connections_from')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='connections_to')
    connection_type = models.CharField(max_length=20, choices=CONNECTION_TYPES, default='friend')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'connections'
        unique_together = ['from_user', 'to_user']
        indexes = [
            models.Index(fields=['from_user', 'status']),
            models.Index(fields=['to_user', 'status']),
            models.Index(fields=['connection_type']),
        ]
    
    def __str__(self):
        return f"{self.from_user.get_full_name()} -> {self.to_user.get_full_name()} ({self.status})"


class TeacherGroup(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='created_groups')
    members = models.ManyToManyField(TeacherProfile, related_name='teacher_groups')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='teacher_groups', blank=True, null=True)
    is_public = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'teacher_groups'
        indexes = [
            models.Index(fields=['school', 'is_active']),
            models.Index(fields=['is_public']),
        ]
    
    def __str__(self):
        return self.name


# Fee and Financial Models
class FeeStructure(models.Model):
    FEE_TYPES = (
        ('tuition', 'Tuition Fee'),
        ('development', 'Development Fee'),
        ('exam', 'Examination Fee'),
        ('sport', 'Sports Fee'),
        ('transport', 'Transport Fee'),
        ('uniform', 'Uniform Fee'),
        ('book', 'Book Fee'),
        ('meal', 'Meal Fee'),
        ('other', 'Other Fee'),
    )
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='fee_structures')
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, related_name='fee_structures')
    class_level = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='fee_structures')
    fee_type = models.CharField(max_length=20, choices=FEE_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_mandatory = models.BooleanField(default=True)
    due_date = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'fee_structures'
        unique_together = ['school', 'session', 'class_level', 'fee_type']
    
    def __str__(self):
        return f"{self.school.name} - {self.class_level.name} - {self.get_fee_type_display()}: ₦{self.amount}"


class FeePayment(models.Model):
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('partial', 'Partial'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    )
    
    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('card', 'Card Payment'),
        ('mobile_money', 'Mobile Money'),
        ('cheque', 'Cheque'),
    )
    
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='fee_payments')
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    reference_number = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    receipt_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='recorded_payments')
    
    class Meta:
        db_table = 'fee_payments'
        indexes = [
            models.Index(fields=['student', 'payment_date']),
            models.Index(fields=['reference_number']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.student.user.get_full_name()} - ₦{self.amount_paid} ({self.status})"


# Timetable and Schedule Models
class Timetable(models.Model):
    DAYS_OF_WEEK = (
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
    )
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='timetables')
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='timetables')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='timetables')
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='timetables')
    day_of_week = models.CharField(max_length=20, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room_number = models.CharField(max_length=50, blank=True)
    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, related_name='timetables')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'timetables'
        unique_together = ['class_assigned', 'day_of_week', 'start_time', 'session']
        indexes = [
            models.Index(fields=['school', 'day_of_week']),
            models.Index(fields=['teacher', 'day_of_week']),
            models.Index(fields=['class_assigned', 'day_of_week']),
        ]
    
    def __str__(self):
        return f"{self.class_assigned.name} - {self.subject.name} ({self.day_of_week})"


# Event and Activity Models
class Event(models.Model):
    EVENT_TYPES = (
        ('academic', 'Academic'),
        ('sports', 'Sports'),
        ('cultural', 'Cultural'),
        ('examination', 'Examination'),
        ('meeting', 'Meeting'),
        ('holiday', 'Holiday'),
        ('other', 'Other'),
    )
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=200)
    description = models.TextField()
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default='other')
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_events')
    attendees = models.ManyToManyField(User, through='EventAttendance', related_name='events_attending')
    is_public = models.BooleanField(default=True)
    max_attendees = models.PositiveIntegerField(blank=True, null=True)
    registration_required = models.BooleanField(default=False)
    registration_deadline = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'events'
        indexes = [
            models.Index(fields=['school', 'start_date']),
            models.Index(fields=['event_type']),
            models.Index(fields=['is_public']),
        ]
        ordering = ['start_date']
    
    def __str__(self):
        return f"{self.school.name}: {self.title}"


class EventAttendance(models.Model):
    ATTENDANCE_STATUS = (
        ('registered', 'Registered'),
        ('attended', 'Attended'),
        ('absent', 'Absent'),
        ('cancelled', 'Cancelled'),
    )
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    attendee = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS, default='registered')
    registered_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'event_attendances'
        unique_together = ['event', 'attendee']


# Resource and Content Models
class Resource(models.Model):
    RESOURCE_TYPES = (
        ('document', 'Document'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('image', 'Image'),
        ('link', 'Web Link'),
        ('presentation', 'Presentation'),
    )
    
    ACCESS_LEVELS = (
        ('public', 'Public'),
        ('school', 'School Only'),
        ('class', 'Class Only'),
        ('subject', 'Subject Only'),
        ('private', 'Private'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    file = models.FileField(upload_to='resources/', blank=True, null=True)
    url = models.URLField(blank=True)
    uploader = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_resources')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='resources', blank=True, null=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='resources', blank=True, null=True)
    class_level = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='resources', blank=True, null=True)
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVELS, default='school')
    tags = models.JSONField(default=list, blank=True)
    download_count = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    file_size = models.PositiveIntegerField(blank=True, null=True)  # in bytes
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'resources'
        indexes = [
            models.Index(fields=['school', 'access_level']),
            models.Index(fields=['subject']),
            models.Index(fields=['resource_type']),
            models.Index(fields=['is_featured']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
