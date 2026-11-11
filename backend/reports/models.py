"""Reports app models and views"""
from django.db import models
from django.conf import settings


class Report(models.Model):
    INDIVIDUAL = 'individual'
    STATISTICAL = 'statistical'
    PREVENTION = 'prevention'
    REPORT_TYPES = [
        (INDIVIDUAL, 'Reporte Individual'),
        (STATISTICAL, 'Reporte Estadístico'),
        (PREVENTION, 'Reporte de Prevención'),
    ]

    PENDING = 'pending'
    GENERATING = 'generating'
    READY = 'ready'
    FAILED = 'failed'
    STATUS_CHOICES = [
        (PENDING, 'Pendiente'),
        (GENERATING, 'Generando'),
        (READY, 'Listo'),
        (FAILED, 'Fallido'),
    ]

    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    title = models.CharField(max_length=200)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='reports'
    )
    athlete = models.ForeignKey(
        'athletes.Athlete', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reports', verbose_name='Atleta (para reportes individuales)'
    )
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    file_key = models.CharField(max_length=500, blank=True, verbose_name='Clave S3 del archivo PDF')
    file_url = models.URLField(blank=True, verbose_name='URL del archivo')
    data_snapshot = models.JSONField(default=dict, blank=True, verbose_name='Snapshot de datos')
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Reporte'
        verbose_name_plural = 'Reportes'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_report_type_display()} — {self.title}'
