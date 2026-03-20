# backend/apps/core/tests/test_models_api.py
import json
import os
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

User = get_user_model()


class ModelsAPITestCase(TestCase):
    """Tests for the models API endpoint"""

    def setUp(self):
        self._original_enabled_providers = os.environ.get("ENABLED_LLM_PROVIDERS")
        os.environ.pop("ENABLED_LLM_PROVIDERS", None)

        # Create a PROTEGRITY user for testing via Django Groups
        self.user = User.objects.create_user(
            username='testuser@example.com',
            password='testpass123'
        )
        protegrity_group, _ = Group.objects.get_or_create(name="Protegrity Users")
        self.user.groups.add(protegrity_group)
        self.user.profile.role = "PROTEGRITY"
        self.user.profile.save(update_fields=["role", "updated_at"])
        
        # Use APIClient and authenticate
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create test LLM providers (these tests expect specific models)
        from apps.core.models import LLMProvider
        LLMProvider.objects.create(
            id='azure-gpt-4o',
            name='GPT-4o (Azure)',
            provider_type='azure',
            description='Azure GPT-4o',
            is_active=True,
            min_role='STANDARD'
        )
        LLMProvider.objects.create(
            id='bedrock-claude',
            name='Claude (Bedrock)',
            provider_type='bedrock',
            description='AWS Bedrock Claude',
            is_active=True,
            min_role='PROTEGRITY'
        )

    def tearDown(self):
        if self._original_enabled_providers is None:
            os.environ.pop("ENABLED_LLM_PROVIDERS", None)
        else:
            os.environ["ENABLED_LLM_PROVIDERS"] = self._original_enabled_providers
        super().tearDown()

    def test_models_requires_get(self):
        """Models endpoint should only accept GET requests"""
        response = self.client.post('/api/models/')
        self.assertEqual(response.status_code, 405)
        data = response.json()
        self.assertIn('not allowed', data['detail'].lower())

    def test_models_returns_available_models(self):
        """Models endpoint should return list of available models"""
        response = self.client.get('/api/models/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn('models', data)
        self.assertIsInstance(data['models'], list)
        self.assertGreater(len(data['models']), 0)

    def test_models_structure(self):
        """Each model should have required fields"""
        response = self.client.get('/api/models/')
        data = response.json()
        
        for model in data['models']:
            self.assertIn('id', model)
            self.assertIn('name', model)
            self.assertIn('description', model)
            self.assertIn('provider', model)
            
            # Validate types
            self.assertIsInstance(model['id'], str)
            self.assertIsInstance(model['name'], str)
            self.assertIsInstance(model['description'], str)
            self.assertIsInstance(model['provider'], str)

    def test_models_includes_azure(self):
        """Models list should include Azure model"""
        response = self.client.get('/api/models/')
        data = response.json()
        
        model_ids = [m['id'] for m in data['models']]
        self.assertIn('azure-gpt-4o', model_ids)

    def test_models_includes_bedrock(self):
        """Models list should include Bedrock Claude"""
        response = self.client.get('/api/models/')
        data = response.json()
        
        model_ids = [m['id'] for m in data['models']]
        self.assertIn('bedrock-claude', model_ids)

    def test_models_filtered_by_enabled_provider_env(self):
        """When ENABLED_LLM_PROVIDERS is set, only matching provider models are returned."""
        os.environ["ENABLED_LLM_PROVIDERS"] = "azure_openai"

        response = self.client.get('/api/models/')
        self.assertEqual(response.status_code, 200)
        data = response.json()

        model_ids = [m['id'] for m in data['models']]
        self.assertIn('azure-gpt-4o', model_ids)
        self.assertNotIn('bedrock-claude', model_ids)
