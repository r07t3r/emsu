
from django.contrib import admin
from .models import User, School, Class, Subject, TeacherProfile, StudentProfile, ParentProfile, PrincipalProfile

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'user_type', 'is_active', 'date_joined']
    list_filter = ['user_type', 'is_active', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-date_joined']

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'phone', 'email', 'created_at']
    search_fields = ['name', 'address']
    ordering = ['name']

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ['name', 'school', 'created_at']
    list_filter = ['school', 'created_at']
    search_fields = ['name']
    ordering = ['school', 'name']

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'created_at']
    search_fields = ['name', 'code']
    ordering = ['name']

@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'employee_id', 'school', 'created_at']
    list_filter = ['school', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'employee_id']
    ordering = ['-created_at']

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'admission_number', 'school', 'current_class', 'created_at']
    list_filter = ['school', 'current_class', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'admission_number']
    ordering = ['-created_at']

@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'relationship', 'occupation', 'created_at']
    list_filter = ['relationship', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'occupation']
    ordering = ['-created_at']

@admin.register(PrincipalProfile)
class PrincipalProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'employee_id', 'school', 'created_at']
    list_filter = ['school', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'employee_id']
    ordering = ['-created_at']
