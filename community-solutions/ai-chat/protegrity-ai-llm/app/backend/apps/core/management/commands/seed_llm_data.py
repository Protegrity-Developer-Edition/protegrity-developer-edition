"""
Django management command to seed initial LLM providers, agents, and tools.

Usage:
    python manage.py seed_llm_data
    python manage.py seed_llm_data --clear  # Clear existing data first
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.core.models import LLMProvider, Agent, Tool


class Command(BaseCommand):
    help = 'Seeds the database with initial LLM providers, agents, and tools'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            Tool.objects.all().delete()
            Agent.objects.all().delete()
            LLMProvider.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ Cleared existing data'))

        with transaction.atomic():
            self.seed_llm_providers()
            self.seed_tools()
            self.seed_agents()

        self.stdout.write(self.style.SUCCESS('\n✓ Database seeded successfully!'))

    def seed_llm_providers(self):
        """Seed LLM provider configurations."""
        self.stdout.write('\nSeeding LLM Providers...')

        # Remove legacy Fin/Intercom providers to keep runtime provider list vendor-neutral.
        removed_count, _ = LLMProvider.objects.filter(provider_type='intercom').delete()
        if removed_count:
            self.stdout.write(f"  Removed {removed_count} legacy Intercom/Fin provider records")

        llm_providers = [
            {
                'id': 'dummy',
                'name': 'Dummy LLM',
                'provider_type': 'custom',
                'description': 'Local dummy model for development and testing (no API keys required)',
                'model_identifier': 'dummy-1.0',
                'is_active': True,
                'requires_polling': False,
                'max_tokens': 4096,
                'supports_streaming': False,
                'cost_per_1k_input_tokens': 0.0,
                'cost_per_1k_output_tokens': 0.0,
                'display_order': 10,
                'configuration': {
                    'local': True,
                    'deterministic': True
                }
            },
            {
                'id': 'bedrock-claude',
                'name': 'Claude 3.5 Sonnet',
                'provider_type': 'bedrock',
                'description': 'Amazon Bedrock - Anthropic Claude 3.5 Sonnet',
                'model_identifier': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
                'is_active': True,
                'requires_polling': False,
                'max_tokens': 8192,
                'supports_streaming': True,
                'cost_per_1k_input_tokens': 0.003,
                'cost_per_1k_output_tokens': 0.015,
                'display_order': 3,
                'configuration': {
                    'region': 'us-east-1',
                    'temperature': 0.7
                }
            },
            {
                'id': 'gpt-4',
                'name': 'GPT-4',
                'provider_type': 'openai',
                'description': 'OpenAI GPT-4 - Advanced reasoning and analysis',
                'model_identifier': 'gpt-4-turbo-preview',
                'is_active': False,
                'requires_polling': False,
                'max_tokens': 128000,
                'supports_streaming': True,
                'cost_per_1k_input_tokens': 0.01,
                'cost_per_1k_output_tokens': 0.03,
                'display_order': 3,
                'configuration': {}
            },
            {
                'id': 'anthropic-claude-3-5-sonnet',
                'name': 'Claude 3.5 Sonnet (Anthropic)',
                'provider_type': 'anthropic',
                'description': 'Anthropic Claude 3.5 Sonnet (direct API)',
                'model_identifier': 'claude-3-5-sonnet-latest',
                'is_active': False,
                'requires_polling': False,
                'max_tokens': 8192,
                'supports_streaming': False,
                'cost_per_1k_input_tokens': 0.003,
                'cost_per_1k_output_tokens': 0.015,
                'display_order': 4,
                'configuration': {
                    'temperature': 0.7
                }
            },
            # Azure OpenAI Models
            {
                'id': 'azure-dalle3',
                'name': 'DALL-E 3 (Azure)',
                'provider_type': 'azure',
                'description': 'Azure OpenAI DALL-E 3 - Image generation model',
                'model_identifier': 'Dalle3',
                'is_active': True,
                'requires_polling': False,
                'max_tokens': 4096,
                'supports_streaming': False,
                'cost_per_1k_input_tokens': 0.0,
                'cost_per_1k_output_tokens': 0.0,
                'display_order': 10,
                'configuration': {
                    'temperature': 0.7,
                    'model_type': 'image'
                }
            },
            {
                'id': 'azure-davinci-002',
                'name': 'Davinci Test (Azure)',
                'provider_type': 'azure',
                'description': 'Azure OpenAI Code Davinci 002 - Legacy completion model',
                'model_identifier': 'Davinci-Test',
                'is_active': False,  # Disabled as shown in screenshot
                'requires_polling': False,
                'max_tokens': 8000,
                'supports_streaming': False,
                'cost_per_1k_input_tokens': 0.002,
                'cost_per_1k_output_tokens': 0.002,
                'display_order': 11,
                'configuration': {
                    'temperature': 0.7
                }
            },
            {
                'id': 'azure-gpt-35-turbo',
                'name': 'GPT-3.5 Turbo (Azure)',
                'provider_type': 'azure',
                'description': 'Azure OpenAI GPT-3.5 Turbo - Fast and efficient chat model',
                'model_identifier': 'gpt-35-turbo-chat',
                'is_active': True,
                'requires_polling': False,
                'max_tokens': 16385,
                'supports_streaming': True,
                'cost_per_1k_input_tokens': 0.0005,
                'cost_per_1k_output_tokens': 0.0015,
                'display_order': 12,
                'configuration': {
                    'temperature': 0.7,
                    'api_version': '2025-04-14'
                }
            },
            {
                'id': 'azure-gpt-4o',
                'name': 'GPT-4o (Azure)',
                'provider_type': 'azure',
                'description': 'Azure OpenAI GPT-4o - Latest GPT-4 optimized model with vision capabilities',
                'model_identifier': 'gpt-4o',
                'is_active': True,
                'requires_polling': False,
                'max_tokens': 4096,
                'supports_streaming': True,
                'cost_per_1k_input_tokens': 0.005,
                'cost_per_1k_output_tokens': 0.015,
                'display_order': 1,
                'configuration': {
                    'temperature': 0.7,
                    'api_version': '2024-11-20'
                }
            },
            {
                'id': 'azure-gpt-4o-test',
                'name': 'GPT-4o Test (Azure)',
                'provider_type': 'azure',
                'description': 'Azure OpenAI GPT-4o Test deployment - For testing and development',
                'model_identifier': 'gpt-4o-test',
                'is_active': True,
                'requires_polling': False,
                'max_tokens': 4096,
                'supports_streaming': True,
                'cost_per_1k_input_tokens': 0.005,
                'cost_per_1k_output_tokens': 0.015,
                'display_order': 14,
                'configuration': {
                    'temperature': 0.7,
                    'api_version': '2024-08-06'
                }
            },
        ]

        for llm_data in llm_providers:
            llm, created = LLMProvider.objects.update_or_create(
                id=llm_data['id'],
                defaults=llm_data
            )
            status = "Created" if created else "Updated"
            active_icon = "✓" if llm.is_active else "○"
            self.stdout.write(f"  {active_icon} {status}: {llm.name}")

    def seed_tools(self):
        """Seed tool configurations."""
        self.stdout.write('\nSeeding Tools...')

        tools = [
            {
                'id': 'protegrity-redact',
                'name': 'Protegrity Data Redaction',
                'tool_type': 'protegrity',
                'description': 'Redacts sensitive PII data using Protegrity guardrails',
                'is_active': True,
                'requires_auth': True,
                'function_schema': {
                    'name': 'redact_pii',
                    'description': 'Redact personally identifiable information from text',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'text': {
                                'type': 'string',
                                'description': 'Text to scan for PII'
                            },
                            'mode': {
                                'type': 'string',
                                'enum': ['redact', 'protect'],
                                'description': 'Protection mode'
                            }
                        },
                        'required': ['text']
                    }
                },
                'configuration': {
                    'api_url': 'http://localhost:8080',
                    'supported_entities': ['EMAIL', 'PHONE', 'SSN', 'CREDIT_CARD']
                }
            },
            {
                'id': 'protegrity-classify',
                'name': 'Protegrity Data Classification',
                'tool_type': 'protegrity',
                'description': 'Classifies and identifies sensitive data types',
                'is_active': True,
                'requires_auth': True,
                'function_schema': {
                    'name': 'classify_data',
                    'description': 'Identify types of sensitive data in text',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'text': {
                                'type': 'string',
                                'description': 'Text to classify'
                            }
                        },
                        'required': ['text']
                    }
                },
                'configuration': {
                    'api_url': 'http://localhost:8081'
                }
            },
            {
                'id': 'protegrity-guardrails',
                'name': 'Protegrity Semantic Guardrails',
                'tool_type': 'protegrity',
                'description': 'Validates prompts against security policies',
                'is_active': True,
                'requires_auth': True,
                'function_schema': {
                    'name': 'check_guardrails',
                    'description': 'Validate prompt against security policies',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'prompt': {
                                'type': 'string',
                                'description': 'Prompt to validate'
                            }
                        },
                        'required': ['prompt']
                    }
                },
                'configuration': {
                    'api_url': 'http://localhost:8082'
                }
            },
        ]

        for tool_data in tools:
            tool, created = Tool.objects.update_or_create(
                id=tool_data['id'],
                defaults=tool_data
            )
            status = "Created" if created else "Updated"
            active_icon = "✓" if tool.is_active else "○"
            self.stdout.write(f"  {active_icon} {status}: {tool.name}")

    def seed_agents(self):
        """Seed agent configurations."""
        self.stdout.write('\nSeeding Agents...')

        # Get LLM providers
        dummy_llm = LLMProvider.objects.get(id='dummy')
        bedrock_llm = LLMProvider.objects.get(id='bedrock-claude')
        azure_llms = list(LLMProvider.objects.filter(provider_type='azure'))

        # Get tools
        redact_tool = Tool.objects.get(id='protegrity-redact')
        classify_tool = Tool.objects.get(id='protegrity-classify')
        guardrails_tool = Tool.objects.get(id='protegrity-guardrails')

        agents_data = [
            {
                'id': 'data-protection-expert',
                'name': 'Data Protection Expert',
                'description': 'Specialized in data privacy, PII protection, and compliance',
                'system_prompt': '''You are a data protection expert specializing in privacy regulations (GDPR, CCPA, HIPAA) and PII protection. 
You help users understand how to protect sensitive data, implement data governance policies, and ensure compliance with privacy laws.
You have access to Protegrity data protection tools for demonstrating real-time PII detection and protection.''',
                'default_llm': dummy_llm,
                'is_active': True,
                'icon': 'shield',
                'color': '#FA5A25',
                'display_order': 1,
                'configuration': {
                    'temperature': 0.7,
                    'max_tokens': 2048
                },
                'tools': [redact_tool, classify_tool, guardrails_tool]
            },
            {
                'id': 'general-assistant',
                'name': 'General Assistant',
                'description': 'Helpful AI assistant for general queries',
                'system_prompt': '''You are a helpful, friendly AI assistant. You provide clear, accurate information and help users with a wide range of tasks.
You communicate in a professional yet approachable manner.''',
                'default_llm': dummy_llm,
                'is_active': True,
                'icon': 'chat',
                'color': '#4F46E5',
                'display_order': 2,
                'configuration': {
                    'temperature': 0.8,
                    'max_tokens': 4096
                },
                'tools': []
            },
        ]

        for agent_data in agents_data:
            tools = agent_data.pop('tools', [])
            
            agent, created = Agent.objects.update_or_create(
                id=agent_data['id'],
                defaults=agent_data
            )
            
            # Set allowed LLMs and tools (exclude legacy Fin/Intercom)
            allowed_llms = [dummy_llm, bedrock_llm, *azure_llms]
            agent.allowed_llms.set(allowed_llms)
            if tools:
                agent.tools.set(tools)
            
            status = "Created" if created else "Updated"
            active_icon = "✓" if agent.is_active else "○"
            tool_count = len(tools)
            self.stdout.write(f"  {active_icon} {status}: {agent.name} ({tool_count} tools)")
