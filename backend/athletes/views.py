"""Athletes API Views"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as filters
from .models import Athlete, InjuryRecord
from .serializers import AthleteSerializer, AthleteListSerializer, InjuryRecordSerializer


class AthleteFilter(filters.FilterSet):
    sport = filters.CharFilter(lookup_expr='icontains')
    risk_level = filters.CharFilter(field_name='current_risk_level')
    min_risk = filters.NumberFilter(field_name='risk_score', lookup_expr='gte')
    max_risk = filters.NumberFilter(field_name='risk_score', lookup_expr='lte')
    name = filters.CharFilter(method='filter_name')

    def filter_name(self, qs, name, value):
        return qs.filter(first_name__icontains=value) | qs.filter(last_name__icontains=value)

    class Meta:
        model = Athlete
        fields = ['sport', 'risk_level', 'gender', 'is_active']


class AthleteViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for athletes.
    GET  /api/v1/athletes/              — List all athletes
    POST /api/v1/athletes/              — Create athlete
    GET  /api/v1/athletes/{id}/         — Athlete detail
    GET  /api/v1/athletes/{id}/assessments/ — Athlete assessment history
    GET  /api/v1/athletes/{id}/alerts/  — Active alerts for athlete
    GET  /api/v1/athletes/risk-summary/ — Risk distribution stats
    """
    queryset = Athlete.objects.select_related('created_by', 'assigned_to').prefetch_related('assessments', 'alerts')
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = AthleteFilter
    search_fields = ['first_name', 'last_name', 'email', 'sport', 'team']
    ordering_fields = ['last_name', 'risk_score', 'created_at']
    ordering = ['last_name']

    def get_serializer_class(self):
        if self.action == 'list':
            return AthleteListSerializer
        return AthleteSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'], url_path='assessments')
    def assessments(self, request, pk=None):
        athlete = self.get_object()
        from assessments.models import PosturalAssessment
        from assessments.serializers import PosturalAssessmentSerializer
        evals = PosturalAssessment.objects.filter(athlete=athlete).order_by('-session_date')
        serializer = PosturalAssessmentSerializer(evals, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='alerts')
    def alerts(self, request, pk=None):
        athlete = self.get_object()
        from assessments.models import Alert
        from assessments.serializers import AlertSerializer
        active_alerts = Alert.objects.filter(athlete=athlete, is_resolved=False).order_by('-created_at')
        serializer = AlertSerializer(active_alerts, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='risk-summary')
    def risk_summary(self, request):
        """Return risk distribution stats for dashboard"""
        from django.db.models import Count, Avg
        qs = Athlete.objects.filter(is_active=True)
        stats = qs.values('current_risk_level').annotate(
            count=Count('id'),
            avg_risk=Avg('risk_score')
        )
        total = qs.count()
        return Response({
            'total': total,
            'distribution': {s['current_risk_level']: s['count'] for s in stats},
            'average_risk': qs.aggregate(avg=Avg('risk_score'))['avg'],
        })


class InjuryRecordViewSet(viewsets.ModelViewSet):
    """CRUD for athlete injury records"""
    queryset = InjuryRecord.objects.select_related('athlete', 'recorded_by')
    serializer_class = InjuryRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['athlete', 'injury_type', 'is_recurring']

    def perform_create(self, serializer):
        serializer.save(recorded_by=self.request.user)
