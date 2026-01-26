"""
Test models for django-outputs tests.
"""
from django.db import models


class SampleModel(models.Model):
    """Simple test model for testing exports."""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    created = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = 'outputs'
        verbose_name = 'Sample Model'
        verbose_name_plural = 'Sample Models'

    def __str__(self):
        return self.name

