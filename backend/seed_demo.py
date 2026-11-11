"""Seed demo athletes and doctor user for PrevenIA development"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'prevenia_api.settings')
django.setup()

from users.models import User
from athletes.models import Athlete

# Create demo doctor user
doctor, created = User.objects.get_or_create(
    email='doctor@prevenia.com',
    defaults={
        'first_name': 'Carlos',
        'last_name': 'López',
        'role': User.MEDICO,
        'specialty': 'Medicina Deportiva y Biomecánica',
        'institution': 'Centro de Alto Rendimiento PrevenIA',
        'is_staff': True,
        'is_superuser': True,
    }
)
if created:
    doctor.set_password('prevenia123')
    doctor.save()
    print('Created doctor user: doctor@prevenia.com / prevenia123')
else:
    print('Doctor user exists')

# Create demo athletes
athletes_data = [
    {
        'first_name': 'María',
        'last_name': 'González',
        'email': 'maria.gonzalez@atleta.com',
        'sport': 'Fútbol',
        'team': 'Selección Femenina',
        'weight_kg': 62.5,
        'height_cm': 168.0,
        'gender': 'F',
        'risk_score': 68.0,
        'current_risk_level': 'high',
    },
    {
        'first_name': 'Pedro',
        'last_name': 'Ramírez',
        'email': 'pedro.ramirez@atleta.com',
        'sport': 'Atletismo / Velocidad',
        'team': 'Club Olímpico',
        'weight_kg': 74.0,
        'height_cm': 182.0,
        'gender': 'M',
        'risk_score': 35.0,
        'current_risk_level': 'medium',
    },
    {
        'first_name': 'Ana',
        'last_name': 'Martínez',
        'email': 'ana.martinez@atleta.com',
        'sport': 'CrossFit / Halterofilia',
        'team': 'Titan CrossFit',
        'weight_kg': 58.0,
        'height_cm': 163.0,
        'gender': 'F',
        'risk_score': 22.0,
        'current_risk_level': 'low',
    },
    {
        'first_name': 'Luis',
        'last_name': 'Torres',
        'email': 'luis.torres@atleta.com',
        'sport': 'Baloncesto',
        'team': 'Halcones BC',
        'weight_kg': 88.0,
        'height_cm': 195.0,
        'gender': 'M',
        'risk_score': 45.0,
        'current_risk_level': 'medium',
    },
]

for a_data in athletes_data:
    athlete, created = Athlete.objects.get_or_create(
        email=a_data['email'],
        defaults={**a_data, 'created_by': doctor, 'assigned_to': doctor}
    )
    if created:
        print(f"Created athlete: {athlete.full_name} ({athlete.sport})")
    else:
        print(f"Athlete exists: {athlete.full_name}")

print(f"Total athletes in DB: {Athlete.objects.count()}")
