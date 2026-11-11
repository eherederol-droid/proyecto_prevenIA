"""
Assessments — PosturalAssessment, JointAngle, Alert models
Core AI analysis logic
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class PosturalAssessment(models.Model):
    """A posture analysis session performed on an athlete"""
    GENERAL = 'general'
    SQUAT = 'squat'
    LUNGE = 'lunge'
    PUSH_UP = 'push_up'
    PLANK = 'plank'
    SIDE_PLANK = 'side_plank'
    BURPEE = 'burpee'
    JUMPING_JACK = 'jumping_jack'
    DEADLIFT = 'deadlift'
    GLUTE_BRIDGE = 'glute_bridge'
    CALF_RAISE = 'calf_raise'
    STEP_UP = 'step_up'
    MOUNTAIN_CLIMBER = 'mountain_climber'
    OVERHEAD_PRESS = 'overhead_press'
    BICEPS_CURL = 'biceps_curl'
    ROW = 'row'
    TRICEPS_DIP = 'triceps_dip'
    LATERAL_RAISE = 'lateral_raise'
    CRUNCH = 'crunch'
    JUMP_LANDING = 'jump_landing'
    ARM_RAISE = 'arm_raise'
    JOINT_MOBILITY = 'joint_mobility'
    EXERCISE_CHOICES = [
        (GENERAL, 'Postura general'),
        (SQUAT, 'Sentadilla'),
        (LUNGE, 'Zancada'),
        (PUSH_UP, 'Flexión de brazos'),
        (ARM_RAISE, 'Elevación de brazos'),
        (JOINT_MOBILITY, 'Movilidad articular'),
        (PLANK, 'Plancha'),
        (SIDE_PLANK, 'Plancha lateral'),
        (BURPEE, 'Burpee'),
        (JUMPING_JACK, 'Jumping jack'),
        (DEADLIFT, 'Peso muerto'),
        (GLUTE_BRIDGE, 'Puente de glúteos'),
        (CALF_RAISE, 'Elevación de pantorrillas'),
        (STEP_UP, 'Subida al cajón'),
        (MOUNTAIN_CLIMBER, 'Escaladores'),
        (OVERHEAD_PRESS, 'Press sobre la cabeza'),
        (BICEPS_CURL, 'Curl de bíceps'),
        (ROW, 'Remo'),
        (TRICEPS_DIP, 'Fondos de tríceps'),
        (LATERAL_RAISE, 'Elevación lateral de hombros'),
        (CRUNCH, 'Abdominales'),
        (JUMP_LANDING, 'Salto y aterrizaje'),
    ]

    FRONTAL = 'frontal'
    LATERAL = 'lateral'
    POSTERIOR = 'posterior'
    DYNAMIC = 'dynamic'
    VIEW_CHOICES = [
        (FRONTAL, 'Vista Frontal'),
        (LATERAL, 'Vista Lateral'),
        (POSTERIOR, 'Vista Posterior'),
        (DYNAMIC, 'Análisis en Movimiento'),
    ]

    PENDING = 'pending'
    ANALYZING = 'analyzing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    STATUS_CHOICES = [
        (PENDING, 'Pendiente'),
        (ANALYZING, 'Analizando'),
        (COMPLETED, 'Completado'),
        (FAILED, 'Fallido'),
    ]

    # Relations
    athlete = models.ForeignKey(
        'athletes.Athlete', on_delete=models.CASCADE,
        related_name='assessments', verbose_name='Atleta'
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='performed_assessments', verbose_name='Realizado por'
    )

    # Session info
    session_date = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de sesión')
    view_type = models.CharField(max_length=20, choices=VIEW_CHOICES, default=FRONTAL, verbose_name='Tipo de vista')
    exercise_type = models.CharField(
        max_length=20, choices=EXERCISE_CHOICES, default=GENERAL, verbose_name='Ejercicio'
    )
    exercise_feedback = models.JSONField(default=dict, blank=True, verbose_name='Evaluación de técnica')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING, verbose_name='Estado')
    notes = models.TextField(blank=True, verbose_name='Notas del profesional')

    # Input media
    image = models.ImageField(upload_to='assessments/images/', blank=True, null=True, verbose_name='Imagen capturada')
    video = models.FileField(upload_to='assessments/videos/', blank=True, null=True, verbose_name='Video capturado')
    image_s3_key = models.CharField(max_length=500, blank=True, verbose_name='Clave S3 imagen')

    # AI Results
    ai_model_version = models.CharField(max_length=50, blank=True, verbose_name='Versión del modelo IA')
    risk_score = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        verbose_name='Puntuación de riesgo IA'
    )
    risk_level = models.CharField(
        max_length=10, blank=True, verbose_name='Nivel de riesgo',
        choices=[('low','Bajo'),('medium','Medio'),('high','Alto'),('critical','Crítico')]
    )
    ai_confidence = models.FloatField(null=True, blank=True, verbose_name='Confianza del modelo (%)')
    detected_issues = models.JSONField(default=list, blank=True, verbose_name='Problemas detectados')
    recommendations = models.JSONField(default=list, blank=True, verbose_name='Recomendaciones IA')
    keypoints_data = models.JSONField(default=dict, blank=True, verbose_name='Keypoints MediaPipe')
    landmark_image_key = models.CharField(max_length=500, blank=True, verbose_name='Imagen con landmarks (S3)')

    # Biomechanical Session & Sports Analysis
    duration_seconds = models.IntegerField(default=0, verbose_name='Duración del análisis (segundos)')
    tracking_quality = models.FloatField(null=True, blank=True, verbose_name='Calidad del seguimiento (%)')
    biomechanical_events = models.JSONField(default=list, blank=True, verbose_name='Eventos y errores biomecánicos')
    exercise_thresholds = models.JSONField(default=dict, blank=True, verbose_name='Umbrales biomecánicos')

    # Medical & Sports Physician Review
    doctor_notes = models.TextField(blank=True, verbose_name='Observaciones médicas')
    preventive_recommendations = models.JSONField(default=dict, blank=True, verbose_name='Recomendaciones preventivas')
    is_reviewed_by_doctor = models.BooleanField(default=False, verbose_name='Revisado por médico deportivo')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_biomechanical_assessments', verbose_name='Revisado por'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de revisión médica')

    # Processing
    processing_time_ms = models.IntegerField(null=True, blank=True, verbose_name='Tiempo de procesamiento (ms)')
    lambda_request_id = models.CharField(max_length=100, blank=True, verbose_name='ID solicitud Lambda')
    error_message = models.TextField(blank=True, verbose_name='Mensaje de error')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Evaluación Postural'
        verbose_name_plural = 'Evaluaciones Posturales'
        ordering = ['-session_date']

    def __str__(self):
        return f'Eval #{self.pk} — {self.athlete.full_name} ({self.get_view_type_display()})'


class JointAngle(models.Model):
    """Individual joint angle measurement from an assessment"""
    KNEE_LEFT = 'knee_left'
    KNEE_RIGHT = 'knee_right'
    HIP_LEFT = 'hip_left'
    HIP_RIGHT = 'hip_right'
    SHOULDER_LEFT = 'shoulder_left'
    SHOULDER_RIGHT = 'shoulder_right'
    ELBOW_LEFT = 'elbow_left'
    ELBOW_RIGHT = 'elbow_right'
    ANKLE_LEFT = 'ankle_left'
    ANKLE_RIGHT = 'ankle_right'
    SPINE_LATERAL = 'spine_lateral'
    SPINE_SAGITTAL = 'spine_sagittal'
    PELVIS_TILT = 'pelvis_tilt'
    HEAD_TILT = 'head_tilt'

    JOINT_CHOICES = [
        (KNEE_LEFT, 'Rodilla Izquierda'),
        (KNEE_RIGHT, 'Rodilla Derecha'),
        (HIP_LEFT, 'Cadera Izquierda'),
        (HIP_RIGHT, 'Cadera Derecha'),
        (SHOULDER_LEFT, 'Hombro Izquierdo'),
        (SHOULDER_RIGHT, 'Hombro Derecho'),
        (ELBOW_LEFT, 'Codo Izquierdo'),
        (ELBOW_RIGHT, 'Codo Derecho'),
        (ANKLE_LEFT, 'Tobillo Izquierdo'),
        (ANKLE_RIGHT, 'Tobillo Derecho'),
        (SPINE_LATERAL, 'Columna (Lateral)'),
        (SPINE_SAGITTAL, 'Columna (Sagital)'),
        (PELVIS_TILT, 'Inclinación Pélvica'),
        (HEAD_TILT, 'Inclinación de Cabeza'),
    ]

    NORMAL_RANGES = {
        KNEE_LEFT: (165, 180),
        KNEE_RIGHT: (165, 180),
        HIP_LEFT: (170, 195),
        HIP_RIGHT: (170, 195),
        SHOULDER_LEFT: (155, 185),
        SHOULDER_RIGHT: (155, 185),
        ELBOW_LEFT: (150, 180),
        ELBOW_RIGHT: (150, 180),
        ANKLE_LEFT: (85, 100),
        ANKLE_RIGHT: (85, 100),
        SPINE_LATERAL: (0, 5),
    }

    assessment = models.ForeignKey(
        PosturalAssessment, on_delete=models.CASCADE,
        related_name='joint_angles', verbose_name='Evaluación'
    )
    joint = models.CharField(max_length=30, choices=JOINT_CHOICES, verbose_name='Articulación')
    angle_degrees = models.FloatField(verbose_name='Ángulo (grados)')
    is_within_normal = models.BooleanField(default=True, verbose_name='Dentro del rango normal')
    deviation_from_normal = models.FloatField(default=0.0, verbose_name='Desviación del rango normal')
    risk_contribution = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        verbose_name='Contribución al riesgo (%)'
    )
    raw_keypoints = models.JSONField(default=dict, blank=True, verbose_name='Keypoints crudos')

    class Meta:
        verbose_name = 'Ángulo Articular'
        verbose_name_plural = 'Ángulos Articulares'
        unique_together = [('assessment', 'joint')]

    def __str__(self):
        return f'{self.get_joint_display()}: {self.angle_degrees}°'

    def save(self, *args, **kwargs):
        """Auto-calculate if within normal range"""
        nrange = self.NORMAL_RANGES.get(self.joint)
        if nrange:
            self.is_within_normal = nrange[0] <= self.angle_degrees <= nrange[1]
            if self.angle_degrees < nrange[0]:
                self.deviation_from_normal = nrange[0] - self.angle_degrees
            elif self.angle_degrees > nrange[1]:
                self.deviation_from_normal = self.angle_degrees - nrange[1]
            else:
                self.deviation_from_normal = 0.0
        super().save(*args, **kwargs)


class Alert(models.Model):
    """AI-generated alert for a specific athlete"""
    POSTURE = 'posture'
    RISK = 'risk'
    PATTERN = 'pattern'
    APPOINTMENT = 'appointment'
    ALERT_TYPES = [
        (POSTURE, 'Alerta Postural'),
        (RISK, 'Riesgo de Lesión'),
        (PATTERN, 'Patrón Detectado'),
        (APPOINTMENT, 'Cita / Seguimiento'),
    ]

    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'
    SEVERITY_CHOICES = [
        (LOW, 'Baja'),
        (MEDIUM, 'Media'),
        (HIGH, 'Alta'),
        (CRITICAL, 'Crítica'),
    ]

    athlete = models.ForeignKey(
        'athletes.Athlete', on_delete=models.CASCADE,
        related_name='alerts', verbose_name='Atleta'
    )
    assessment = models.ForeignKey(
        PosturalAssessment, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='alerts', verbose_name='Evaluación relacionada'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Asignada a'
    )

    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES, verbose_name='Tipo de alerta')
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, verbose_name='Severidad')
    title = models.CharField(max_length=200, verbose_name='Título')
    description = models.TextField(verbose_name='Descripción')
    recommended_action = models.TextField(blank=True, verbose_name='Acción recomendada')

    is_read = models.BooleanField(default=False, verbose_name='Leída')
    is_resolved = models.BooleanField(default=False, verbose_name='Resuelta')
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='resolved_alerts'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.get_severity_display().upper()}] {self.title}'


class BiomechanicalEvent(models.Model):
    """Specific biomechanical error or observation captured during sports movement scanning"""
    SEVERITY_CHOICES = [
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('critical', 'Crítica'),
    ]

    assessment = models.ForeignKey(
        PosturalAssessment, on_delete=models.CASCADE,
        related_name='events', verbose_name='Evaluación'
    )
    error_name = models.CharField(max_length=150, verbose_name='Nombre del posible error')
    exercise_type = models.CharField(max_length=50, verbose_name='Ejercicio')
    timestamp_seconds = models.FloatField(default=0.0, verbose_name='Segundo en que ocurrió')
    joint = models.CharField(max_length=50, blank=True, verbose_name='Articulación involucrada')
    angle_degrees = models.FloatField(null=True, blank=True, verbose_name='Ángulo calculado')
    reference_range = models.CharField(max_length=80, blank=True, verbose_name='Valor de referencia')
    frequency = models.IntegerField(default=1, verbose_name='Frecuencia de aparición')
    confidence = models.FloatField(default=0.0, verbose_name='Nivel de confianza (%)')
    severity = models.CharField(max_length=20, default='medium', choices=SEVERITY_CHOICES, verbose_name='Severidad')
    observations = models.TextField(blank=True, verbose_name='Observaciones del evento')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Evento Biomecánico'
        verbose_name_plural = 'Eventos Biomecánicos'
        ordering = ['timestamp_seconds', 'created_at']

    def __str__(self):
        return f'{self.error_name} ({self.exercise_type}) @ {self.timestamp_seconds:.1f}s - {self.frequency}x'
