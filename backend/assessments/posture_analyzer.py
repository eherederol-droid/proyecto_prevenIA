"""
PostureAnalyzer — Core AI service using MediaPipe + OpenCV
Analyzes posture from images, computes joint angles, and returns risk assessment
"""
import cv2
import numpy as np
import mediapipe as mp
import math
import logging
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Optional, Tuple
from django.conf import settings

logger = logging.getLogger('prevenia')
mp_pose = mp.tasks.vision
PoseLandmark = mp_pose.PoseLandmark


class _PoseLandmarkerAdapter:
    """Expose MediaPipe Tasks results through the analyzer's process() interface."""

    def __init__(self, min_detection_confidence: float):
        model_path = Path(__file__).with_name('ai_models') / 'pose_landmarker_lite.task'
        if not model_path.is_file():
            model_path = Path(__file__).with_name('models') / 'pose_landmarker_lite.task'
        if not model_path.is_file():
            raise FileNotFoundError(
                f'No se encontró el modelo de postura de MediaPipe: {model_path}'
            )

        options = mp_pose.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp_pose.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=min_detection_confidence,
        )
        self._landmarker = mp_pose.PoseLandmarker.create_from_options(options)

    def process(self, image: np.ndarray):
        result = self._landmarker.detect(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=image)
        )
        landmarks = result.pose_landmarks[0] if result.pose_landmarks else None
        pose_landmarks = SimpleNamespace(landmark=landmarks) if landmarks else None
        return SimpleNamespace(pose_landmarks=pose_landmarks)

    def close(self):
        self._landmarker.close()


def calculate_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """
    Calculate the angle at point B formed by vectors BA and BC.
    Returns angle in degrees [0, 180].
    """
    ba = a - b
    bc = c - b
    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    angle = math.degrees(math.acos(np.clip(cosine, -1.0, 1.0)))
    return round(angle, 2)


def pixel_coords(landmark, h: int, w: int) -> np.ndarray:
    return np.array([landmark.x * w, landmark.y * h])


