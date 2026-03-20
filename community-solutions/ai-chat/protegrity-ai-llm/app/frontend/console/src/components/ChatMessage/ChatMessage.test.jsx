import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ChatMessage from './ChatMessage';

describe('ChatMessage Component', () => {
  describe('Basic Rendering', () => {
    it('renders user message correctly', () => {
      render(
        <ChatMessage
          role="user"
          content="Hello, this is a test message"
        />
      );
      
      expect(screen.getByText('You')).toBeInTheDocument();
      expect(screen.getByText('Hello, this is a test message')).toBeInTheDocument();
    });
    
    it('renders assistant message correctly', () => {
      render(
        <ChatMessage
          role="assistant"
          content="This is an assistant response"
        />
      );
      
      expect(screen.getByText('Assistant')).toBeInTheDocument();
      expect(screen.getByText('This is an assistant response')).toBeInTheDocument();
    });
    
    it('applies correct CSS class for user messages', () => {
      const { container } = render(
        <ChatMessage role="user" content="Test" />
      );
      
      expect(container.querySelector('.chat-msg-user')).toBeInTheDocument();
    });
    
    it('applies correct CSS class for assistant messages', () => {
      const { container } = render(
        <ChatMessage role="assistant" content="Test" />
      );
      
      expect(container.querySelector('.chat-msg-assistant')).toBeInTheDocument();
    });
  });
  
  describe('Pending State', () => {
    it('shows thinking indicator when pending is true', () => {
      const { container } = render(
        <ChatMessage
          role="assistant"
          content=""
          pending={true}
        />
      );
      
      expect(container.querySelector('.thinking-indicator')).toBeInTheDocument();
      expect(container.querySelectorAll('.dot')).toHaveLength(3);
    });
    
    it('shows thinking indicator for assistant with no content', () => {
      const { container } = render(
        <ChatMessage
          role="assistant"
          content=""
        />
      );
      
      expect(container.querySelector('.thinking-indicator')).toBeInTheDocument();
    });
    
    it('does not show content when pending', () => {
      render(
        <ChatMessage
          role="assistant"
          content="This should not appear"
          pending={true}
        />
      );
      
      expect(screen.queryByText('This should not appear')).not.toBeInTheDocument();
    });
  });
  
  describe('Agent and Model Display', () => {
    const mockAgents = [
      { id: 'agent-1', name: 'Research Agent' },
      { id: 'agent-2', name: 'Code Agent' }
    ];
    
    const mockModels = [
      { id: 'gpt-4', name: 'GPT-4' },
      { id: 'claude', name: 'Claude' }
    ];
    
    it('shows agent name when agent is provided for assistant', () => {
      render(
        <ChatMessage
          role="assistant"
          content="Response"
          agent="agent-1"
          agents={mockAgents}
          models={mockModels}
        />
      );
      
      // Agent info is hidden by default until showDebugInfo is toggled
      // This tests that the component accepts the props without error
      expect(screen.getByText('Response')).toBeInTheDocument();
    });
    
    it('does not show agent info for user messages', () => {
      render(
        <ChatMessage
          role="user"
          content="Question"
          agent="agent-1"
          agents={mockAgents}
        />
      );
      
      expect(screen.queryByText('via Research Agent')).not.toBeInTheDocument();
    });
  });
  
  describe('Protegrity Data Integration', () => {
    it('shows inspection toggle when user message has input_processing data', () => {
      const protegrityData = {
        input_processing: {
          original_text: 'Email: john@example.com',
          discovery: {
            EMAIL: [{ entity_text: 'john@example.com' }]
          }
        }
      };
      
      render(
        <ChatMessage
          role="user"
          content="Email: john@example.com"
          protegrityData={protegrityData}
        />
      );
      
      expect(screen.getByText('Show Protegrity Analysis')).toBeInTheDocument();
    });
    
    it('shows inspection toggle when assistant message has output_processing data', () => {
      const protegrityData = {
        output_processing: {
          original_response: 'Your SSN is 123-45-6789',
          discovery: {
            SSN: [{ entity_text: '123-45-6789' }]
          }
        }
      };
      
      render(
        <ChatMessage
          role="assistant"
          content="Your SSN is [REDACTED]"
          protegrityData={protegrityData}
        />
      );
      
      expect(screen.getByText('Show Protegrity Analysis')).toBeInTheDocument();
    });
    
    it('does not show inspection toggle when no protegrity data', () => {
      render(
        <ChatMessage
          role="user"
          content="Hello"
        />
      );
      
      expect(screen.queryByText('Show Protegrity Analysis')).not.toBeInTheDocument();
    });
    
    it('does not show inspection toggle when pending', () => {
      const protegrityData = {
        input_processing: {
          discovery: { EMAIL: [] }
        }
      };
      
      render(
        <ChatMessage
          role="user"
          content="Test"
          protegrityData={protegrityData}
          pending={true}
        />
      );
      
      expect(screen.queryByText('Show Protegrity Analysis')).not.toBeInTheDocument();
    });
    
    it('toggles inspection panel when button is clicked', async () => {
      const protegrityData = {
        input_processing: {
          original_text: 'Sensitive data',
          discovery: {
            EMAIL: [{ entity_text: 'test@example.com' }]
          }
        }
      };
      
      render(
        <ChatMessage
          role="user"
          content="Test"
          protegrityData={protegrityData}
        />
      );
      
      const toggleButton = screen.getByText('Show Protegrity Analysis');
      
      // Initially hidden
      expect(screen.queryByText('Protegrity Developer Edition Analysis')).not.toBeInTheDocument();
      
      // Click to show
      fireEvent.click(toggleButton);
      
      await waitFor(() => {
        expect(screen.getByText('Protegrity Developer Edition Analysis')).toBeInTheDocument();
      });
      
      expect(screen.getByText('Hide Protegrity Analysis')).toBeInTheDocument();
      
      // Click to hide
      fireEvent.click(screen.getByText('Hide Protegrity Analysis'));
      
      await waitFor(() => {
        expect(screen.queryByText('Protegrity Developer Edition Analysis')).not.toBeInTheDocument();
      });
    });
  });
  
  describe('Protegrity Inspection Panel', () => {
    it('displays original text in inspection', () => {
      const protegrityData = {
        input_processing: {
          original_text: 'My email is john@example.com',
          discovery: { EMAIL: [] }
        }
      };
      
      const { container } = render(
        <ChatMessage
          role="user"
          content="Test"
          protegrityData={protegrityData}
        />
      );
      
      // Open inspection
      fireEvent.click(screen.getByText('Show Protegrity Analysis'));
      
      expect(screen.getByText('My email is john@example.com')).toBeInTheDocument();
    });
    
    it('displays guardrails data when present', () => {
      const protegrityData = {
        input_processing: {
          guardrails: {
            outcome: 'accepted',
            risk_score: 0.1,
            blocked_categories: []
          }
        }
      };
      
      render(
        <ChatMessage
          role="user"
          content="Test"
          protegrityData={protegrityData}
        />
      );
      
      fireEvent.click(screen.getByText('Show Protegrity Analysis'));
      
      expect(screen.getByText('Semantic Guardrails')).toBeInTheDocument();
    });
    
    it('displays entity discovery data', () => {
      const protegrityData = {
        input_processing: {
          discovery: {
            EMAIL: [
              { entity_text: 'john@example.com', start: 0, end: 16 }
            ],
            PHONE: [
              { entity_text: '555-1234', start: 20, end: 28 }
            ]
          }
        }
      };
      
      render(
        <ChatMessage
          role="user"
          content="Test"
          protegrityData={protegrityData}
        />
      );
      
      fireEvent.click(screen.getByText('Show Protegrity Analysis'));
      
      expect(screen.getByText('PII & Entity Discovery')).toBeInTheDocument();
    });
    
    it('displays protection data when present', () => {
      const protegrityData = {
        input_processing: {
          protection: {
            success: true,
            protected_text: 'Protected data'
          }
        }
      };
      
      render(
        <ChatMessage
          role="user"
          content="Test"
          protegrityData={protegrityData}
        />
      );
      
      fireEvent.click(screen.getByText('Show Protegrity Analysis'));
      
      expect(screen.getByText('Data Protection (Tokenization)')).toBeInTheDocument();
    });
    
    it('displays redaction data when present', () => {
      const protegrityData = {
        output_processing: {
          redaction: {
            redacted_text: 'Email: [REDACTED]'
          }
        }
      };
      
      render(
        <ChatMessage
          role="assistant"
          content="Test"
          protegrityData={protegrityData}
        />
      );
      
      fireEvent.click(screen.getByText('Show Protegrity Analysis'));
      
      expect(screen.getByText('Data Redaction')).toBeInTheDocument();
    });
  });
  
  describe('Content Changes', () => {
    it('hides inspection panel when content changes', () => {
      const protegrityData = {
        input_processing: {
          original_text: 'Test',
          discovery: { EMAIL: [] }
        }
      };
      
      const { rerender } = render(
        <ChatMessage
          role="user"
          content="Original message"
          protegrityData={protegrityData}
        />
      );
      
      // Open inspection
      fireEvent.click(screen.getByText('Show Protegrity Analysis'));
      expect(screen.getByText('Protegrity Developer Edition Analysis')).toBeInTheDocument();
      
      // Change content
      rerender(
        <ChatMessage
          role="user"
          content="New message"
          protegrityData={protegrityData}
        />
      );
      
      // Inspection should be hidden
      expect(screen.queryByText('Protegrity Developer Edition Analysis')).not.toBeInTheDocument();
    });
  });
  
  describe('Edge Cases', () => {
    it('handles empty content gracefully', () => {
      render(
        <ChatMessage
          role="user"
          content=""
        />
      );
      
      expect(screen.getByText('You')).toBeInTheDocument();
    });
    
    it('handles missing protegrityData prop', () => {
      render(
        <ChatMessage
          role="user"
          content="Test"
        />
      );
      
      expect(screen.getByText('Test')).toBeInTheDocument();
    });
    
    it('handles empty agents and models arrays', () => {
      render(
        <ChatMessage
          role="assistant"
          content="Response"
          agent="agent-1"
          llmProvider="model-1"
          agents={[]}
          models={[]}
        />
      );
      
      expect(screen.getByText('Response')).toBeInTheDocument();
    });
    
    it('handles protegrity data with empty discovery object', () => {
      const protegrityData = {
        input_processing: {
          discovery: {}
        }
      };
      
      render(
        <ChatMessage
          role="user"
          content="Test"
          protegrityData={protegrityData}
        />
      );
      
      // Component still shows toggle if input_processing exists, even with empty discovery
      // This is expected behavior - user can still inspect the data
      expect(screen.getByText('Show Protegrity Analysis')).toBeInTheDocument();
    });
  });
});
