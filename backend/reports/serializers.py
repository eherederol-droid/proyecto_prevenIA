"""Reports serializer and URL routing"""
from rest_framework import serializers
from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    generated_by_name = serializers.CharField(source='generated_by.get_full_name', read_only=True)
    athlete_name = serializers.CharField(source='athlete.full_name', read_only=True, default=None)
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Report
        fields = [
            'id', 'report_type', 'report_type_display', 'title',
            'generated_by', 'generated_by_name',
            'athlete', 'athlete_name',
            'date_from', 'date_to',
            'status', 'status_display',
            'file_url', 'data_snapshot',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'generated_by', 'status', 'file_url', 'created_at', 'updated_at']
