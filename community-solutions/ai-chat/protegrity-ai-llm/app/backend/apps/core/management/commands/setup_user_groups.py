"""
Management command to set up user groups and migrate existing UserProfile roles.

This command:
1. Creates "Protegrity Users" and "Standard Users" groups
2. Migrates existing users from UserProfile.role to Groups
3. Assigns all existing PROTEGRITY users to "Protegrity Users" group

Usage:
    python manage.py setup_user_groups
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, User
from apps.core.models import UserProfile


class Command(BaseCommand):
    help = 'Set up user groups and migrate existing role data'

    def handle(self, *args, **options):
        self.stdout.write("Setting up user groups...")
        
        # Create groups
        protegrity_group, created = Group.objects.get_or_create(name="Protegrity Users")
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Created "Protegrity Users" group'))
        else:
            self.stdout.write('  "Protegrity Users" group already exists')
        
        standard_group, created = Group.objects.get_or_create(name="Standard Users")
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Created "Standard Users" group'))
        else:
            self.stdout.write('  "Standard Users" group already exists')
        
        # Migrate existing users from UserProfile.role to Groups
        self.stdout.write("\nMigrating existing users...")
        
        protegrity_count = 0
        standard_count = 0
        
        for profile in UserProfile.objects.all():
            user = profile.user
            
            if profile.role == "PROTEGRITY":
                if not user.groups.filter(name="Protegrity Users").exists():
                    user.groups.add(protegrity_group)
                    protegrity_count += 1
                    self.stdout.write(f'  ✓ Added {user.username} to Protegrity Users')
            else:  # STANDARD
                if not user.groups.filter(name="Standard Users").exists():
                    user.groups.add(standard_group)
                    standard_count += 1
                    self.stdout.write(f'  ✓ Added {user.username} to Standard Users')
        
        # Handle users without profiles (shouldn't happen, but just in case)
        users_without_profile = User.objects.exclude(profile__isnull=False)
        for user in users_without_profile:
            if not user.groups.exists():
                user.groups.add(standard_group)
                standard_count += 1
                self.stdout.write(f'  ✓ Added {user.username} to Standard Users (no profile)')
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Migration complete: {protegrity_count} Protegrity users, {standard_count} Standard users'
        ))
        
        self.stdout.write(self.style.WARNING(
            '\n⚠️  Note: UserProfile.role field is now deprecated. Use Django Groups instead.'
        ))
