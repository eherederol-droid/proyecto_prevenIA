"""Assessment API Views"""
import logging
import math
from collections import Counter
from functools import lru_cache
from io import BytesIO
from threading import Lock
from xml.sax.saxutils import escape
from django.core.files.base import ContentFile
from django.http import HttpResponse
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import transaction
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from django.utils import timezone

from .models import PosturalAssessment, JointAngle, Alert, BiomechanicalEvent
from .serializers import (
    PosturalAssessmentSerializer,
    PosturalAssessmentCreateSerializer,
    JointAngleSerializer,
    AlertSerializer,
    BiomechanicalEventSerializer,
)
from .posture_analyzer import PostureAnalyzer
from .tasks import analyze_assessment_async

logger = logging.getLogger('prevenia')

_live_preview_analysis_lock = Lock()
MAX_EXERCISE_SESSION_FRAMES = 30
MAX_EXERCISE_SESSION_BYTES = 12 * 1024 * 1024


def _aggregate_exercise_results(results, exercise_type, duration_seconds, analyzer):
    frame_count = len(results)
    if not frame_count:
        raise ValueError('No se pudieron analizar fotogramas de la sesión.')

    angle_samples = {}
    for result in results:
        for joint, angle in result['joint_angles'].items():
            angle_samples.setdefault(joint, []).append(angle)
    average_angles = {
        joint: round(sum(values) / len(values), 2)
        for joint, values in angle_samples.items()
    }
    asymmetry_samples = {}
    for result in results:
        for joint, value in result.get('asymmetries', {}).items():
            asymmetry_samples.setdefault(joint, []).append(value)
    average_asymmetries = {
        joint: round(sum(values) / len(values), 2)
        for joint, values in asymmetry_samples.items()
    }

    issue_counts = Counter()
    issue_details = {}
    severity_rank = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
    for result in results:
        frame_issues = {}
        for issue in result.get('detected_issues', []):
            key = (issue.get('type', ''), issue.get('zone', ''), issue.get('joint', ''))
            frame_issues[key] = issue
        for key, issue in frame_issues.items():
            issue_counts[key] += 1
            current = issue_details.get(key)
            if not current or severity_rank.get(issue.get('severity', 'low'), 0) > severity_rank.get(current.get('severity', 'low'), 0):
                issue_details[key] = issue

    minimum_occurrences = max(1, math.ceil(frame_count * 0.2))
    detected_issues = []
    for key, occurrences in issue_counts.most_common():
        if occurrences < minimum_occurrences:
            continue
        issue = dict(issue_details[key])
        issue['occurrence_count'] = occurrences
        issue['occurrence_percentage'] = round(occurrences / frame_count * 100)
        detected_issues.append(issue)

    risk_scores = [result['risk_score'] for result in results if result.get('risk_score') is not None]
    average_risk = round(sum(risk_scores) / len(risk_scores), 2) if risk_scores else 0.0
    peak_risk = round(max(risk_scores), 2) if risk_scores else 0.0
    risk_level = analyzer._risk_level_from_score(average_risk)
    exercise_display = dict(PosturalAssessment.EXERCISE_CHOICES).get(exercise_type, exercise_type)

    feedback_samples = [
        result['exercise_feedback']
        for result in results
        if result.get('exercise_feedback')
    ]
    cue_counts = Counter(
        cue
        for feedback in feedback_samples
        for cue in feedback.get('cues', [])
        if cue and cue != feedback.get('summary')
    )
    exercise_issues = []
    feedback_issue_counts = Counter()
    feedback_issue_details = {}
    for feedback in feedback_samples:
        for issue in feedback.get('issues', []):
            key = (issue.get('type', ''), issue.get('zone', ''))
            feedback_issue_counts[key] += 1
            current = feedback_issue_details.get(key)
            if not current or len(issue.get('description', '')) > len(current.get('description', '')):
                feedback_issue_details[key] = issue
    for key, occurrences in feedback_issue_counts.most_common():
        if occurrences < minimum_occurrences:
            continue
        issue = dict(feedback_issue_details[key])
        issue['occurrence_count'] = occurrences
        issue['occurrence_percentage'] = round(occurrences / frame_count * 100)
        exercise_issues.append(issue)

    warning_frames = sum(
        feedback.get('status') == 'warning'
        for feedback in feedback_samples
    )
    has_repeated_warnings = bool(exercise_issues) or (
        feedback_samples and warning_frames / len(feedback_samples) >= 0.2
    )
    feedback = {
        'exercise_type': exercise_type,
        'exercise_display': exercise_display,
        'status': 'warning' if has_repeated_warnings else 'ok',
        'summary': f'Sesión evaluada con {frame_count} fotogramas durante {duration_seconds} s.',
        'cues': [cue for cue, _count in cue_counts.most_common(4)],
        'issues': exercise_issues,
        'session_statistics': {
            'frames_analyzed': frame_count,
            'duration_seconds': duration_seconds,
            'average_risk_score': average_risk,
            'peak_risk_score': peak_risk,
            'repeated_findings': len(detected_issues),
        },
    }

    recommendations = analyzer._generate_recommendations(detected_issues, risk_level)
    for cue, _count in cue_counts.most_common(4):
        if cue not in recommendations:
            recommendations.append(cue)

    confidence_samples = [
        result['ai_confidence']
        for result in results
        if result.get('ai_confidence') is not None
    ]
    confidence = (
        round(sum(confidence_samples) / len(confidence_samples), 2)
        if confidence_samples else None
    )
    representative = results[frame_count // 2]
    breakdown_samples = {}
    for result in results:
        for key, value in result.get('risk_breakdown', {}).items():
            breakdown_samples.setdefault(key, []).append(value)

    return {
        'success': True,
        'ai_model_version': representative.get('ai_model_version', ''),
        'joint_angles': average_angles,
        'asymmetries': average_asymmetries,
        'risk_score': average_risk,
        'risk_level': risk_level,
        'ai_confidence': confidence,
        'detected_issues': detected_issues,
        'recommendations': recommendations,
        'exercise_feedback': feedback,
        'risk_breakdown': {
            key: round(sum(values) / len(values), 2)
            for key, values in breakdown_samples.items()
        },
        'keypoints_data': representative.get('keypoints_data', {}),
        'processing_time_ms': sum(result.get('processing_time_ms', 0) for result in results),
    }


@lru_cache(maxsize=1)
def _get_live_preview_analyzer() -> PostureAnalyzer:
    return PostureAnalyzer()


class PosturalAssessmentViewSet(viewsets.ModelViewSet):
    """
    CRUD + AI analysis for posture assessments.

    POST /api/v1/assessments/           — Create assessment (without analysis)
    POST /api/v1/assessments/{id}/analyze/  — Trigger AI analysis
    POST /api/v1/assessments/analyze-image/ — Upload image & analyze immediately
    GET  /api/v1/assessments/{id}/pdf/  — Download PDF report
    """

    queryset = PosturalAssessment.objects.select_related('athlete', 'performed_by').prefetch_related('joint_angles', 'alerts')
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ['athlete', 'view_type', 'status', 'risk_level']
    search_fields = ['athlete__first_name', 'athlete__last_name', 'notes']
    ordering_fields = ['session_date', 'risk_score']

    def get_serializer_class(self):
        if self.action == 'create':
            return PosturalAssessmentCreateSerializer
        return PosturalAssessmentSerializer

    def perform_create(self, serializer):
        serializer.save(performed_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='analyze')
    def analyze(self, request, pk=None):
        """Trigger AI analysis on an existing assessment with an uploaded image."""
        assessment = self.get_object()

        if not assessment.image:
            return Response(
                {'error': 'La evaluación no tiene imagen adjunta para analizar.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Run synchronously in dev, async (Celery) in production
        if settings.DEBUG or not settings.CELERY_BROKER_URL:
            result = self._run_analysis_sync(assessment)
            return Response(result, status=status.HTTP_200_OK)
        else:
            task = analyze_assessment_async.delay(assessment.id)
            return Response({
                'message': 'Análisis iniciado. Recibirás una notificación al completarse.',
                'task_id': task.id,
                'assessment_id': assessment.id,
            }, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['post'], url_path='analyze-image')
    def analyze_image(self, request):
        """Upload an image and get AI analysis immediately (single-step)."""
        image_file = request.FILES.get('image')
        athlete_id = request.data.get('athlete_id')

        if not image_file:
            return Response({'error': 'Se requiere una imagen.'}, status=status.HTTP_400_BAD_REQUEST)
        if not athlete_id:
            return Response({'error': 'Se requiere athlete_id.'}, status=status.HTTP_400_BAD_REQUEST)

        exercise_type = request.data.get('exercise_type', PosturalAssessment.GENERAL)
        view_type = request.data.get('view_type', PosturalAssessment.FRONTAL)
        if exercise_type not in dict(PosturalAssessment.EXERCISE_CHOICES):
            return Response({'error': 'Selecciona un ejercicio compatible.'}, status=status.HTTP_400_BAD_REQUEST)
        if view_type not in dict(PosturalAssessment.VIEW_CHOICES):
            return Response({'error': 'Selecciona una vista compatible.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from athletes.models import Athlete
            athlete = Athlete.objects.get(pk=athlete_id)
        except Athlete.DoesNotExist:
            return Response({'error': 'Atleta no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        # Create assessment
        with transaction.atomic():
            assessment = PosturalAssessment.objects.create(
                athlete=athlete,
                performed_by=request.user,
                view_type=view_type,
                exercise_type=exercise_type,
                status=PosturalAssessment.ANALYZING,
                image=image_file,
            )

        # Run analysis
        result = self._run_analysis_sync(assessment)
        return Response(result, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='analyze-exercise-session')
    def analyze_exercise_session(self, request):
        """Analyze a bounded set of camera frames collected during one exercise."""
        frames = request.FILES.getlist('images')
        if not 3 <= len(frames) <= MAX_EXERCISE_SESSION_FRAMES:
            return Response(
                {'error': f'La sesión debe incluir entre 3 y {MAX_EXERCISE_SESSION_FRAMES} fotogramas.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        total_size = sum(frame.size for frame in frames)
        if total_size > MAX_EXERCISE_SESSION_BYTES:
            return Response(
                {'error': 'La sesión supera el límite de 12 MB.'},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        athlete_id = request.data.get('athlete_id')
        exercise_type = request.data.get('exercise_type', PosturalAssessment.GENERAL)
        view_type = request.data.get('view_type', PosturalAssessment.FRONTAL)
        try:
            duration_seconds = int(request.data.get('duration_seconds', 0))
        except (TypeError, ValueError):
            duration_seconds = 0
        if not athlete_id:
            return Response({'error': 'Se requiere athlete_id.'}, status=status.HTTP_400_BAD_REQUEST)
        if exercise_type not in dict(PosturalAssessment.EXERCISE_CHOICES):
            return Response({'error': 'Selecciona un ejercicio compatible.'}, status=status.HTTP_400_BAD_REQUEST)
        if view_type not in dict(PosturalAssessment.VIEW_CHOICES):
            return Response({'error': 'Selecciona una vista compatible.'}, status=status.HTTP_400_BAD_REQUEST)
        if not 1 <= duration_seconds <= 900:
            return Response(
                {'error': 'La duración de la sesión debe estar entre 1 y 900 segundos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from athletes.models import Athlete
        try:
            athlete = Athlete.objects.get(pk=athlete_id)
        except (Athlete.DoesNotExist, TypeError, ValueError):
            return Response({'error': 'Atleta no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        frame_bytes = [frame.read() for frame in frames]
        with _live_preview_analysis_lock:
            analyzer = _get_live_preview_analyzer()
            analyzed_frames = []
            for content in frame_bytes:
                result = analyzer.analyze_bytes(
                    content,
                    exercise_type=exercise_type,
                    view_type=view_type,
                )
                if result['success']:
                    analyzed_frames.append((content, result))
            results = [result for _content, result in analyzed_frames]
            if len(results) < 3:
                return Response(
                    {'error': 'No se detectó una postura estable en al menos 3 fotogramas. Repite el ejercicio mostrando el cuerpo completo.'},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            result = _aggregate_exercise_results(
                results,
                exercise_type,
                duration_seconds,
                analyzer,
            )

        representative_image = ContentFile(
            analyzed_frames[len(analyzed_frames) // 2][0],
            name='exercise-session.jpg',
        )
        with transaction.atomic():
            assessment = PosturalAssessment.objects.create(
                athlete=athlete,
                performed_by=request.user,
                view_type=view_type,
                exercise_type=exercise_type,
                status=PosturalAssessment.ANALYZING,
                image=representative_image,
            )
        return Response(self._save_analysis_result(assessment, result), status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='save-biomechanical-session')
    def save_biomechanical_session(self, request):
        """Save a real-time biomechanical analysis session with all detected events."""
        import json
        data = request.data
        athlete_id = data.get('athlete_id')
        if not athlete_id:
            return Response({'error': 'Se requiere athlete_id.'}, status=status.HTTP_400_BAD_REQUEST)

        from athletes.models import Athlete
        try:
            athlete = Athlete.objects.get(pk=athlete_id)
        except (Athlete.DoesNotExist, TypeError, ValueError):
            return Response({'error': 'Atleta no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        exercise_type = data.get('exercise_type', PosturalAssessment.GENERAL)
        view_type = data.get('view_type', PosturalAssessment.FRONTAL)
        image_file = request.FILES.get('image')

        def _parse_field(val, default):
            if isinstance(val, (dict, list)):
                return val
            if isinstance(val, str) and val.strip():
                try:
                    return json.loads(val)
                except Exception:
                    return default
            return default

        joint_angles_raw = _parse_field(data.get('joint_angles'), {})
        biomechanical_events_raw = _parse_field(data.get('biomechanical_events'), [])
        detected_issues_raw = _parse_field(data.get('detected_issues'), [])
        recommendations_raw = _parse_field(data.get('recommendations'), [])
        preventive_recommendations_raw = _parse_field(data.get('preventive_recommendations'), {})
        exercise_feedback_raw = _parse_field(data.get('exercise_feedback'), {})
        exercise_thresholds_raw = _parse_field(data.get('exercise_thresholds'), {})
        keypoints_data_raw = _parse_field(data.get('keypoints_data'), {})

        try:
            duration_seconds = int(data.get('duration_seconds', 0))
        except (TypeError, ValueError):
            duration_seconds = 0

        try:
            tracking_quality = float(data.get('tracking_quality', 0.0))
        except (TypeError, ValueError):
            tracking_quality = None

        try:
            risk_score = float(data.get('risk_score', 0.0))
        except (TypeError, ValueError):
            risk_score = 0.0

        risk_level = data.get('risk_level') or _get_live_preview_analyzer()._risk_level_from_score(risk_score)
        doctor_notes = data.get('doctor_notes', '')

        with transaction.atomic():
            assessment = PosturalAssessment.objects.create(
                athlete=athlete,
                performed_by=request.user,
                view_type=view_type,
                exercise_type=exercise_type,
                status=PosturalAssessment.COMPLETED,
                duration_seconds=duration_seconds,
                tracking_quality=tracking_quality,
                risk_score=round(risk_score, 2),
                risk_level=risk_level,
                ai_confidence=tracking_quality or 92.0,
                detected_issues=detected_issues_raw,
                recommendations=recommendations_raw,
                biomechanical_events=biomechanical_events_raw,
                doctor_notes=doctor_notes,
                preventive_recommendations=preventive_recommendations_raw,
                exercise_feedback=exercise_feedback_raw,
                exercise_thresholds=exercise_thresholds_raw,
                keypoints_data=keypoints_data_raw,
                ai_model_version=f'PrevenIA-BioMechanics',
                image=image_file,
            )

            # Save joint angles
            angles_to_create = []
            if isinstance(joint_angles_raw, dict):
                angle_items = joint_angles_raw.items()
            elif isinstance(joint_angles_raw, list):
                angle_items = [
                    (item.get('joint'), item.get('angle_degrees', 0))
                    for item in joint_angles_raw if isinstance(item, dict) and item.get('joint')
                ]
            else:
                angle_items = []

            for joint_key, angle_val in angle_items:
                if not joint_key or angle_val is None:
                    continue
                try:
                    angle_val = float(angle_val)
                except (ValueError, TypeError):
                    continue
                normal_range = JointAngle.NORMAL_RANGES.get(joint_key)
                is_within_normal = not normal_range or normal_range[0] <= angle_val <= normal_range[1]
                deviation = 0.0
                if normal_range and angle_val < normal_range[0]:
                    deviation = normal_range[0] - angle_val
                elif normal_range and angle_val > normal_range[1]:
                    deviation = angle_val - normal_range[1]
                angles_to_create.append(JointAngle(
                    assessment=assessment,
                    joint=joint_key,
                    angle_degrees=round(angle_val, 2),
                    is_within_normal=is_within_normal,
                    deviation_from_normal=round(deviation, 2),
                ))
            if angles_to_create:
                JointAngle.objects.bulk_create(angles_to_create, ignore_conflicts=True)

            # Save BiomechanicalEvent rows
            events_to_create = []
            for ev in biomechanical_events_raw:
                if not isinstance(ev, dict) or not ev.get('error_name'):
                    continue
                events_to_create.append(BiomechanicalEvent(
                    assessment=assessment,
                    error_name=ev.get('error_name', 'Error biomecánico'),
                    exercise_type=ev.get('exercise_type', exercise_type),
                    timestamp_seconds=float(ev.get('timestamp_seconds', 0.0)),
                    joint=ev.get('joint', ''),
                    angle_degrees=float(ev.get('angle_degrees')) if ev.get('angle_degrees') is not None else None,
                    reference_range=str(ev.get('reference_range', '')),
                    frequency=int(ev.get('frequency', 1)),
                    confidence=float(ev.get('confidence', 90.0)),
                    severity=ev.get('severity', 'medium'),
                    observations=ev.get('observations', ''),
                ))
            if events_to_create:
                BiomechanicalEvent.objects.bulk_create(events_to_create)

            # Update athlete risk metrics
            athlete.risk_score = round(risk_score, 2)
            athlete.current_risk_level = risk_level
            athlete.save(update_fields=['risk_score', 'current_risk_level'])

            # Create alerts for notable findings
            self._create_alerts(assessment, {
                'detected_issues': detected_issues_raw,
                'joint_angles': {ja.joint: ja.angle_degrees for ja in angles_to_create},
                'recommendations': recommendations_raw,
            })

        serializer = PosturalAssessmentSerializer(assessment)
        return Response({'success': True, 'assessment': serializer.data}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='save-doctor-review')
    def save_doctor_review(self, request, pk=None):
        """Update sports physician observations, preventive recommendations and approval status."""
        assessment = self.get_object()
        data = request.data
        doctor_notes = data.get('doctor_notes')
        preventive_recommendations = data.get('preventive_recommendations')
        is_reviewed = data.get('is_reviewed_by_doctor')

        if doctor_notes is not None:
            assessment.doctor_notes = str(doctor_notes).strip()
        if preventive_recommendations is not None:
            if isinstance(preventive_recommendations, str):
                import json
                try:
                    assessment.preventive_recommendations = json.loads(preventive_recommendations)
                except Exception:
                    assessment.preventive_recommendations = {}
            elif isinstance(preventive_recommendations, dict):
                assessment.preventive_recommendations = preventive_recommendations

        if is_reviewed is not None:
            assessment.is_reviewed_by_doctor = bool(is_reviewed)
            if assessment.is_reviewed_by_doctor:
                assessment.reviewed_by = request.user
                assessment.reviewed_at = timezone.now()
            else:
                assessment.reviewed_by = None
                assessment.reviewed_at = None

        assessment.save()
        serializer = PosturalAssessmentSerializer(assessment)
        return Response({'success': True, 'assessment': serializer.data})

    @action(detail=False, methods=['get'], url_path='athlete-history')
    def athlete_history(self, request):
        """Retrieve previous assessments of an athlete for comparison."""
        athlete_id = request.query_params.get('athlete_id')
        if not athlete_id:
            return Response({'error': 'Se requiere athlete_id'}, status=status.HTTP_400_BAD_REQUEST)
        assessments = PosturalAssessment.objects.filter(
            athlete_id=athlete_id
        ).select_related('performed_by', 'reviewed_by').prefetch_related('events', 'joint_angles').order_by('-session_date')[:25]
        serializer = PosturalAssessmentSerializer(assessments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='pose-preview')
    def pose_preview(self, request):
        """Analyze a camera frame for live feedback without saving an assessment."""
        image_file = request.FILES.get('image')
        if not image_file:
            return Response({'error': 'Se requiere una imagen.'}, status=status.HTTP_400_BAD_REQUEST)
        if image_file.size > 5 * 1024 * 1024:
            return Response(
                {'error': 'El fotograma de cámara supera el límite de 5 MB.'},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        exercise_type = request.data.get('exercise_type', PosturalAssessment.GENERAL)
        view_type = request.data.get('view_type', PosturalAssessment.FRONTAL)
        if exercise_type not in dict(PosturalAssessment.EXERCISE_CHOICES):
            return Response({'error': 'Selecciona un ejercicio compatible.'}, status=status.HTTP_400_BAD_REQUEST)
        if view_type not in dict(PosturalAssessment.VIEW_CHOICES):
            return Response({'error': 'Selecciona una vista compatible.'}, status=status.HTTP_400_BAD_REQUEST)

        with _live_preview_analysis_lock:
            result = _get_live_preview_analyzer().analyze_bytes(
                image_file.read(),
                exercise_type=exercise_type,
                view_type=view_type,
            )
        if not result['success']:
            return Response({'success': False, 'error': result['error']}, status=status.HTTP_200_OK)

        joint_angles = []
        for joint, angle in result['joint_angles'].items():
            normal_range = JointAngle.NORMAL_RANGES.get(joint)
            is_within_normal = not normal_range or normal_range[0] <= angle <= normal_range[1]
            deviation = 0.0
            if normal_range and angle < normal_range[0]:
                deviation = normal_range[0] - angle
            elif normal_range and angle > normal_range[1]:
                deviation = angle - normal_range[1]
            joint_angles.append({
                'joint': joint,
                'joint_display': dict(JointAngle.JOINT_CHOICES).get(joint, joint),
                'angle_degrees': angle,
                'is_within_normal': is_within_normal,
                'deviation_from_normal': deviation,
                'normal_range': normal_range,
            })
        return Response({
            'success': True,
            'keypoints_data': result['keypoints_data'],
            'joint_angles': joint_angles,
            'detected_issues': result['detected_issues'],
            'exercise_feedback': result['exercise_feedback'],
            'risk_score': result['risk_score'],
            'risk_level': result['risk_level'],
        })

    def _run_analysis_sync(self, assessment: PosturalAssessment) -> dict:
        """Run MediaPipe analysis synchronously"""
        image_path = assessment.image.path

        with PostureAnalyzer() as analyzer:
            result = analyzer.analyze_image(
                image_path,
                exercise_type=assessment.exercise_type,
                view_type=assessment.view_type,
            )

        return self._save_analysis_result(assessment, result)

    def _save_analysis_result(self, assessment: PosturalAssessment, result: dict) -> dict:
        """Persist a single-frame or aggregated exercise analysis."""
        if not result['success']:
            assessment.status = PosturalAssessment.FAILED
            assessment.error_message = result.get('error', '')
            assessment.save(update_fields=['status', 'error_message'])
            return {'success': False, 'error': result['error']}

        # Save results
        with transaction.atomic():
            assessment.status = PosturalAssessment.COMPLETED
            assessment.ai_model_version = result['ai_model_version']
            assessment.risk_score = result['risk_score']
            assessment.risk_level = result['risk_level']
            assessment.ai_confidence = result['ai_confidence']
            assessment.detected_issues = result['detected_issues']
            assessment.recommendations = result['recommendations']
            assessment.exercise_feedback = result['exercise_feedback'] or {}
            assessment.keypoints_data = result['keypoints_data']
            assessment.processing_time_ms = result['processing_time_ms']
            assessment.save()

            # Save joint angles
            JointAngle.objects.filter(assessment=assessment).delete()
            angles_to_create = []
            for joint_key, angle_val in result['joint_angles'].items():
                normal_range = JointAngle.NORMAL_RANGES.get(joint_key)
                is_within_normal = not normal_range or normal_range[0] <= angle_val <= normal_range[1]
                deviation = 0.0
                if normal_range and angle_val < normal_range[0]:
                    deviation = normal_range[0] - angle_val
                elif normal_range and angle_val > normal_range[1]:
                    deviation = angle_val - normal_range[1]
                angles_to_create.append(JointAngle(
                    assessment=assessment,
                    joint=joint_key,
                    angle_degrees=angle_val,
                    is_within_normal=is_within_normal,
                    deviation_from_normal=deviation,
                ))
            JointAngle.objects.bulk_create(angles_to_create, ignore_conflicts=True)

            # Update athlete risk
            athlete = assessment.athlete
            athlete.risk_score = result['risk_score']
            athlete.current_risk_level = result['risk_level']
            athlete.save(update_fields=['risk_score', 'current_risk_level'])

            # Create alerts for detected posture deviations.
            self._create_alerts(assessment, result)

        serializer = PosturalAssessmentSerializer(assessment)
        return {'success': True, 'assessment': serializer.data}

    def _create_alerts(self, assessment, result):
        """Create alerts for notable findings and every measured range deviation."""
        covered_joints = set()
        for issue in result.get('detected_issues', []):
            if issue['severity'] in ('medium', 'high', 'critical'):
                Alert.objects.create(
                    athlete=assessment.athlete,
                    assessment=assessment,
                    alert_type=Alert.RISK,
                    severity=issue['severity'],
                    title=f"{issue['zone']} — {assessment.athlete.full_name}",
                    description=issue['description'],
                    recommended_action='; '.join(result.get('recommendations', [])[:3]),
                )
                issue_type = issue.get('type')
                if issue_type == 'valgus_knee':
                    side = 'left' if 'izquierda' in issue.get('zone', '').lower() else 'right'
                    covered_joints.add(f'knee_{side}')
                elif issue_type == 'hip_asymmetry':
                    covered_joints.update(('hip_left', 'hip_right'))
                elif issue_type == 'shoulder_asymmetry':
                    covered_joints.update(('shoulder_left', 'shoulder_right'))
                elif issue_type == 'lateral_deviation':
                    covered_joints.add('spine_lateral')
                elif issue_type == 'joint_deviation':
                    covered_joints.add(issue.get('joint'))

        joint_labels = dict(JointAngle.JOINT_CHOICES)
        for joint, angle in result.get('joint_angles', {}).items():
            normal_range = JointAngle.NORMAL_RANGES.get(joint)
            if not normal_range or joint in covered_joints:
                continue
            if normal_range[0] <= angle <= normal_range[1]:
                continue
            label = joint_labels.get(joint, joint)
            if angle < normal_range[0]:
                deviation = normal_range[0] - angle
            else:
                deviation = angle - normal_range[1]
            Alert.objects.create(
                athlete=assessment.athlete,
                assessment=assessment,
                alert_type=Alert.POSTURE,
                severity=Alert.MEDIUM,
                title=f'Desviación postural — {assessment.athlete.full_name}',
                description=(
                    f'{label}: {angle:.1f}°, fuera del rango de '
                    f'{normal_range[0]}°–{normal_range[1]}° por {deviation:.1f}°.'
                ),
                recommended_action='Revisar la postura y repetir la evaluación.',
            )

    @action(detail=True, methods=['get'], url_path='pdf')
    def pdf_report(self, request, pk=None):
        """Generate and download a PDF report for an assessment."""
        assessment = self.get_object()
        pdf_file = _build_assessment_pdf(assessment)
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="prevenia-evaluacion-{assessment.pk}.pdf"'
        return response


def _build_assessment_pdf(assessment) -> bytes:
    """Render a comprehensive biomechanical and sports posture assessment report."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        title=f'Evaluación Biomecánica #{assessment.pk} — {assessment.athlete.full_name}',
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='PreveniaTitle',
        parent=styles['Title'],
        textColor=colors.HexColor('#1E3A8A'),
        alignment=0,
        fontSize=18,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name='PreveniaSubtitle',
        parent=styles['Normal'],
        textColor=colors.HexColor('#4B5563'),
        fontSize=10,
        spaceAfter=12,
    ))
    styles.add(ParagraphStyle(name='PreveniaSmall', parent=styles['BodyText'], fontSize=8, leading=10))
    styles.add(ParagraphStyle(name='PreveniaTableHeader', parent=styles['BodyText'], fontSize=8, leading=10, fontName='Helvetica-Bold', textColor=colors.white))
    body = styles['BodyText']

    story = [
        Paragraph('PrevenIA — Informe de Análisis Biomecánico Deportivo', styles['PreveniaTitle']),
        Paragraph('Evaluación neuromuscular, cinemática articular y prevención de lesiones', styles['PreveniaSubtitle']),
        Spacer(1, 6),
    ]

    # Resumen Info Box
    duration_str = f"{assessment.duration_seconds} seg" if assessment.duration_seconds else "—"
    quality_str = f"{assessment.tracking_quality:.1f}%" if assessment.tracking_quality else (f"{assessment.ai_confidence:.1f}%" if assessment.ai_confidence else "—")
    reviewed_status = "Revisado por Especialista Médico" if assessment.is_reviewed_by_doctor else "Pendiente de validación médica"

    info_data = [
        [
            Paragraph(f'<b>Atleta:</b> {escape(assessment.athlete.full_name)}', body),
            Paragraph(f'<b>Deporte:</b> {escape(str(assessment.athlete.sport))}', body),
            Paragraph(f'<b>Fecha:</b> {escape(assessment.session_date.strftime("%d/%m/%Y %H:%M"))}', body),
        ],
        [
            Paragraph(f'<b>Ejercicio:</b> {escape(assessment.get_exercise_type_display())}', body),
            Paragraph(f'<b>Duración:</b> {duration_str}', body),
            Paragraph(f'<b>Calidad Tracking:</b> {quality_str}', body),
        ],
        [
            Paragraph(f'<b>Nivel de Riesgo:</b> {escape(assessment.get_risk_level_display() or "Bajo")} ({assessment.risk_score or 0}/100)', body),
            Paragraph(f'<b>Evaluador:</b> {escape(assessment.performed_by.get_full_name() if assessment.performed_by else "Sistema IA")}', body),
            Paragraph(f'<b>Estado Médico:</b> {reviewed_status}', body),
        ]
    ]
    info_table = Table(info_data, colWidths=[2.4 * inch, 2.3 * inch, 2.4 * inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.extend((info_table, Spacer(1, 10)))

    # Errores Biomecánicos Identificados
    events = list(assessment.events.all())
    story.append(Paragraph('Errores Biomecánicos Identificados', styles['Heading2']))
    if events or (assessment.biomechanical_events):
        event_rows = [['Posible Error Biomecánico', 'Articulación', 'Ángulo', 'Referencia', 'Frecuencia', 'Severidad']]
        ev_list = events if events else assessment.biomechanical_events
        for ev in ev_list:
            if isinstance(ev, BiomechanicalEvent):
                name = ev.error_name
                joint = ev.joint or "General"
                angle = f"{ev.angle_degrees:.1f}°" if ev.angle_degrees is not None else "—"
                ref = ev.reference_range or "Normal"
                freq = f"{ev.frequency}x"
                sev = ev.get_severity_display()
            else:
                name = ev.get('error_name', 'Desviación')
                joint = ev.get('joint', 'General')
                angle = f"{ev.get('angle_degrees'):.1f}°" if ev.get('angle_degrees') is not None else "—"
                ref = ev.get('reference_range', 'Normal')
                freq = f"{ev.get('frequency', 1)}x"
                sev = ev.get('severity', 'media').capitalize()

            event_rows.append([
                Paragraph(escape(str(name)), styles['PreveniaSmall']),
                Paragraph(escape(str(joint)), styles['PreveniaSmall']),
                angle,
                ref,
                freq,
                sev,
            ])
        events_table = Table(event_rows, colWidths=[2.3 * inch, 1.3 * inch, 0.8 * inch, 1.2 * inch, 0.7 * inch, 0.8 * inch], repeatRows=1)
        events_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#DC2626')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#FECACA')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FFF1F2')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.extend((events_table, Spacer(1, 10)))
    else:
        story.append(Paragraph('No se registraron errores biomecánicos repetitivos durante la ejecución.', body))
        story.append(Spacer(1, 8))

    # Ángulos Articulares Medidos
    story.append(Paragraph('Cinemática y Ángulos Articulares', styles['Heading2']))
    angle_rows = [['Articulación Evaluada', 'Ángulo Medido', 'Rango Normal de Referencia', 'Estado']]
    for angle in assessment.joint_angles.all():
        normal_range = JointAngle.NORMAL_RANGES.get(angle.joint)
        range_text = f'{normal_range[0]}°–{normal_range[1]}°' if normal_range else 'Referencial'
        angle_rows.append([
            Paragraph(escape(angle.get_joint_display()), styles['PreveniaSmall']),
            f'{angle.angle_degrees:.1f}°',
            range_text,
            'Dentro de Rango' if angle.is_within_normal else f'Desviación ({angle.deviation_from_normal:.1f}°)',
        ])
    if len(angle_rows) == 1:
        angle_rows.append(['Sin mediciones articulares registradas', '', '', ''])
    angles_table = Table(angle_rows, colWidths=[2.6 * inch, 1.2 * inch, 1.8 * inch, 1.5 * inch], repeatRows=1)
    angles_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563EB')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#D1D5DB')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.extend((angles_table, Spacer(1, 10)))

    # Observaciones Médicas Deportivas
    story.append(Paragraph('Observaciones del Médico / Fisioterapeuta Deportivo', styles['Heading2']))
    notes_text = assessment.doctor_notes or assessment.notes or 'Sin observaciones registradas por el médico tratante.'
    story.append(Paragraph(escape(notes_text), body))
    story.append(Spacer(1, 8))

    # Recomendaciones Preventivas por Categorías
    story.append(Paragraph('Plan Preventivo y Recomendaciones del Profesional', styles['Heading2']))
    prev_recs = assessment.preventive_recommendations or {}
    categories = [
        ('technical_correction', 'Corrección Técnica'),
        ('mobility', 'Movilidad Articular'),
        ('strength', 'Fortalecimiento Muscular'),
        ('stability', 'Estabilidad y Propiocepción'),
        ('flexibility', 'Flexibilidad'),
        ('follow_up', 'Seguimiento y Control Deportivo'),
    ]
    has_any_cat = False
    for cat_key, cat_name in categories:
        val = prev_recs.get(cat_key)
        if val:
            has_any_cat = True
            story.append(Paragraph(f'<b>• {cat_name}:</b> {escape(str(val))}', body))
            story.append(Spacer(1, 2))

    if not has_any_cat and assessment.recommendations:
        for item in assessment.recommendations:
            story.append(Paragraph(f'• {escape(str(item))}', body))
            story.append(Spacer(1, 2))
    elif not has_any_cat:
        story.append(Paragraph('Plan preventivo estándar sugerido según el patrón biomecánico analizado.', body))

    story.append(Spacer(1, 14))

    # Medical Approval & Signoff
    if assessment.is_reviewed_by_doctor and assessment.reviewed_by:
        reviewer_name = assessment.reviewed_by.get_full_name() or assessment.reviewed_by.email
        reviewed_date = assessment.reviewed_at.strftime("%d/%m/%Y %H:%M") if assessment.reviewed_at else ""
        story.append(Paragraph(f'<i>Evaluación validada por: <b>{escape(reviewer_name)}</b> el {reviewed_date}</i>', styles['PreveniaSmall']))
    else:
        story.append(Paragraph('<i>Informe preliminar asistido por visión artificial. Requiere confirmación y firma médica deportiva.</i>', styles['PreveniaSmall']))

    document.build(story)
    return buffer.getvalue()


class AlertViewSet(viewsets.ModelViewSet):
    """CRUD for AI-generated alerts"""
    queryset = Alert.objects.select_related('athlete', 'assessment', 'assigned_to')
    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['severity', 'is_read', 'is_resolved', 'alert_type', 'athlete']
    ordering_fields = ['created_at', 'severity']

    def get_queryset(self):
        qs = super().get_queryset()
        # Entrenadores y médicos see only their assigned alerts
        user = self.request.user
        if user.role == 'atleta':
            qs = qs.filter(athlete__email=user.email)
        return qs

    @action(detail=True, methods=['post'], url_path='resolve')
    def resolve(self, request, pk=None):
        alert = self.get_object()
        from django.utils import timezone
        alert.is_resolved = True
        alert.resolved_by = request.user
        alert.resolved_at = timezone.now()
        alert.resolution_notes = request.data.get('notes', '')
        alert.save()
        return Response({'message': 'Alerta marcada como resuelta.'})

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        Alert.objects.filter(is_read=False).update(is_read=True)
        return Response({'message': 'Todas las alertas marcadas como leídas.'})
