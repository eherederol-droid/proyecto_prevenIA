"""Reports Views"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from .models import Report
from .serializers import ReportSerializer


class ReportViewSet(viewsets.ModelViewSet):
    """
    Generate and retrieve reports.
    POST /api/v1/reports/generate/ — Generate a new report
    GET  /api/v1/reports/{id}/download/ — Download PDF
    GET  /api/v1/reports/dashboard-stats/ — Dashboard summary stats
    """
    queryset = Report.objects.select_related('generated_by', 'athlete')
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(generated_by=self.request.user)

    @action(detail=False, methods=['get'], url_path='dashboard-stats')
    def dashboard_stats(self, request):
        """Full dashboard statistics for home page"""
        from athletes.models import Athlete
        from assessments.models import PosturalAssessment, Alert

        today = timezone.now().date()
        month_start = today.replace(day=1)

        # Athletes
        athletes_qs = Athlete.objects.filter(is_active=True)
        total_athletes = athletes_qs.count()
        risk_distribution = dict(
            athletes_qs.values('current_risk_level')
            .annotate(count=Count('id'))
            .values_list('current_risk_level', 'count')
        )

        # Assessments
        assessments_today = PosturalAssessment.objects.filter(
            session_date__date=today
        ).count()
        assessments_this_month = PosturalAssessment.objects.filter(
            session_date__date__gte=month_start
        ).count()

        # Body zone frequency this month
        zone_freq = {}
        from assessments.models import JointAngle
        for ja in JointAngle.objects.filter(
            assessment__session_date__date__gte=month_start
        ).values('joint').annotate(count=Count('id')):
            zone_freq[ja['joint']] = ja['count']

        # Active alerts
        active_alerts = Alert.objects.filter(is_resolved=False).count()
        critical_alerts = Alert.objects.filter(is_resolved=False, severity='critical').count()
        recent_alerts = Alert.objects.filter(is_resolved=False).order_by('-created_at')[:5]
        from assessments.serializers import AlertSerializer
        recent_alerts_data = AlertSerializer(recent_alerts, many=True).data

        # Average risk score
        avg_risk = athletes_qs.aggregate(avg=Avg('risk_score'))['avg'] or 0

        return Response({
            'athletes': {
                'total': total_athletes,
                'risk_distribution': risk_distribution,
                'average_risk_score': round(avg_risk, 2),
            },
            'assessments': {
                'today': assessments_today,
                'this_month': assessments_this_month,
            },
            'alerts': {
                'active': active_alerts,
                'critical': critical_alerts,
                'recent': recent_alerts_data,
            },
            'zone_frequency': zone_freq,
            'period': {
                'today': today.isoformat(),
                'month_start': month_start.isoformat(),
            }
        })

    @action(detail=False, methods=['post'], url_path='generate')
    def generate(self, request):
        """Generate a new report asynchronously"""
        report_type = request.data.get('report_type', Report.INDIVIDUAL)
        athlete_id = request.data.get('athlete_id')
        date_from = request.data.get('date_from')
        date_to = request.data.get('date_to')

        # Gather data snapshot
        data = self._gather_report_data(report_type, athlete_id, date_from, date_to)

        titles = {
            Report.INDIVIDUAL: f'Reporte Individual',
            Report.STATISTICAL: 'Reporte Estadístico del Equipo',
            Report.PREVENTION: 'Reporte de Prevención de Lesiones',
        }

        report = Report.objects.create(
            report_type=report_type,
            title=titles.get(report_type, 'Reporte'),
            generated_by=request.user,
            athlete_id=athlete_id,
            date_from=date_from,
            date_to=date_to,
            status=Report.READY,
            data_snapshot=data,
        )

        serializer = ReportSerializer(report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _gather_report_data(self, report_type, athlete_id, date_from, date_to):
        from athletes.models import Athlete
        from assessments.models import PosturalAssessment

        data = {}
        qs = PosturalAssessment.objects.filter(status='completed')

        if date_from:
            qs = qs.filter(session_date__date__gte=date_from)
        if date_to:
            qs = qs.filter(session_date__date__lte=date_to)

        if report_type == Report.INDIVIDUAL and athlete_id:
            try:
                athlete = Athlete.objects.get(pk=athlete_id)
                evals = qs.filter(athlete=athlete).order_by('-session_date')
                data = {
                    'athlete': {
                        'name': athlete.full_name,
                        'sport': athlete.sport,
                        'age': athlete.age,
                        'risk_level': athlete.current_risk_level,
                        'risk_score': athlete.risk_score,
                    },
                    'assessments': list(evals.values(
                        'id', 'session_date', 'risk_score', 'risk_level',
                        'view_type', 'detected_issues', 'recommendations'
                    )[:10]),
                    'total_evaluations': evals.count(),
                }
            except Athlete.DoesNotExist:
                pass

        elif report_type == Report.STATISTICAL:
            from athletes.models import Athlete as AthleteModel
            athletes = AthleteModel.objects.filter(is_active=True)
            data = {
                'total_athletes': athletes.count(),
                'risk_distribution': dict(
                    athletes.values('current_risk_level')
                    .annotate(count=Count('id'))
                    .values_list('current_risk_level', 'count')
                ),
                'total_assessments': qs.count(),
                'avg_risk_score': qs.aggregate(avg=Avg('risk_score'))['avg'],
            }

        elif report_type == Report.PREVENTION:
            data = {
                'total_assessments': qs.count(),
                'high_risk_detected': qs.filter(risk_level__in=['high', 'critical']).count(),
                'avg_confidence': qs.aggregate(avg=Avg('ai_confidence'))['avg'],
            }

        return data

    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, pk=None):
        report = self.get_object()
        if report.file_url:
            return Response({'download_url': report.file_url})
        return Response({'data': report.data_snapshot, 'message': 'Datos del reporte disponibles.'})
