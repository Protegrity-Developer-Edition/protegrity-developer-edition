"""Tests for user role resolution behavior."""

import pytest
from django.contrib.auth.models import Group, User

from apps.core.models import UserProfile
from apps.core.utils import get_user_role


@pytest.mark.django_db
def test_get_user_role_prefers_user_profile_role():
    user = User.objects.create_user(username="profile_role_user", password="test123")
    profile = user.profile
    profile.role = "PROTEGRITY"
    profile.save(update_fields=["role", "updated_at"])

    role = get_user_role(user)

    assert role == "PROTEGRITY"


@pytest.mark.django_db
def test_get_user_role_falls_back_to_groups_without_profile_override():
    user = User.objects.create_user(username="group_role_user", password="test123")
    profile = user.profile
    profile.role = "STANDARD"
    profile.save(update_fields=["role", "updated_at"])

    protegrity_group, _ = Group.objects.get_or_create(name="Protegrity Users")
    user.groups.add(protegrity_group)

    role = get_user_role(user)

    # profile role takes precedence over group fallback
    assert role == "STANDARD"
