"""Athletes URL routing"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AthleteViewSet, InjuryRecordViewSet

router = DefaultRouter()
router.register(r'', AthleteViewSet, basename='athletes')
router.register(r'injuries', InjuryRecordViewSet, basename='injuries')

urlpatterns = [
    path('', include(router.urls)),
]
