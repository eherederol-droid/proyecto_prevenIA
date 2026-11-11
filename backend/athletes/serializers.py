"""Serializers for Athletes app"""
from rest_framework import serializers
from .models import Athlete, InjuryRecord


class InjuryRecordSerializer(serializers.ModelSerializer):
    injury_type_display = serializers.CharField(source='get_injury_type_display', read_only=True)

    class Meta:
        model = InjuryRecord
        fields = '__all__'
        read_only_fields = ['id', 'recorded_by', 'created_at']


class AthleteListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    initials = serializers.SerializerMethodField()
    risk_level_display = serializers.CharField(source='get_current_risk_level_display', read_only=True)
    assessments_count = serializers.SerializerMethodField()
    last_assessment_date = serializers.SerializerMethodField()

    class Meta:
        model = Athlete
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'initials',
            'age', 'gender', 'sport', 'team',
            'current_risk_level', 'risk_level_display', 'risk_score',
            'assessments_count', 'last_assessment_date',
            'is_active', 'created_at',
        ]

    def get_full_name(self, obj): return obj.full_name
    def get_age(self, obj): return obj.age
    def get_initials(self, obj): return obj.initials
    def get_assessments_count(self, obj): return obj.assessments.count()
    def get_last_assessment_date(self, obj):
        last = obj.assessments.order_by('-session_date').first()
        return last.session_date if last else None


class AthleteSerializer(serializers.ModelSerializer):
    """Full serializer with all fields"""
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    bmi = serializers.SerializerMethodField()
    initials = serializers.SerializerMethodField()
    risk_level_display = serializers.CharField(source='get_current_risk_level_display', read_only=True)
    injury_records = InjuryRecordSerializer(many=True, read_only=True)
    active_alerts_count = serializers.SerializerMethodField()

    class Meta:
        model = Athlete
        fields = '__all__'
        read_only_fields = ['id', 'created_by', 'risk_score', 'current_risk_level', 'created_at', 'updated_at']

    def get_full_name(self, obj): return obj.full_name
    def get_age(self, obj): return obj.age
    def get_bmi(self, obj): return obj.bmi
    def get_initials(self, obj): return obj.initials
    def get_active_alerts_count(self, obj):
        return obj.alerts.filter(is_resolved=False).count()
