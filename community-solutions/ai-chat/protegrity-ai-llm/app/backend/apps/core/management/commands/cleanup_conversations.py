"""
Django management command to clean up conversations and messages.

Usage:
    python manage.py cleanup_conversations --all           # Delete all conversations
    python manage.py cleanup_conversations --soft-deleted  # Delete only soft-deleted conversations
    python manage.py cleanup_conversations --days=7        # Delete conversations deleted > 7 days ago
    python manage.py cleanup_conversations --dry-run       # Preview what would be deleted
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.core.models import Conversation, Message


class Command(BaseCommand):
    help = 'Clean up conversations and messages from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Delete ALL conversations (hard delete)',
        )
        parser.add_argument(
            '--soft-deleted',
            action='store_true',
            help='Delete only soft-deleted conversations (hard delete)',
        )
        parser.add_argument(
            '--days',
            type=int,
            help='Delete conversations soft-deleted more than N days ago',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Determine which conversations to delete
        if options['all']:
            queryset = Conversation.objects.all()
            description = "ALL conversations"
        elif options['soft_deleted']:
            queryset = Conversation.objects.filter(deleted_at__isnull=False)
            description = "soft-deleted conversations"
        elif options['days'] is not None:
            days = options['days']
            cutoff_date = timezone.now() - timedelta(days=days)
            queryset = Conversation.objects.filter(
                deleted_at__isnull=False,
                deleted_at__lt=cutoff_date
            )
            description = f"conversations deleted more than {days} days ago"
        else:
            self.stdout.write(
                self.style.ERROR('Error: Must specify --all, --soft-deleted, or --days=N')
            )
            return

        # Count conversations and messages
        conversation_count = queryset.count()
        message_count = Message.objects.filter(conversation__in=queryset).count()

        if conversation_count == 0:
            self.stdout.write(self.style.SUCCESS('✓ No conversations to delete'))
            return

        # Preview
        self.stdout.write(f'\n{"="*60}')
        self.stdout.write(f'Cleanup Preview: {description}')
        self.stdout.write(f'{"="*60}')
        self.stdout.write(f'Conversations to delete: {conversation_count}')
        self.stdout.write(f'Messages to delete: {message_count}')
        self.stdout.write(f'{"="*60}\n')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No data was deleted'))
            
            # Show sample conversations
            sample = queryset[:5]
            if sample:
                self.stdout.write('\nSample conversations that would be deleted:')
                for conv in sample:
                    deleted_str = f" (deleted {conv.deleted_at})" if conv.deleted_at else ""
                    self.stdout.write(f'  - {conv.title[:50]} (ID: {conv.id}){deleted_str}')
                if conversation_count > 5:
                    self.stdout.write(f'  ... and {conversation_count - 5} more')
            return

        # Confirm deletion
        if not options['all']:
            # Auto-confirm for soft-deleted cleanup
            confirmed = True
        else:
            # Require confirmation for --all
            confirm = input(f'\n⚠️  Are you sure you want to permanently delete {conversation_count} conversations? (yes/no): ')
            confirmed = confirm.lower() == 'yes'

        if not confirmed:
            self.stdout.write(self.style.WARNING('Cancelled - No data was deleted'))
            return

        # Perform hard delete
        self.stdout.write('\nDeleting...')
        
        # Delete messages first (although CASCADE would handle it)
        deleted_messages = Message.objects.filter(conversation__in=queryset).delete()
        
        # Delete conversations
        deleted_conversations = queryset.delete()

        self.stdout.write(self.style.SUCCESS(f'\n✓ Deleted {deleted_conversations[0]} conversations'))
        self.stdout.write(self.style.SUCCESS(f'✓ Deleted {deleted_messages[0]} messages'))
        self.stdout.write(self.style.SUCCESS('\nCleanup completed successfully!'))
