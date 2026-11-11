"""Assessments URL routing"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PosturalAssessmentViewSet, AlertViewSet

router = DefaultRouter()
router.register(r'alerts', AlertViewSet, basename='alerts')
router.register(r'', PosturalAssessmentViewSet, basename='assessments')

urlpatterns = [
    path('', include(router.urls)),
]
