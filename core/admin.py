from django.contrib import admin
from .models import User, School, Class, Subject, TeacherProfile, StudentProfile, ParentProfile, PrincipalProfile

admin.site.register(User)
admin.site.register(School)
admin.site.register(Class)
admin.site.register(Subject)
admin.site.register(TeacherProfile)
admin.site.register(StudentProfile)
admin.site.register(ParentProfile)
admin.site.register(PrincipalProfile)