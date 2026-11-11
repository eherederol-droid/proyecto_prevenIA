"""Custom User model for PrevenIA"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El correo electrónico es requerido')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.ADMIN)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model with role-based access control.
    Roles: admin, medico (physician/physio), entrenador (coach), atleta (athlete)
    """
    ADMIN = 'admin'
    MEDICO = 'medico'
    ENTRENADOR = 'entrenador'
    ATLETA = 'atleta'

    ROLE_CHOICES = [
        (ADMIN, 'Administrador'),
        (MEDICO, 'Médico / Fisioterapeuta'),
        (ENTRENADOR, 'Entrenador'),
        (ATLETA, 'Atleta'),
    ]

    email = models.EmailField(unique=True, verbose_name='Correo electrónico')
    first_name = models.CharField(max_length=80, verbose_name='Nombre')
    last_name = models.CharField(max_length=80, verbose_name='Apellido')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=MEDICO, verbose_name='Rol')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, verbose_name='Teléfono')
    institution = models.CharField(max_length=150, blank=True, verbose_name='Institución')
    specialty = models.CharField(max_length=100, blank=True, verbose_name='Especialidad')
    license_number = models.CharField(max_length=50, blank=True, verbose_name='Número de cédula')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)
    notification_preferences = models.JSONField(default=dict, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f'{self.get_full_name()} ({self.get_role_display()})'

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def get_short_name(self):
        return self.first_name

    @property
    def is_medico(self):
        return self.role == self.MEDICO

    @property
    def is_entrenador(self):
        return self.role == self.ENTRENADOR

    @property
    def is_atleta(self):
        return self.role == self.ATLETA

    @property
    def initials(self):
        parts = [self.first_name[:1], self.last_name[:1]]
        return ''.join(p.upper() for p in parts if p)
