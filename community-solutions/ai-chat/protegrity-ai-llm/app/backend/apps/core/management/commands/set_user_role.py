"""
Management command to set user role (STANDARD or PROTEGRITY) via Django Groups.

Usage:
    python manage.py set_user_role username PROTEGRITY
    python manage.py set_user_role username STANDARD
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group


class Command(BaseCommand):
    help = 'Set user role via Django Groups (STANDARD or PROTEGRITY)'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username or email')
        parser.add_argument('role', type=str, choices=['STANDARD', 'PROTEGRITY'], 
                          help='Role to assign (STANDARD or PROTEGRITY)')

    def handle(self, *args, **options):
        username = options['username']
        role = options['role']
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User "{username}" does not exist')
        
        # Get or create groups
        protegrity_group, _ = Group.objects.get_or_create(name="Protegrity Users")
        standard_group, _ = Group.objects.get_or_create(name="Standard Users")
        
        # Remove from both groups first
        user.groups.remove(protegrity_group, standard_group)
        
        # Add to appropriate group
        if role == "PROTEGRITY":
            user.groups.add(protegrity_group)
            self.stdout.write(
                self.style.SUCCESS(f'✓ Added "{username}" to Protegrity Users group')
            )
        else:  # STANDARD
            user.groups.add(standard_group)
            self.stdout.write(
                self.style.SUCCESS(f'✓ Added "{username}" to Standard Users group')
            )
        
        # Show current groups
        group_names = ", ".join(user.groups.values_list('name', flat=True))
        self.stdout.write(f'  Current groups: {group_names or "None"}')