class PostureAnalyzer:
    """
    MediaPipe-based posture analyzer.
    Can run locally or delegate to AWS Lambda for production scale.
    """

    # Normal angle ranges (min, max) in degrees
    NORMAL_RANGES: Dict[str, Tuple[float, float]] = {
        'knee_left': (165.0, 180.0),
        'knee_right': (165.0, 180.0),
        'hip_left': (170.0, 195.0),
        'hip_right': (170.0, 195.0),
        'shoulder_left': (155.0, 185.0),
        'shoulder_right': (155.0, 185.0),
        'elbow_left': (150.0, 180.0),
        'elbow_right': (150.0, 180.0),
        'ankle_left': (85.0, 100.0),
        'ankle_right': (85.0, 100.0),
        'spine_lateral': (0.0, 5.0),
    }

    # Risk weights (sum doesn't need to be 1 — we normalize)
    RISK_WEIGHTS: Dict[str, float] = {
        'knee_left': 1.5,
        'knee_right': 1.5,
        'hip_left': 1.2,
        'hip_right': 1.2,
        'shoulder_left': 0.8,
        'shoulder_right': 0.8,
        'spine_lateral': 1.3,
        'ankle_left': 0.6,
        'ankle_right': 0.6,
    }

    def __init__(self, min_detection_confidence: float = 0.7):
        self.pose = _PoseLandmarkerAdapter(min_detection_confidence)
        self.ai_version = f'PrevenIA-MediaPipe-Tasks-{mp.__version__}'

    def analyze_image(
        self,
        image_path: str,
        exercise_type: str = 'general',
        view_type: str = 'frontal',
    ) -> Dict:
        """
        Main analysis entry point.
        Returns dict with joint_angles, risk_score, risk_level, recommendations, keypoints.
        """
        start_time = time.time()
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f'No se pudo cargar la imagen: {image_path}')
            return self._analyze_array(image, start_time, exercise_type, view_type)
        except Exception as e:
            logger.error(f'Error analizando imagen {image_path}: {e}')
            return self._error_result(str(e))

    def analyze_bytes(
        self,
        image_bytes: bytes,
        exercise_type: str = 'general',
        view_type: str = 'frontal',
    ) -> Dict:
        """Analyze image from bytes (used when image comes from upload)"""
        start_time = time.time()
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError('No se pudo decodificar la imagen')
            return self._analyze_array(image, start_time, exercise_type, view_type)
        except Exception as e:
            logger.error(f'Error analizando bytes de imagen: {e}')
            return self._error_result(str(e))

    def _analyze_array(
        self,
        image: np.ndarray,
        start_time: float,
        exercise_type: str = 'general',
        view_type: str = 'frontal',
    ) -> Dict:
        h, w, _ = image.shape
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)

        if not results.pose_landmarks:
            return self._error_result('No se detectó pose en la imagen. Asegúrese de que el atleta sea visible.')

        lm = results.pose_landmarks.landmark
        joint_angles = self._compute_joint_angles(lm, h, w)
        asymmetries = self._compute_asymmetries(joint_angles)
        risk_score, risk_breakdown = self._compute_risk_score(joint_angles, asymmetries)
        risk_level = self._risk_level_from_score(risk_score)
        issues = self._detect_issues(joint_angles, asymmetries)
        recommendations = self._generate_recommendations(issues, risk_level)

        keypoints = {
            name.name: {'x': round(l.x, 4), 'y': round(l.y, 4), 'z': round(l.z, 4), 'visibility': round(l.visibility, 4)}
            for name, l in zip(PoseLandmark, lm)
        }
        exercise_feedback = self.evaluate_exercise(
            exercise_type,
            keypoints,
            joint_angles,
            image_width=w,
            image_height=h,
            view_type=view_type,
        )
        if exercise_feedback:
            issues.extend(exercise_feedback['issues'])
            recommendations.extend(exercise_feedback['cues'])

        processing_ms = int((time.time() - start_time) * 1000)

        return {
            'success': True,
            'ai_model_version': self.ai_version,
            'joint_angles': joint_angles,
            'asymmetries': asymmetries,
            'risk_score': round(risk_score, 2),
            'risk_level': risk_level,
            'ai_confidence': self._estimate_confidence(results),
            'detected_issues': issues,
            'recommendations': recommendations,
            'exercise_feedback': exercise_feedback,
            'risk_breakdown': risk_breakdown,
            'keypoints_data': keypoints,
            'processing_time_ms': processing_ms,
        }

    @staticmethod
    def evaluate_exercise(
        exercise_type: str,
        keypoints: Dict,
        joint_angles: Dict[str, float],
        image_width: int,
        image_height: int,
        view_type: str,
    ) -> Optional[Dict]:
        """Return simple, exercise-specific visual cues from a single pose frame."""
        if exercise_type == 'general':
            return None

        labels = {
            'squat': 'Sentadilla',
            'lunge': 'Zancada',
            'push_up': 'Flexión de brazos',
            'arm_raise': 'Elevación de brazos',
            'joint_mobility': 'Movilidad articular',
            'plank': 'Plancha',
            'side_plank': 'Plancha lateral',
            'burpee': 'Burpee',
            'jumping_jack': 'Jumping jack',
            'deadlift': 'Peso muerto',
            'glute_bridge': 'Puente de glúteos',
            'calf_raise': 'Elevación de pantorrillas',
            'step_up': 'Subida al cajón',
            'mountain_climber': 'Escaladores',
            'overhead_press': 'Press sobre la cabeza',
            'biceps_curl': 'Curl de bíceps',
            'row': 'Remo',
            'triceps_dip': 'Fondos de tríceps',
            'lateral_raise': 'Elevación lateral de hombros',
            'crunch': 'Abdominales',
            'jump_landing': 'Salto y aterrizaje',
        }
        if exercise_type not in labels:
            raise ValueError(f'Ejercicio no compatible: {exercise_type}')

        visible = {
            name: point for name, point in keypoints.items()
            if point.get('visibility', 0) >= 0.5
        }
        issues = []
        cues = []

        def add_issue(zone: str, description: str, landmarks: List[str]):
            issues.append({
                'type': 'exercise_form',
                'zone': zone,
                'severity': 'medium',
                'description': description,
                'landmarks': landmarks,
            })
            cues.append(description)

        def body_angle(first: str, vertex: str, last: str) -> Optional[float]:
            if not all(name in visible for name in (first, vertex, last)):
                return None
            a, b, c = (visible[name] for name in (first, vertex, last))
            return calculate_angle(
                np.array([a['x'] * image_width, a['y'] * image_height]),
                np.array([b['x'] * image_width, b['y'] * image_height]),
                np.array([c['x'] * image_width, c['y'] * image_height]),
            )

        def knee_alignment(side: str) -> bool:
            hip = visible.get(f'{side.upper()}_HIP')
            knee = visible.get(f'{side.upper()}_KNEE')
            ankle = visible.get(f'{side.upper()}_ANKLE')
            if not hip or not knee or not ankle:
                return False
            hip_center = (
                (visible['LEFT_HIP']['x'] + visible['RIGHT_HIP']['x']) / 2
                if 'LEFT_HIP' in visible and 'RIGHT_HIP' in visible
                else hip['x']
            )
            outward = -1 if hip['x'] < hip_center else 1
            hip_width = abs(
                visible['LEFT_HIP']['x'] - visible['RIGHT_HIP']['x']
            ) if 'LEFT_HIP' in visible and 'RIGHT_HIP' in visible else 0
            if hip_width < 0.02:
                return False
            knee_outward = (knee['x'] - hip_center) * outward
            ankle_outward = (ankle['x'] - hip_center) * outward
            return knee_outward + hip_width * 0.12 < ankle_outward

        def neutral(summary: str) -> Dict:
            return {
                'exercise_type': exercise_type,
                'exercise_display': labels[exercise_type],
                'status': 'neutral',
                'summary': summary,
                'cues': [],
                'issues': [],
            }

        def body_is_horizontal() -> bool:
            for side in ('LEFT', 'RIGHT'):
                body_points = [
                    visible.get(f'{side}_SHOULDER'),
                    visible.get(f'{side}_HIP'),
                    visible.get(f'{side}_ANKLE'),
                ]
                if any(point is None for point in body_points):
                    continue
                horizontal_span = abs(body_points[2]['x'] - body_points[0]['x']) * image_width
                vertical_span = (
                    max(point['y'] for point in body_points)
                    - min(point['y'] for point in body_points)
                ) * image_height
                if horizontal_span >= image_width * 0.18 and vertical_span <= horizontal_span * 0.8:
                    return True
            return False

        def add_body_alignment_issue(threshold: float = 155):
            found_issue = False
            for side in ('LEFT', 'RIGHT'):
                alignment = body_angle(f'{side}_SHOULDER', f'{side}_HIP', f'{side}_ANKLE')
                if alignment is not None and alignment < threshold:
                    add_issue(
                        'Alineación corporal',
                        'Hombros, caderas y tobillos pierden la línea; activa el abdomen y conserva el tronco firme.',
                        [f'{side}_SHOULDER', f'{side}_HIP', f'{side}_ANKLE'],
                    )
                    found_issue = True
                    break
            return found_issue

        left_knee = (
            joint_angles.get('knee_left')
            if all(name in visible for name in ('LEFT_HIP', 'LEFT_KNEE', 'LEFT_ANKLE'))
            else None
        )
        right_knee = (
            joint_angles.get('knee_right')
            if all(name in visible for name in ('RIGHT_HIP', 'RIGHT_KNEE', 'RIGHT_ANKLE'))
            else None
        )
        knees = [angle for angle in (left_knee, right_knee) if angle is not None]
        left_elbow = (
            joint_angles.get('elbow_left')
            if all(name in visible for name in ('LEFT_SHOULDER', 'LEFT_ELBOW', 'LEFT_WRIST'))
            else None
        )
        right_elbow = (
            joint_angles.get('elbow_right')
            if all(name in visible for name in ('RIGHT_SHOULDER', 'RIGHT_ELBOW', 'RIGHT_WRIST'))
            else None
        )
        elbows = [angle for angle in (left_elbow, right_elbow) if angle is not None]

        if exercise_type == 'squat':
            if not knees:
                return {
                    'exercise_type': exercise_type,
                    'exercise_display': labels[exercise_type],
                    'status': 'neutral',
                    'summary': 'Muestra las caderas, rodillas y tobillos para evaluar la sentadilla.',
                    'cues': [],
                    'issues': [],
                }
            knee_flexion = min(knees)
            if knee_flexion >= 155:
                summary = 'Posición inicial detectada; inicia la sentadilla para evaluar el recorrido.'
                status = 'neutral'
            elif knee_flexion < 60:
                summary = 'Flexión profunda detectada; controla el recorrido y evita forzar la posición.'
                status = 'warning'
                add_issue(
                    'Sentadilla',
                    summary,
                    ['LEFT_HIP', 'LEFT_KNEE', 'LEFT_ANKLE', 'RIGHT_HIP', 'RIGHT_KNEE', 'RIGHT_ANKLE'],
                )
            elif knee_flexion > 135:
                summary = 'Continúa flexionando las rodillas de forma controlada durante el descenso.'
                status = 'warning'
                add_issue(
                    'Sentadilla',
                    summary,
                    ['LEFT_HIP', 'LEFT_KNEE', 'LEFT_ANKLE', 'RIGHT_HIP', 'RIGHT_KNEE', 'RIGHT_ANKLE'],
                )
            else:
                summary = 'Flexión detectada; mantén el control durante el descenso y el ascenso.'
                status = 'good'
            if view_type == 'frontal' and knee_flexion < 155:
                for side in ('left', 'right'):
                    if knee_alignment(side):
                        side_label = 'izquierda' if side == 'left' else 'derecha'
                        add_issue(
                            f'Rodilla {side_label}',
                            f'La rodilla {side_label} parece desplazarse hacia dentro; intenta alinearla con el pie.',
                            [f'{side.upper()}_HIP', f'{side.upper()}_KNEE', f'{side.upper()}_ANKLE'],
                        )

        elif exercise_type == 'lunge':
            if not knees:
                return {
                    'exercise_type': exercise_type,
                    'exercise_display': labels[exercise_type],
                    'status': 'neutral',
                    'summary': 'Muestra ambas piernas para evaluar la zancada.',
                    'cues': [],
                    'issues': [],
                }
            knee_flexion = min(knees)
            if knee_flexion >= 155:
                summary = 'Posición inicial detectada; realiza la zancada para evaluar la técnica.'
                status = 'neutral'
            elif knee_flexion < 60:
                summary = 'La rodilla está muy flexionada; acorta el recorrido y mantén el control.'
                status = 'warning'
                add_issue('Zancada', summary, ['LEFT_HIP', 'LEFT_KNEE', 'LEFT_ANKLE', 'RIGHT_HIP', 'RIGHT_KNEE', 'RIGHT_ANKLE'])
            elif knee_flexion > 135:
                summary = 'Aumenta ligeramente la flexión y conserva una postura estable.'
                status = 'warning'
                add_issue('Zancada', summary, ['LEFT_HIP', 'LEFT_KNEE', 'LEFT_ANKLE', 'RIGHT_HIP', 'RIGHT_KNEE', 'RIGHT_ANKLE'])
            else:
                summary = 'Flexión detectada; procura mantener el tronco estable y la rodilla alineada con el pie.'
                status = 'good'
            if left_knee is not None and right_knee is not None and abs(left_knee - right_knee) > 25:
                add_issue(
                    'Zancada',
                    'Hay una diferencia marcada entre las rodillas; revisa que el paso y el apoyo sean estables.',
                    ['LEFT_HIP', 'LEFT_KNEE', 'LEFT_ANKLE', 'RIGHT_HIP', 'RIGHT_KNEE', 'RIGHT_ANKLE'],
                )
            if view_type == 'frontal' and knee_flexion < 155:
                for side in ('left', 'right'):
                    if knee_alignment(side):
                        side_label = 'izquierda' if side == 'left' else 'derecha'
                        add_issue(
                            f'Rodilla {side_label}',
                            f'La rodilla {side_label} parece desplazarse hacia dentro; intenta alinearla con el pie.',
                            [f'{side.upper()}_HIP', f'{side.upper()}_KNEE', f'{side.upper()}_ANKLE'],
                        )

        elif exercise_type == 'push_up':
            if view_type != 'lateral':
                return {
                    'exercise_type': exercise_type,
                    'exercise_display': labels[exercise_type],
                    'status': 'neutral',
                    'summary': 'Selecciona la vista lateral y colócate en posición de plancha para evaluar la flexión.',
                    'cues': [],
                    'issues': [],
                }
            horizontal_body = False
            for side in ('LEFT', 'RIGHT'):
                body_points = [
                    visible.get(f'{side}_SHOULDER'),
                    visible.get(f'{side}_HIP'),
                    visible.get(f'{side}_ANKLE'),
                ]
                if any(point is None for point in body_points):
                    continue
                horizontal_span = abs(body_points[2]['x'] - body_points[0]['x']) * image_width
                vertical_span = (
                    max(point['y'] for point in body_points)
                    - min(point['y'] for point in body_points)
                ) * image_height
                if horizontal_span >= image_width * 0.18 and vertical_span <= horizontal_span * 0.8:
                    horizontal_body = True
                    break
            if not horizontal_body:
                return {
                    'exercise_type': exercise_type,
                    'exercise_display': labels[exercise_type],
                    'status': 'neutral',
                    'summary': 'Colócate de lado en posición de plancha y muestra hombros, caderas y tobillos.',
                    'cues': [],
                    'issues': [],
                }
            if not elbows:
                return {
                    'exercise_type': exercise_type,
                    'exercise_display': labels[exercise_type],
                    'status': 'neutral',
                    'summary': 'Muestra hombros, codos, caderas y tobillos para evaluar la flexión.',
                    'cues': [],
                    'issues': [],
                }
            elbow_flexion = min(elbows)
            if elbow_flexion >= 160:
                summary = 'Posición alta detectada; desciende de forma controlada para evaluar la flexión.'
                status = 'neutral'
            elif elbow_flexion < 55:
                summary = 'Flexión muy profunda; reduce el recorrido si pierdes el control.'
                status = 'warning'
                add_issue('Flexión de brazos', summary, ['LEFT_SHOULDER', 'LEFT_ELBOW', 'LEFT_WRIST', 'RIGHT_SHOULDER', 'RIGHT_ELBOW', 'RIGHT_WRIST'])
            else:
                summary = 'Flexión detectada; conserva el cuerpo alineado mientras bajas y subes.'
                status = 'good'
            for side in ('LEFT', 'RIGHT'):
                alignment = body_angle(f'{side}_SHOULDER', f'{side}_HIP', f'{side}_ANKLE')
                if alignment is not None and alignment < 155:
                    add_issue(
                        'Alineación corporal',
                        'Caderas y hombros pierden la línea del cuerpo; activa el abdomen y mantén el tronco firme.',
                        [f'{side}_SHOULDER', f'{side}_HIP', f'{side}_ANKLE'],
                    )

        elif exercise_type in ('plank', 'side_plank', 'burpee', 'mountain_climber'):
            if view_type != 'lateral':
                return neutral('Usa la vista lateral y muestra hombros, caderas y tobillos para revisar la alineación.')
            if not body_is_horizontal():
                prompts = {
                    'plank': 'Colócate en posición de plancha lateral a la cámara para revisar la alineación.',
                    'side_plank': 'Colócate de lado en posición de plancha lateral y muestra el cuerpo completo.',
                    'burpee': 'Continúa el burpee; la cámara revisará la alineación durante la fase de plancha.',
                    'mountain_climber': 'Colócate en posición de plancha para evaluar los escaladores.',
                }
                return neutral(prompts[exercise_type])
            if add_body_alignment_issue():
                status = 'warning'
                summary = issues[0]['description']
            else:
                status = 'good'
                summary = 'Alineación corporal detectada; conserva el abdomen activo durante el movimiento.'

        elif exercise_type == 'jumping_jack':
            if view_type != 'frontal':
                return neutral('Usa la vista frontal y muestra brazos y piernas completos para evaluar el jumping jack.')
            wrists_above_shoulders = all(
                name in visible for name in ('LEFT_WRIST', 'RIGHT_WRIST', 'LEFT_SHOULDER', 'RIGHT_SHOULDER')
            ) and visible['LEFT_WRIST']['y'] < visible['LEFT_SHOULDER']['y'] \
                and visible['RIGHT_WRIST']['y'] < visible['RIGHT_SHOULDER']['y']
            feet_apart = all(
                name in visible for name in ('LEFT_ANKLE', 'RIGHT_ANKLE', 'LEFT_HIP', 'RIGHT_HIP')
            ) and abs(visible['LEFT_ANKLE']['x'] - visible['RIGHT_ANKLE']['x']) \
                > abs(visible['LEFT_HIP']['x'] - visible['RIGHT_HIP']['x']) * 1.35
            if wrists_above_shoulders and feet_apart:
                status = 'good'
                summary = 'Posición abierta detectada; controla el aterrizaje y mantén rodillas alineadas con los pies.'
                if knees and min(knees) < 160:
                    for side in ('left', 'right'):
                        if knee_alignment(side):
                            side_label = 'izquierda' if side == 'left' else 'derecha'
                            add_issue(
                                f'Rodilla {side_label}',
                                f'La rodilla {side_label} parece desplazarse hacia dentro; al aterrizar, alinéala con el pie.',
                                [f'{side.upper()}_HIP', f'{side.upper()}_KNEE', f'{side.upper()}_ANKLE'],
                            )
            else:
                return neutral('Completa la apertura elevando los brazos y separando los pies; se revisa cada fotograma.')

        elif exercise_type == 'deadlift':
            if view_type != 'lateral':
                return neutral('Usa la vista lateral y muestra hombros, caderas, rodillas y tobillos durante el peso muerto.')
            torso_hip_angle = body_angle('LEFT_SHOULDER', 'LEFT_HIP', 'LEFT_KNEE')
            if torso_hip_angle is None:
                torso_hip_angle = body_angle('RIGHT_SHOULDER', 'RIGHT_HIP', 'RIGHT_KNEE')
            if torso_hip_angle is None or torso_hip_angle >= 160:
                return neutral('Posición inicial detectada; inicia la bisagra de cadera para revisar el recorrido.')
            if torso_hip_angle < 70:
                status = 'warning'
                summary = 'El ángulo de cadera está muy cerrado en este fotograma; reduce el recorrido si pierdes el control.'
                add_issue('Cadera', summary, ['LEFT_SHOULDER', 'LEFT_HIP', 'LEFT_KNEE'])
            else:
                status = 'good'
                summary = 'Bisagra de cadera detectada; mantén la espalda estable y la carga cerca del cuerpo.'

        elif exercise_type == 'glute_bridge':
            if view_type != 'lateral':
                return neutral('Usa la vista lateral y muestra hombro, cadera y rodilla para revisar el puente de glúteos.')
            if not all(name in visible for name in ('LEFT_SHOULDER', 'LEFT_HIP', 'LEFT_KNEE')) \
                    and not all(name in visible for name in ('RIGHT_SHOULDER', 'RIGHT_HIP', 'RIGHT_KNEE')):
                return neutral('No se ven suficientes puntos para revisar la posición del puente.')
            hip_angle = body_angle('LEFT_SHOULDER', 'LEFT_HIP', 'LEFT_KNEE')
            if hip_angle is None:
                hip_angle = body_angle('RIGHT_SHOULDER', 'RIGHT_HIP', 'RIGHT_KNEE')
            if hip_angle is None or hip_angle > 155:
                return neutral('Posición inicial detectada; eleva la pelvis de forma controlada para evaluar el puente.')
            if hip_angle < 75:
                status = 'warning'
                summary = 'Evita comprimir demasiado la cadera; reduce el recorrido y mantén el control.'
                add_issue('Cadera', summary, ['LEFT_SHOULDER', 'LEFT_HIP', 'LEFT_KNEE'])
            else:
                status = 'good'
                summary = 'Elevación detectada; evita arquear la zona lumbar al final del recorrido.'

        elif exercise_type in ('calf_raise', 'step_up'):
            if not knees:
                return neutral('Muestra caderas, rodillas y tobillos completos para revisar este ejercicio.')
            if exercise_type == 'calf_raise':
                if view_type != 'lateral':
                    return neutral('Usa la vista lateral para mostrar tobillo, rodilla y pie durante la elevación.')
                foot_angles = [
                    body_angle(f'{side}_KNEE', f'{side}_ANKLE', f'{side}_FOOT_INDEX')
                    for side in ('LEFT', 'RIGHT')
                ]
                raised_feet = [angle for angle in foot_angles if angle is not None and angle < 70]
                if not raised_feet:
                    return neutral('Posición inicial detectada; eleva los talones para revisar el control del movimiento.')
                status = 'good'
                summary = 'Elevación detectada; conserva el apoyo simétrico y controla el descenso.'
            else:
                if left_knee is None or right_knee is None or abs(left_knee - right_knee) < 25:
                    return neutral('Muestra la fase de subida al escalón de lado o de frente para evaluar el apoyo.')
                status = 'good'
                summary = 'Subida detectada; apoya el pie completo en el escalón y controla la alineación de la rodilla.'
                for side in ('left', 'right'):
                    if knee_alignment(side):
                        side_label = 'izquierda' if side == 'left' else 'derecha'
                        add_issue(
                            f'Rodilla {side_label}',
                            f'La rodilla {side_label} parece desviarse hacia dentro durante la subida.',
                            [f'{side.upper()}_HIP', f'{side.upper()}_KNEE', f'{side.upper()}_ANKLE'],
                        )

        elif exercise_type in ('overhead_press', 'lateral_raise', 'arm_raise'):
            if view_type != 'frontal':
                return neutral('Usa la vista frontal y muestra hombros, codos y muñecas durante el ejercicio.')
            if not all(name in visible for name in ('LEFT_WRIST', 'RIGHT_WRIST', 'LEFT_SHOULDER', 'RIGHT_SHOULDER')):
                return neutral('Muestra ambos brazos completos para revisar la simetría.')
            left_raised = visible['LEFT_WRIST']['y'] < visible['LEFT_SHOULDER']['y']
            right_raised = visible['RIGHT_WRIST']['y'] < visible['RIGHT_SHOULDER']['y']
            if exercise_type in ('lateral_raise', 'arm_raise'):
                left_height = visible['LEFT_SHOULDER']['y'] - visible['LEFT_WRIST']['y']
                right_height = visible['RIGHT_SHOULDER']['y'] - visible['RIGHT_WRIST']['y']
                at_shoulder_height = (
                    abs(left_height) <= 0.14 and abs(right_height) <= 0.14
                    and max(left_height, right_height) >= 0.02
                )
                asymmetric_height = abs(left_height - right_height) > 0.08
            else:
                at_shoulder_height = left_raised and right_raised
                asymmetric_height = left_raised != right_raised
            if asymmetric_height:
                side = 'izquierdo' if left_raised else 'derecho'
                landmarks = ['LEFT_SHOULDER', 'LEFT_ELBOW', 'LEFT_WRIST', 'RIGHT_SHOULDER', 'RIGHT_ELBOW', 'RIGHT_WRIST']
                status = 'warning'
                summary = f'Los brazos no están a la misma altura; revisa la simetría del hombro {side}.'
                add_issue('Hombros', summary, landmarks)
            elif at_shoulder_height:
                status = 'good'
                summary = 'Elevación simétrica detectada; evita arquear la espalda o encoger los hombros.'
            else:
                return neutral('Posición inicial detectada; eleva ambos brazos para revisar la simetría del movimiento.')

        elif exercise_type == 'joint_mobility':
            if not all(name in visible for name in ('LEFT_SHOULDER', 'RIGHT_SHOULDER')):
                return neutral('Muestra el cuerpo completo para evaluar la movilidad y simetría articular.')
            status = 'good'
            summary = 'Movilidad y alineación general dentro de rangos normales.'
            # Check shoulder level asymmetry
            left_sh = visible.get('LEFT_SHOULDER')
            right_sh = visible.get('RIGHT_SHOULDER')
            if left_sh and right_sh and abs(left_sh['y'] - right_sh['y']) > 0.05:
                status = 'warning'
                summary = 'Desbalance o asimetría escapular detectada en el plano coronal.'
                add_issue('Hombros', summary, ['LEFT_SHOULDER', 'RIGHT_SHOULDER'])

        elif exercise_type in ('biceps_curl', 'triceps_dip'):
            if not elbows:
                return neutral('Muestra hombros, codos y muñecas para revisar la flexión del brazo.')
            elbow_flexion = min(elbows)
            if elbow_flexion < 35:
                status = 'warning'
                summary = 'El codo está muy cerrado en este fotograma; evita forzar el final del recorrido.'
                add_issue('Codo', summary, ['LEFT_SHOULDER', 'LEFT_ELBOW', 'LEFT_WRIST', 'RIGHT_SHOULDER', 'RIGHT_ELBOW', 'RIGHT_WRIST'])
            elif left_elbow is not None and right_elbow is not None and abs(left_elbow - right_elbow) > 30:
                status = 'warning'
                summary = 'Se observa una diferencia entre ambos brazos; intenta realizar el movimiento de forma simétrica.'
                add_issue('Brazos', summary, ['LEFT_SHOULDER', 'LEFT_ELBOW', 'LEFT_WRIST', 'RIGHT_SHOULDER', 'RIGHT_ELBOW', 'RIGHT_WRIST'])
            elif elbow_flexion > 155:
                return neutral('Posición inicial detectada; realiza la repetición para evaluar la técnica del brazo.')
            else:
                status = 'good'
                summary = 'Flexión de codo detectada; conserva el brazo controlado y evita balancear el tronco.'

        elif exercise_type == 'row':
            if view_type != 'lateral':
                return neutral('Usa la vista lateral para revisar la posición del tronco durante el remo.')
            if not elbows:
                return neutral('Muestra hombros, codos y muñecas durante la repetición.')
            if min(elbows) > 155:
                return neutral('Posición inicial detectada; realiza el tirón para revisar la simetría de los brazos.')
            if left_elbow is not None and right_elbow is not None and abs(left_elbow - right_elbow) > 30:
                add_issue(
                    'Brazos',
                    'Se observa una diferencia entre ambos brazos; intenta realizar el tirón de forma simétrica.',
                    ['LEFT_SHOULDER', 'LEFT_ELBOW', 'LEFT_WRIST', 'RIGHT_SHOULDER', 'RIGHT_ELBOW', 'RIGHT_WRIST'],
                )
                status = 'warning'
                summary = issues[0]['description']
            else:
                status = 'good'
                summary = 'Fase de tracción detectada; evita impulsarte y mantén el tronco estable durante la repetición.'

        elif exercise_type == 'crunch':
            if view_type != 'lateral':
                return neutral('Usa la vista lateral para revisar el recorrido de los abdominales.')
            hip_angle = body_angle('LEFT_SHOULDER', 'LEFT_HIP', 'LEFT_KNEE')
            if hip_angle is None:
                hip_angle = body_angle('RIGHT_SHOULDER', 'RIGHT_HIP', 'RIGHT_KNEE')
            if hip_angle is None or hip_angle > 155:
                return neutral('Posición inicial detectada; inicia el abdominal y evita tirar del cuello.')
            if hip_angle < 40:
                status = 'warning'
                summary = 'Reduce el recorrido si sientes tensión; evita forzar la flexión del tronco.'
                add_issue('Tronco', summary, ['LEFT_SHOULDER', 'LEFT_HIP', 'LEFT_KNEE'])
            else:
                status = 'good'
                summary = 'Flexión del tronco detectada; mantén el cuello relajado y controla el descenso.'

        elif exercise_type == 'jump_landing':
            if not knees:
                return neutral('Muestra el cuerpo completo y usa una vista frontal o lateral para revisar el aterrizaje.')
            if view_type == 'frontal':
                for side in ('left', 'right'):
                    if knee_alignment(side):
                        side_label = 'izquierda' if side == 'left' else 'derecha'
                        add_issue(
                            f'Rodilla {side_label}',
                            f'La rodilla {side_label} parece desplazarse hacia dentro en este fotograma de apoyo.',
                            [f'{side.upper()}_HIP', f'{side.upper()}_KNEE', f'{side.upper()}_ANKLE'],
                        )
            if min(knees) >= 160:
                return neutral('Un fotograma no confirma el aterrizaje; captura la fase de contacto y flexión de rodillas.')
            if issues:
                status = 'warning'
                summary = issues[0]['description']
            else:
                status = 'good'
                summary = 'Flexión de apoyo detectada; el control del aterrizaje requiere revisar varios fotogramas.'

        if issues:
            status = 'warning'
            summary = issues[0]['description']
        return {
            'exercise_type': exercise_type,
            'exercise_display': labels[exercise_type],
            'status': status,
            'summary': summary,
            'cues': list(dict.fromkeys(cues)),
            'issues': issues,
        }

    def _compute_joint_angles(self, lm, h: int, w: int) -> Dict[str, float]:
        """Compute all relevant joint angles using MediaPipe landmarks"""
        PL = PoseLandmark
        angles = {}

        # Helper
        def pt(landmark_id):
            l = lm[landmark_id.value]
            return pixel_coords(l, h, w)

        # Knees
        try:
            angles['knee_left'] = calculate_angle(pt(PL.LEFT_HIP), pt(PL.LEFT_KNEE), pt(PL.LEFT_ANKLE))
            angles['knee_right'] = calculate_angle(pt(PL.RIGHT_HIP), pt(PL.RIGHT_KNEE), pt(PL.RIGHT_ANKLE))
        except Exception:
            pass

        # Hips
        try:
            angles['hip_left'] = calculate_angle(pt(PL.LEFT_SHOULDER), pt(PL.LEFT_HIP), pt(PL.LEFT_KNEE))
            angles['hip_right'] = calculate_angle(pt(PL.RIGHT_SHOULDER), pt(PL.RIGHT_HIP), pt(PL.RIGHT_KNEE))
        except Exception:
            pass

        # Shoulders
        try:
            angles['shoulder_left'] = calculate_angle(pt(PL.LEFT_ELBOW), pt(PL.LEFT_SHOULDER), pt(PL.LEFT_HIP))
            angles['shoulder_right'] = calculate_angle(pt(PL.RIGHT_ELBOW), pt(PL.RIGHT_SHOULDER), pt(PL.RIGHT_HIP))
        except Exception:
            pass

        # Elbows
        try:
            angles['elbow_left'] = calculate_angle(pt(PL.LEFT_SHOULDER), pt(PL.LEFT_ELBOW), pt(PL.LEFT_WRIST))
            angles['elbow_right'] = calculate_angle(pt(PL.RIGHT_SHOULDER), pt(PL.RIGHT_ELBOW), pt(PL.RIGHT_WRIST))
        except Exception:
            pass

        # Ankles
        try:
            angles['ankle_left'] = calculate_angle(pt(PL.LEFT_KNEE), pt(PL.LEFT_ANKLE), pt(PL.LEFT_FOOT_INDEX))
            angles['ankle_right'] = calculate_angle(pt(PL.RIGHT_KNEE), pt(PL.RIGHT_ANKLE), pt(PL.RIGHT_FOOT_INDEX))
        except Exception:
            pass

        # Spine lateral (shoulder vs hip lateral deviation)
        try:
            ls = lm[PL.LEFT_SHOULDER.value]
            rs = lm[PL.RIGHT_SHOULDER.value]
            lh = lm[PL.LEFT_HIP.value]
            rh = lm[PL.RIGHT_HIP.value]
            mid_shoulder_x = (ls.x + rs.x) / 2
            mid_hip_x = (lh.x + rh.x) / 2
            angles['spine_lateral'] = round(abs(mid_shoulder_x - mid_hip_x) * 100, 2)
        except Exception:
            pass

        return angles

    def _compute_asymmetries(self, angles: Dict[str, float]) -> Dict[str, float]:
        """Compute left-right asymmetries for paired joints"""
        asymmetries = {}
        pairs = [
            ('knee', 'knee_left', 'knee_right'),
            ('hip', 'hip_left', 'hip_right'),
            ('shoulder', 'shoulder_left', 'shoulder_right'),
            ('elbow', 'elbow_left', 'elbow_right'),
            ('ankle', 'ankle_left', 'ankle_right'),
        ]
        for name, left_key, right_key in pairs:
            if left_key in angles and right_key in angles:
                asymmetries[name] = round(abs(angles[left_key] - angles[right_key]), 2)
        return asymmetries

    def _compute_risk_score(self, angles: Dict, asymmetries: Dict) -> Tuple[float, Dict]:
        """
        Weighted risk score computation.
        Returns (0-100 score, breakdown dict)
        """
        breakdown = {}
        total_weight = 0.0
        weighted_risk = 0.0

        for joint, (min_a, max_a) in self.NORMAL_RANGES.items():
            if joint not in angles:
                continue
            angle = angles[joint]
            weight = self.RISK_WEIGHTS.get(joint, 1.0)
            total_weight += weight

            if min_a <= angle <= max_a:
                joint_risk = 0.0
            elif angle < min_a:
                deviation = min_a - angle
                joint_risk = min(100.0, (deviation / min_a) * 200)
            else:
                deviation = angle - max_a
                joint_risk = min(100.0, (deviation / max_a) * 150)

            weighted_risk += joint_risk * weight
            breakdown[joint] = round(joint_risk, 2)

        # Add asymmetry risk
        for joint, asymm in asymmetries.items():
            thresholds = {'knee': 5, 'hip': 8, 'shoulder': 5, 'elbow': 10, 'ankle': 5}
            threshold = thresholds.get(joint, 8)
            if asymm > threshold:
                asymm_risk = min(30.0, (asymm - threshold) * 3)
                weighted_risk += asymm_risk * 0.8
                total_weight += 0.8
                breakdown[f'{joint}_asymmetry'] = round(asymm_risk, 2)

        final_score = (weighted_risk / total_weight) if total_weight > 0 else 0.0
        return min(100.0, final_score), breakdown

    def _risk_level_from_score(self, score: float) -> str:
        ai_settings = settings.POSTURE_AI
        if score >= ai_settings['CRITICAL_RISK_THRESHOLD'] * 100:
            return 'critical'
        elif score >= ai_settings['HIGH_RISK_THRESHOLD'] * 100:
            return 'high'
        elif score >= 40:
            return 'medium'
        return 'low'

    def _detect_issues(self, angles: Dict, asymmetries: Dict) -> List[Dict]:
        """Detect specific biomechanical issues"""
        issues = []

        # Knee valgus / varus
        for side, key in [('izquierda', 'knee_left'), ('derecha', 'knee_right')]:
            if key in angles and angles[key] < 160:
                issues.append({
                    'type': 'valgus_knee',
                    'zone': f'Rodilla {side}',
                    'severity': 'critical' if angles[key] < 150 else 'high',
                    'description': f'Posible valgo de rodilla {side} ({angles[key]}°). Ángulo por debajo del rango normal.',
                })

        # Hip asymmetry
        if asymmetries.get('hip', 0) > 10:
            issues.append({
                'type': 'hip_asymmetry',
                'zone': 'Cadera',
                'severity': 'high',
                'description': f'Asimetría de cadera detectada ({asymmetries["hip"]}°). Posible dismetría o inclinación pélvica.',
            })

        # Shoulder asymmetry
        if asymmetries.get('shoulder', 0) > 8:
            issues.append({
                'type': 'shoulder_asymmetry',
                'zone': 'Hombros',
                'severity': 'medium',
                'description': f'Asimetría de hombros ({asymmetries["shoulder"]}°). Revisar compensaciones posturales.',
            })

        # Spine lateral
        if angles.get('spine_lateral', 0) > 5:
            issues.append({
                'type': 'lateral_deviation',
                'zone': 'Columna Vertebral',
                'severity': 'high' if angles['spine_lateral'] > 10 else 'medium',
                'description': f'Desviación lateral de columna detectada ({angles["spine_lateral"]}%). Posible escoliosis funcional.',
            })

        covered_joints = set()
        for issue in issues:
            issue_type = issue['type']
            if issue_type == 'valgus_knee':
                side = 'left' if 'izquierda' in issue['zone'].lower() else 'right'
                covered_joints.add(f'knee_{side}')
            elif issue_type == 'hip_asymmetry':
                covered_joints.update(('hip_left', 'hip_right'))
            elif issue_type == 'shoulder_asymmetry':
                covered_joints.update(('shoulder_left', 'shoulder_right'))
            elif issue_type == 'lateral_deviation':
                covered_joints.add('spine_lateral')

        labels = {
            'knee_left': 'Rodilla izquierda', 'knee_right': 'Rodilla derecha',
            'hip_left': 'Cadera izquierda', 'hip_right': 'Cadera derecha',
            'shoulder_left': 'Hombro izquierdo', 'shoulder_right': 'Hombro derecho',
            'elbow_left': 'Codo izquierdo', 'elbow_right': 'Codo derecho',
            'ankle_left': 'Tobillo izquierdo', 'ankle_right': 'Tobillo derecho',
            'spine_lateral': 'Columna vertebral',
        }
        for joint, angle in angles.items():
            normal_range = self.NORMAL_RANGES.get(joint)
            if not normal_range or joint in covered_joints:
                continue
            if normal_range[0] <= angle <= normal_range[1]:
                continue
            deviation = normal_range[0] - angle if angle < normal_range[0] else angle - normal_range[1]
            issues.append({
                'type': 'joint_deviation',
                'joint': joint,
                'zone': labels.get(joint, joint),
                'severity': 'medium',
                'description': (
                    f'{labels.get(joint, joint)} fuera del rango normal '
                    f'({angle:.1f}°; rango {normal_range[0]}°–{normal_range[1]}°, '
                    f'desviación {deviation:.1f}°).'
                ),
            })

        return issues

    def _generate_recommendations(self, issues: List[Dict], risk_level: str) -> List[str]:
        """Generate AI recommendations based on detected issues"""
        recs = []
        issue_types = {i['type'] for i in issues}

        if 'valgus_knee' in issue_types:
            recs.extend([
                'Fortalecer musculatura abductora y rotadora externa de cadera (glúteo medio y menor)',
                'Ejercicios de propiocepción y control neuromuscular de rodilla',
                'Revisar técnica en gestos deportivos específicos (saltos, cambios de dirección)',
                'Considerar uso de órtesis o taping rotuliano bajo supervisión médica',
            ])

        if 'hip_asymmetry' in issue_types:
            recs.extend([
                'Evaluación de dismetría de miembros inferiores por especialista',
                'Ejercicios de equilibrio y estabilización pélvica',
                'Análisis de plantillas ortopédicas si se confirma dismetría',
            ])

        if 'shoulder_asymmetry' in issue_types:
            recs.extend([
                'Trabajo de fortalecimiento y flexibilidad de cintura escapular',
                'Evaluar postura sedente y ergonomía del equipamiento deportivo',
            ])

        if 'lateral_deviation' in issue_types:
            recs.extend([
                'Evaluación radiológica de columna si la desviación persiste',
                'Ejercicios de Schroth o fisioterapia específica para escoliosis',
                'Seguimiento mensual con análisis postural digital',
            ])

        if risk_level in ('high', 'critical'):
            recs.insert(0, '⚠️ Se recomienda evaluación médica especializada en los próximos 7 días')
            recs.append('Reducir carga de entrenamiento hasta nueva evaluación')

        if not recs:
            recs.append('Mantener rutina actual. Continuar con evaluaciones periódicas.')

        return recs

    def _estimate_confidence(self, results) -> float:
        """Estimate model confidence from landmark visibility scores"""
        key_landmarks = [
            PoseLandmark.LEFT_KNEE, PoseLandmark.RIGHT_KNEE,
            PoseLandmark.LEFT_HIP, PoseLandmark.RIGHT_HIP,
            PoseLandmark.LEFT_SHOULDER, PoseLandmark.RIGHT_SHOULDER,
        ]
        visibilities = [
            results.pose_landmarks.landmark[lm.value].visibility
            for lm in key_landmarks
        ]
        return round(float(np.mean(visibilities)) * 100, 1)

    def draw_landmarks(self, image_path: str, keypoints: Dict, output_path: str) -> bool:
        """Draw pose landmarks on image and save"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f'No se pudo cargar la imagen: {image_path}')
            height, width = image.shape[:2]
            points = {
                landmark.value: (int(data['x'] * width), int(data['y'] * height))
                for landmark in PoseLandmark
                if (data := keypoints.get(landmark.name)) is not None
            }
            for connection in mp_pose.PoseLandmarksConnections.POSE_LANDMARKS:
                start = points.get(connection.start)
                end = points.get(connection.end)
                if start and end:
                    cv2.line(image, start, end, (37, 99, 235), 2)
            for point in points.values():
                cv2.circle(image, point, 3, (16, 185, 129), -1)
            if not cv2.imwrite(output_path, image):
                raise OSError(f'No se pudo guardar la imagen procesada: {output_path}')
            return True
        except Exception as e:
            logger.error(f'Error dibujando landmarks: {e}')
            return False

    def _error_result(self, msg: str) -> Dict:
        return {
            'success': False,
            'error': msg,
            'joint_angles': {},
            'asymmetries': {},
            'risk_score': None,
            'risk_level': None,
            'ai_confidence': None,
            'detected_issues': [],
            'recommendations': [],
            'keypoints_data': {},
            'processing_time_ms': 0,
        }

    def close(self):
        if self.pose:
            self.pose.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
