"""Athletes app models"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Athlete(models.Model):
    """Athlete profile with sport and biometric data"""
    MALE = 'M'
    FEMALE = 'F'
    OTHER = 'O'
    GENDER_CHOICES = [(MALE, 'Masculino'), (FEMALE, 'Femenino'), (OTHER, 'Otro')]

    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'
    RISK_CHOICES = [
        (LOW, 'Bajo'),
        (MEDIUM, 'Medio'),
        (HIGH, 'Alto'),
        (CRITICAL, 'Crítico'),
    ]

    # Managed by
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_athletes', verbose_name='Registrado por'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_athletes', verbose_name='Asignado a'
    )

    # Personal info
    first_name = models.CharField(max_length=80, verbose_name='Nombre')
    last_name = models.CharField(max_length=80, verbose_name='Apellido')
    email = models.EmailField(unique=True, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True, verbose_name='Fecha de nacimiento')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    photo = models.ImageField(upload_to='athletes/photos/', blank=True, null=True)

    # Biometrics
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Peso (kg)')
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Altura (cm)')

    # Sport
    sport = models.CharField(max_length=80, verbose_name='Deporte')
    team = models.CharField(max_length=100, blank=True, verbose_name='Equipo')
    position = models.CharField(max_length=50, blank=True, verbose_name='Posición')
    years_practicing = models.PositiveSmallIntegerField(default=0, verbose_name='Años de práctica')
    training_frequency = models.CharField(max_length=50, blank=True, verbose_name='Frecuencia de entrenamiento')

    # Medical history
    previous_injuries = models.TextField(blank=True, verbose_name='Lesiones previas')
    surgeries = models.TextField(blank=True, verbose_name='Cirugías')
    chronic_conditions = models.TextField(blank=True, verbose_name='Condiciones crónicas')
    current_medications = models.TextField(blank=True, verbose_name='Medicamentos actuales')
    allergies = models.TextField(blank=True, verbose_name='Alergias')

    # Risk assessment (updated by AI)
    current_risk_level = models.CharField(
        max_length=10, choices=RISK_CHOICES, default=LOW, verbose_name='Nivel de riesgo actual'
    )
    risk_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        verbose_name='Puntuación de riesgo'
    )

    # Status
    is_active = models.BooleanField(default=True, verbose_name='Activo')
    notes = models.TextField(blank=True, verbose_name='Notas generales')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Atleta'
        verbose_name_plural = 'Atletas'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f'{self.first_name} {self.last_name} — {self.sport}'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    @property
    def age(self):
        if self.date_of_birth:
            from django.utils import timezone
            today = timezone.now().date()
            d = today - self.date_of_birth
            return int(d.days / 365.25)
        return None

    @property
    def bmi(self):
        if self.weight_kg and self.height_cm and self.height_cm > 0:
            h = float(self.height_cm) / 100
            return round(float(self.weight_kg) / (h ** 2), 2)
        return None

    @property
    def initials(self):
        return (self.first_name[:1] + self.last_name[:1]).upper()


class InjuryRecord(models.Model):
    """Record of past or current injuries"""
    STRAIN = 'strain'
    SPRAIN = 'sprain'
    FRACTURE = 'fracture'
    CONTUSION = 'contusion'
    TENDINITIS = 'tendinitis'
    DISLOCATION = 'dislocation'
    OTHER = 'other'

    INJURY_TYPES = [
        (STRAIN, 'Desgarro / Distensión'),
        (SPRAIN, 'Esguince'),
        (FRACTURE, 'Fractura'),
        (CONTUSION, 'Contusión'),
        (TENDINITIS, 'Tendinitis'),
        (DISLOCATION, 'Luxación'),
        (OTHER, 'Otro'),
    ]

    athlete = models.ForeignKey(Athlete, on_delete=models.CASCADE, related_name='injury_records')
    injury_type = models.CharField(max_length=20, choices=INJURY_TYPES)
    body_part = models.CharField(max_length=80, verbose_name='Zona corporal')
    description = models.TextField(verbose_name='Descripción')
    injury_date = models.DateField(verbose_name='Fecha de lesión')
    recovery_date = models.DateField(null=True, blank=True, verbose_name='Fecha de recuperación')
    was_surgical = models.BooleanField(default=False, verbose_name='Requirió cirugía')
    is_recurring = models.BooleanField(default=False, verbose_name='Lesión recurrente')
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Lesión'
        verbose_name_plural = 'Lesiones'
        ordering = ['-injury_date']

    def __str__(self):
        return f'{self.athlete.full_name} — {self.get_injury_type_display()} ({self.body_part})'
