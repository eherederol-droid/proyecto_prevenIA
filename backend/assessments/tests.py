from types import SimpleNamespace

import numpy as np
from django.test import SimpleTestCase, TestCase

from .models import PosturalAssessment
from .posture_analyzer import PostureAnalyzer, PoseLandmark
from .views import _aggregate_exercise_results


class ExerciseTechniqueTests(SimpleTestCase):
    def make_keypoints(self, **overrides):
        points = {
            name: {'x': 0.5, 'y': 0.5, 'visibility': 0.95}
            for name in (
                'LEFT_HIP', 'RIGHT_HIP', 'LEFT_KNEE', 'RIGHT_KNEE',
                'LEFT_ANKLE', 'RIGHT_ANKLE', 'LEFT_SHOULDER', 'RIGHT_SHOULDER',
                'LEFT_ELBOW', 'RIGHT_ELBOW', 'LEFT_WRIST', 'RIGHT_WRIST',
            )
        }
        points.update(overrides)
        return points

    def test_general_posture_does_not_apply_exercise_rules(self):
        feedback = PostureAnalyzer.evaluate_exercise(
            'general', {}, {}, image_width=640, image_height=480, view_type='frontal'
        )
        self.assertIsNone(feedback)

    def test_every_catalog_exercise_has_a_neutral_setup_state(self):
        exercise_types = {
            exercise_type for exercise_type, _label in PosturalAssessment.EXERCISE_CHOICES
            if exercise_type != 'general'
        }
        self.assertEqual(len(exercise_types), len(PosturalAssessment.EXERCISE_CHOICES) - 1)
        for exercise_type in exercise_types:
            with self.subTest(exercise_type=exercise_type):
                feedback = PostureAnalyzer.evaluate_exercise(
                    exercise_type,
                    {},
                    {},
                    image_width=640,
                    image_height=480,
                    view_type='frontal',
                )
                self.assertEqual(feedback['exercise_type'], exercise_type)
                self.assertEqual(feedback['status'], 'neutral')

    def test_plank_reports_visible_loss_of_body_alignment(self):
        keypoints = self.make_keypoints(
            LEFT_SHOULDER={'x': 0.2, 'y': 0.3, 'visibility': 0.95},
            LEFT_HIP={'x': 0.5, 'y': 0.5, 'visibility': 0.95},
            LEFT_ANKLE={'x': 0.8, 'y': 0.3, 'visibility': 0.95},
            RIGHT_SHOULDER={'x': 0.22, 'y': 0.3, 'visibility': 0.95},
            RIGHT_HIP={'x': 0.52, 'y': 0.5, 'visibility': 0.95},
            RIGHT_ANKLE={'x': 0.82, 'y': 0.3, 'visibility': 0.95},
        )
        feedback = PostureAnalyzer.evaluate_exercise(
            'plank',
            keypoints,
            {},
            image_width=640,
            image_height=480,
            view_type='lateral',
        )
        self.assertEqual(feedback['status'], 'warning')
        self.assertEqual(feedback['issues'][0]['zone'], 'Alineación corporal')

    def test_overhead_press_reports_asymmetric_arm_position(self):
        keypoints = self.make_keypoints(
            LEFT_SHOULDER={'x': 0.4, 'y': 0.3, 'visibility': 0.95},
            RIGHT_SHOULDER={'x': 0.6, 'y': 0.3, 'visibility': 0.95},
            LEFT_WRIST={'x': 0.4, 'y': 0.1, 'visibility': 0.95},
            RIGHT_WRIST={'x': 0.6, 'y': 0.4, 'visibility': 0.95},
        )
        feedback = PostureAnalyzer.evaluate_exercise(
            'overhead_press',
            keypoints,
            {},
            image_width=640,
            image_height=480,
            view_type='frontal',
        )
        self.assertEqual(feedback['status'], 'warning')
        self.assertEqual(feedback['issues'][0]['zone'], 'Hombros')

    def test_squat_reports_front_view_knee_collapse(self):
        keypoints = self.make_keypoints(
            LEFT_HIP={'x': 0.4, 'y': 0.4, 'visibility': 0.95},
            RIGHT_HIP={'x': 0.6, 'y': 0.4, 'visibility': 0.95},
            LEFT_KNEE={'x': 0.46, 'y': 0.6, 'visibility': 0.95},
            RIGHT_KNEE={'x': 0.55, 'y': 0.6, 'visibility': 0.95},
            LEFT_ANKLE={'x': 0.38, 'y': 0.8, 'visibility': 0.95},
            RIGHT_ANKLE={'x': 0.62, 'y': 0.8, 'visibility': 0.95},
        )
        feedback = PostureAnalyzer.evaluate_exercise(
            'squat',
            keypoints,
            {'knee_left': 100, 'knee_right': 100},
            image_width=640,
            image_height=480,
            view_type='frontal',
        )
        self.assertEqual(feedback['status'], 'warning')
        self.assertTrue(any('hacia dentro' in issue['description'] for issue in feedback['issues']))
        self.assertIn('LEFT_KNEE', feedback['issues'][0]['landmarks'])

    def test_push_up_reports_loss_of_body_alignment(self):
        keypoints = self.make_keypoints(
            LEFT_SHOULDER={'x': 0.25, 'y': 0.3, 'visibility': 0.95},
            LEFT_HIP={'x': 0.5, 'y': 0.8, 'visibility': 0.95},
            LEFT_ANKLE={'x': 0.75, 'y': 0.3, 'visibility': 0.95},
            RIGHT_SHOULDER={'x': 0.27, 'y': 0.3, 'visibility': 0.95},
            RIGHT_HIP={'x': 0.52, 'y': 0.8, 'visibility': 0.95},
            RIGHT_ANKLE={'x': 0.77, 'y': 0.3, 'visibility': 0.95},
        )
        feedback = PostureAnalyzer.evaluate_exercise(
            'push_up',
            keypoints,
            {'elbow_left': 100, 'elbow_right': 105},
            image_width=640,
            image_height=480,
            view_type='lateral',
        )
        self.assertEqual(feedback['status'], 'warning')
        self.assertTrue(any(issue['zone'] == 'Alineación corporal' for issue in feedback['issues']))

    def test_upright_pose_is_not_misclassified_as_a_push_up(self):
        feedback = PostureAnalyzer.evaluate_exercise(
            'push_up',
            self.make_keypoints(),
            {'elbow_left': 30, 'elbow_right': 35},
            image_width=640,
            image_height=480,
            view_type='lateral',
        )
        self.assertEqual(feedback['status'], 'neutral')
        self.assertEqual(feedback['issues'], [])

    def test_analysis_keypoints_use_landmark_names_for_skeleton_connections(self):
        landmarks = [
            SimpleNamespace(
                x=0.25 + (index % 6) * 0.1,
                y=0.1 + (index // 6) * 0.15,
                z=0.0,
                visibility=0.95,
            )
            for index in range(len(PoseLandmark))
        ]
        analyzer = object.__new__(PostureAnalyzer)
        analyzer.ai_version = 'test'
        analyzer.pose = SimpleNamespace(
            process=lambda _image: SimpleNamespace(
                pose_landmarks=SimpleNamespace(landmark=landmarks)
            )
        )

        result = analyzer._analyze_array(
            np.zeros((480, 640, 3), dtype=np.uint8),
            start_time=0,
        )

        self.assertTrue(result['success'])
        self.assertEqual(len(result['keypoints_data']), len(PoseLandmark))
        self.assertIn('LEFT_SHOULDER', result['keypoints_data'])
        self.assertIn('RIGHT_ANKLE', result['keypoints_data'])
        self.assertNotIn('11', result['keypoints_data'])

    def test_lunge_reports_unbalanced_knee_flexion(self):
        feedback = PostureAnalyzer.evaluate_exercise(
            'lunge',
            self.make_keypoints(),
            {'knee_left': 95, 'knee_right': 130},
            image_width=640,
            image_height=480,
            view_type='lateral',
        )
        self.assertEqual(feedback['status'], 'warning')
        self.assertTrue(any('diferencia marcada' in issue['description'] for issue in feedback['issues']))


class ExerciseSessionAggregationTests(SimpleTestCase):
    def test_session_statistics_average_angles_and_keep_recurrent_findings(self):
        analyzer = SimpleNamespace(
            _risk_level_from_score=lambda score: 'high' if score >= 70 else 'low',
            _generate_recommendations=lambda issues, risk: ['Revisar técnica'] if issues else ['Mantener rutina'],
        )
        results = [
            {
                'joint_angles': {'knee_left': 150, 'hip_left': 175},
                'risk_score': 60,
                'risk_level': 'medium',
                'ai_confidence': 80,
                'detected_issues': [{
                    'type': 'valgus_knee', 'zone': 'Rodilla izquierda',
                    'severity': 'high', 'description': 'Valgo repetido',
                }],
                'exercise_feedback': {
                    'status': 'warning',
                    'cues': ['Alinear la rodilla'],
                    'issues': [{'type': 'exercise_form', 'zone': 'Rodilla', 'description': 'Se desplaza'}],
                },
                'keypoints_data': {'LEFT_KNEE': {'x': 0.4, 'y': 0.6, 'z': 0, 'visibility': 0.9}},
                'risk_breakdown': {'knee_left': 40},
                'ai_model_version': 'test',
                'processing_time_ms': 100,
            },
            {
                'joint_angles': {'knee_left': 130, 'hip_left': 185},
                'risk_score': 80,
                'risk_level': 'high',
                'ai_confidence': 90,
                'detected_issues': [{
                    'type': 'valgus_knee', 'zone': 'Rodilla izquierda',
                    'severity': 'critical', 'description': 'Valgo persistente',
                }],
                'exercise_feedback': {
                    'status': 'warning',
                    'cues': ['Alinear la rodilla'],
                    'issues': [{'type': 'exercise_form', 'zone': 'Rodilla', 'description': 'Se desplaza'}],
                },
                'keypoints_data': {'LEFT_KNEE': {'x': 0.5, 'y': 0.7, 'z': 0, 'visibility': 0.95}},
                'risk_breakdown': {'knee_left': 80},
                'ai_model_version': 'test',
                'processing_time_ms': 120,
            },
            {
                'joint_angles': {'knee_left': 170, 'hip_left': 180},
                'risk_score': 30,
                'risk_level': 'low',
                'ai_confidence': 85,
                'detected_issues': [],
                'exercise_feedback': {
                    'status': 'ok',
                    'cues': ['Mantener control'],
                    'issues': [],
                },
                'keypoints_data': {'LEFT_KNEE': {'x': 0.6, 'y': 0.8, 'z': 0, 'visibility': 0.9}},
                'risk_breakdown': {'knee_left': 20},
                'ai_model_version': 'test',
                'processing_time_ms': 90,
            },
        ]

        result = _aggregate_exercise_results(results, 'squat', 12, analyzer)

        self.assertEqual(result['joint_angles'], {'knee_left': 150, 'hip_left': 180})
        self.assertEqual(result['risk_score'], 56.67)
        self.assertEqual(result['risk_level'], 'low')
        self.assertEqual(result['exercise_feedback']['session_statistics'], {
            'frames_analyzed': 3,
            'duration_seconds': 12,
            'average_risk_score': 56.67,
            'peak_risk_score': 80,
            'repeated_findings': 1,
        })
        self.assertEqual(result['detected_issues'][0]['occurrence_percentage'], 67)
        self.assertEqual(result['detected_issues'][0]['severity'], 'critical')
        self.assertEqual(result['exercise_feedback']['status'], 'warning')
        self.assertEqual(result['keypoints_data']['LEFT_KNEE']['x'], 0.5)
        self.assertIn('Alinear la rodilla', result['recommendations'])


class BiomechanicalAssessmentAPITests(TestCase):
    def test_save_biomechanical_session_and_doctor_review(self):
        from athletes.models import Athlete
        from users.models import User
        from assessments.models import PosturalAssessment, BiomechanicalEvent, JointAngle
        from rest_framework.test import APIRequestFactory, force_authenticate
        from assessments.views import PosturalAssessmentViewSet

        user = User.objects.create_user(email='test_doc@test.com', password='123', first_name='Doc', last_name='Test', role=User.MEDICO)
        athlete = Athlete.objects.create(first_name='Atleta', last_name='Prueba', sport='Fútbol', email='atleta@test.com')

        factory = APIRequestFactory()
        view = PosturalAssessmentViewSet.as_view({'post': 'save_biomechanical_session'})

        payload = {
            'athlete_id': athlete.id,
            'exercise_type': 'squat',
            'duration_seconds': 45,
            'tracking_quality': 96.5,
            'risk_score': 65.0,
            'risk_level': 'high',
            'joint_angles': {'knee_left': 142.0, 'knee_right': 160.0},
            'detected_issues': [
                {
                    'zone': 'knee_left',
                    'description': 'Valgo dinámico de rodilla (3 veces)',
                    'severity': 'high',
                    'type': 'biomechanical',
                }
            ],
            'recommendations': ['Alinear la rodilla durante el descenso.'],
            'exercise_thresholds': {'valgus': 12, 'framesDebounce': 3},
            'exercise_feedback': {
                'status': 'warning',
                'summary': 'Se detectaron patrones biomecánicos.',
                'session_statistics': {
                    'frames_analyzed': 120,
                    'duration_seconds': 45,
                    'tracking_quality': 96.5,
                    'repeated_findings': 3,
                    'risk_score': 65.0,
                },
            },
            'biomechanical_events': [
                {
                    'error_name': 'Valgo dinámico de rodilla',
                    'exercise_type': 'squat',
                    'timestamp_seconds': 14.5,
                    'joint': 'knee_left',
                    'angle_degrees': 142.0,
                    'reference_range': '165°–180°',
                    'frequency': 3,
                    'confidence': 95.0,
                    'severity': 'high',
                    'observations': 'Colapso medial durante fase excéntrica',
                }
            ],
            'doctor_notes': 'Atleta presenta ligero déficit de glúteo medio.',
            'preventive_recommendations': {'technical_correction': 'Empujar rodillas hacia afuera al descender'},
        }

        request = factory.post('/api/v1/assessments/save-biomechanical-session/', payload, format='json')
        force_authenticate(request, user=user)
        response = view(request)
        self.assertEqual(response.status_code, 201)

        assessment_id = response.data['assessment']['id']
        assessment = PosturalAssessment.objects.get(pk=assessment_id)
        self.assertEqual(assessment.duration_seconds, 45)
        self.assertEqual(assessment.tracking_quality, 96.5)
        self.assertEqual(assessment.risk_score, 65.0)
        self.assertEqual(assessment.risk_level, 'high')
        self.assertEqual(assessment.joint_angles.count(), 2)
        self.assertEqual(assessment.detected_issues[0]['zone'], 'knee_left')
        self.assertEqual(assessment.recommendations[0], 'Alinear la rodilla durante el descenso.')
        self.assertEqual(assessment.exercise_thresholds['valgus'], 12)
        self.assertEqual(assessment.exercise_feedback['session_statistics']['frames_analyzed'], 120)
        self.assertEqual(assessment.events.count(), 1)
        event = assessment.events.first()
        self.assertEqual(event.error_name, 'Valgo dinámico de rodilla')
        self.assertEqual(event.frequency, 3)
        self.assertEqual(event.confidence, 95.0)
        self.assertEqual(event.observations, 'Colapso medial durante fase excéntrica')

        # Test doctor review endpoint
        review_view = PosturalAssessmentViewSet.as_view({'post': 'save_doctor_review'})
        review_request = factory.post(f'/api/v1/assessments/{assessment_id}/save-doctor-review/', {
            'doctor_notes': 'Notas médicas actualizadas y aprobadas.',
            'is_reviewed_by_doctor': True,
        }, format='json')
        force_authenticate(review_request, user=user)
        review_response = review_view(review_request, pk=assessment_id)
        self.assertEqual(review_response.status_code, 200)

        assessment.refresh_from_db()
        self.assertTrue(assessment.is_reviewed_by_doctor)
        self.assertEqual(assessment.reviewed_by, user)
        self.assertEqual(assessment.doctor_notes, 'Notas médicas actualizadas y aprobadas.')
