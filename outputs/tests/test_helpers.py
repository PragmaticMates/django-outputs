"""
Helper functions for tests.
"""
from django.contrib.auth import get_user_model


def create_test_users(count=5):
    """Create multiple test users."""
    User = get_user_model()
    users = []
    for i in range(count):
        user = User.objects.create_user(
            username=f'user{i}',
            email=f'user{i}@example.com',
            password='testpass123'
        )
        users.append(user)
    return users

