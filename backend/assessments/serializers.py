"""Serializers for Assessments app"""
from rest_framework import serializers
from .models import PosturalAssessment, JointAngle, Alert, BiomechanicalEvent


class JointAngleSerializer(serializers.ModelSerializer):
    joint_display = serializers.CharField(source='get_joint_display', read_only=True)
    normal_range = serializers.SerializerMethodField()

    class Meta:
        model = JointAngle
        fields = [
            'id', 'joint', 'joint_display', 'angle_degrees',
            'is_within_normal', 'deviation_from_normal',
            'risk_contribution', 'normal_range',
        ]

    def get_normal_range(self, obj):
        return JointAngle.NORMAL_RANGES.get(obj.joint)


class BiomechanicalEventSerializer(serializers.ModelSerializer):
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)

    class Meta:
        model = BiomechanicalEvent
        fields = [
            'id', 'error_name', 'exercise_type', 'timestamp_seconds',
            'joint', 'angle_degrees', 'reference_range', 'frequency',
            'confidence', 'severity', 'severity_display', 'observations', 'created_at',
        ]


class PosturalAssessmentSerializer(serializers.ModelSerializer):
    athlete_name = serializers.CharField(source='athlete.full_name', read_only=True)
    athlete_sport = serializers.CharField(source='athlete.sport', read_only=True)
    performed_by_name = serializers.CharField(source='performed_by.get_full_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True, default=None)
    view_type_display = serializers.CharField(source='get_view_type_display', read_only=True)
    exercise_display = serializers.CharField(source='get_exercise_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    risk_level_display = serializers.SerializerMethodField()
    joint_angles = JointAngleSerializer(many=True, read_only=True)
    events = BiomechanicalEventSerializer(many=True, read_only=True)
    alerts_count = serializers.SerializerMethodField()

    class Meta:
        model = PosturalAssessment
        fields = [
            'id', 'athlete', 'athlete_name', 'athlete_sport',
            'performed_by', 'performed_by_name',
            'session_date', 'view_type', 'view_type_display',
            'exercise_type', 'exercise_display', 'exercise_feedback',
            'status', 'status_display', 'notes',
            'image', 'video', 'landmark_image_key',
            'ai_model_version', 'risk_score', 'risk_level', 'risk_level_display',
            'ai_confidence', 'detected_issues', 'recommendations', 'keypoints_data',
            'duration_seconds', 'tracking_quality', 'biomechanical_events', 'exercise_thresholds',
            'doctor_notes', 'preventive_recommendations', 'is_reviewed_by_doctor',
            'reviewed_by', 'reviewed_by_name', 'reviewed_at',
            'processing_time_ms', 'joint_angles', 'events', 'alerts_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'session_date', 'status', 'ai_model_version',
            'risk_score', 'risk_level', 'ai_confidence', 'exercise_feedback',
            'detected_issues', 'recommendations', 'keypoints_data',
            'processing_time_ms', 'created_at', 'updated_at',
        ]

    def get_risk_level_display(self, obj):
        mapping = {'low': 'Bajo', 'medium': 'Medio', 'high': 'Alto', 'critical': 'Crítico'}
        return mapping.get(obj.risk_level, obj.risk_level)

    def get_alerts_count(self, obj):
        return obj.alerts.filter(is_resolved=False).count()


class PosturalAssessmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PosturalAssessment
        fields = ['athlete', 'view_type', 'exercise_type', 'notes', 'image', 'video']


class AlertSerializer(serializers.ModelSerializer):
    athlete_name = serializers.CharField(source='athlete.full_name', read_only=True)
    athlete_sport = serializers.CharField(source='athlete.sport', read_only=True)
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True, default=None)

    class Meta:
        model = Alert
        fields = [
            'id', 'athlete', 'athlete_name', 'athlete_sport',
            'assessment', 'assigned_to', 'assigned_to_name',
            'alert_type', 'alert_type_display',
            'severity', 'severity_display',
            'title', 'description', 'recommended_action',
            'is_read', 'is_resolved', 'resolved_at', 'resolution_notes',
            'created_at', 'notified_at',
        ]
        read_only_fields = ['id', 'created_at', 'resolved_at']
