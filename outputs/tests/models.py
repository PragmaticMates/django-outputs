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
    
    def get_absolute_url(self):
        """Return absolute URL for this model instance."""
        from django.urls import reverse
        try:
            return reverse('outputs:samplemodel-detail', kwargs={'pk': self.pk})
        except:
            # If URL doesn't exist, return a simple path
            return f'/samplemodel/{self.pk}/'

