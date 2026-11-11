"""Celery tasks for async AI processing"""
from celery import shared_task
import logging

logger = logging.getLogger('prevenia')


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def analyze_assessment_async(self, assessment_id: int):
    """
    Async Celery task to run posture analysis.
    Retries up to 3 times on failure.
    """
    try:
        from assessments.models import PosturalAssessment
        from assessments.posture_analyzer import PostureAnalyzer
        from assessments.views import PosturalAssessmentViewSet

        assessment = PosturalAssessment.objects.get(pk=assessment_id)
        assessment.status = PosturalAssessment.ANALYZING
        assessment.save(update_fields=['status'])

        logger.info(f'Starting async analysis for assessment #{assessment_id}')

        viewset = PosturalAssessmentViewSet()
        result = viewset._run_analysis_sync(assessment)

        if result['success']:
            # Notify user via email (AWS SES)
            notify_assessment_complete.delay(assessment_id)
            logger.info(f'Assessment #{assessment_id} completed. Risk: {result["assessment"]["risk_level"]}')
        else:
            logger.error(f'Assessment #{assessment_id} failed: {result.get("error")}')

        return result

    except PosturalAssessment.DoesNotExist:
        logger.error(f'Assessment #{assessment_id} not found')
        raise
    except Exception as exc:
        logger.error(f'Error in analyze_assessment_async #{assessment_id}: {exc}')
        raise self.retry(exc=exc)


@shared_task
def notify_assessment_complete(assessment_id: int):
    """Send email notification when assessment is complete"""
    try:
        from assessments.models import PosturalAssessment
        from django.core.mail import send_mail
        from django.conf import settings

        assessment = PosturalAssessment.objects.select_related(
            'athlete', 'performed_by'
        ).get(pk=assessment_id)

        if assessment.performed_by and assessment.performed_by.email:
            subject = f'PrevenIA — Análisis completado: {assessment.athlete.full_name}'
            message = f"""
Su análisis postural ha sido completado.

Atleta: {assessment.athlete.full_name}
Riesgo detectado: {assessment.risk_level.upper()} ({assessment.risk_score:.1f}/100)
Fecha: {assessment.session_date.strftime('%d/%m/%Y %H:%M')}

Ingrese al sistema para ver el reporte completo.

PrevenIA — Sistema de Prevención de Lesiones Deportivas
            """.strip()

            send_mail(
                subject, message,
                settings.DEFAULT_FROM_EMAIL,
                [assessment.performed_by.email],
                fail_silently=True,
            )
    except Exception as e:
        logger.error(f'Error sending notification for assessment #{assessment_id}: {e}')


@shared_task
def weekly_risk_report():
    """
    Weekly scheduled task — generates and sends risk summary report.
    Triggered by Celery Beat every Monday at 8 AM.
    """
    from athletes.models import Athlete
    from django.db.models import Count, Avg
    from django.core.mail import send_mail
    from django.conf import settings
    from users.models import User

    stats = Athlete.objects.filter(is_active=True).aggregate(
        total=Count('id'),
        high_risk=Count('id', filter=__import__('django.db.models', fromlist=['Q']).Q(current_risk_level__in=['high', 'critical'])),
        avg_risk=Avg('risk_score'),
    )

    # Send to all medical staff
    medicos = User.objects.filter(role='medico', is_active=True).values_list('email', flat=True)
    if medicos:
        send_mail(
            f'PrevenIA — Reporte Semanal de Riesgo',
            f'Atletas activos: {stats["total"]}\nRiesgo alto/crítico: {stats["high_risk"]}\nRiesgo promedio: {stats["avg_risk"]:.1f}',
            settings.DEFAULT_FROM_EMAIL,
            list(medicos),
            fail_silently=True,
        )
    logger.info(f'Weekly report sent to {len(medicos)} professionals')
