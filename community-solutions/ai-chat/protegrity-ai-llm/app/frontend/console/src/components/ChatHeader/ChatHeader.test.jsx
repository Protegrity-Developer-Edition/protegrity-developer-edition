import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ChatHeader from './ChatHeader';

describe('ChatHeader Component', () => {
  const mockAgents = [
    { id: 'agent-1', name: 'Research Agent', icon: '🔬', color: '#4A90E2' },
    { id: 'agent-2', name: 'Code Agent', icon: '💻', color: '#50C878' }
  ];

  const mockModels = [
    { id: 'gpt-4', name: 'GPT-4' },
    { id: 'claude', name: 'Claude' },
    { id: 'gemini', name: 'Gemini' }
  ];

  describe('Basic Rendering', () => {
    it('renders with default title', () => {
      render(<ChatHeader showHamburger={true} />);
      
      expect(screen.getByText('New chat')).toBeInTheDocument();
    });

    it('renders with custom title', () => {
      render(<ChatHeader title="Custom Conversation" showHamburger={true} />);
      
      expect(screen.getByText('Custom Conversation')).toBeInTheDocument();
    });

    it('renders logo when showHamburger is false', () => {
      const { container } = render(<ChatHeader showHamburger={false} />);
      
      const logo = container.querySelector('.header-logo-image');
      expect(logo).toBeInTheDocument();
      expect(logo?.getAttribute('src')).toBe('/images/white-logo.svg');
    });

    it('renders title when showHamburger is true', () => {
      render(<ChatHeader title="My Chat" showHamburger={true} />);
      
      expect(screen.getByText('My Chat')).toBeInTheDocument();
    });

    it('does not show title when showHamburger is false', () => {
      render(<ChatHeader title="Hidden Title" showHamburger={false} />);
      
      expect(screen.queryByText('Hidden Title')).not.toBeInTheDocument();
    });
  });

  describe('Agent Display', () => {
    it('displays agent name when conversation has primary_agent', () => {
      const conversation = {
        id: 'conv-1',
        primary_agent: 'agent-1',
        primary_llm: 'gpt-4'
      };

      render(
        <ChatHeader
          title="Test"
          showHamburger={true}
          conversation={conversation}
          agents={mockAgents}
          models={mockModels}
        />
      );
      
      expect(screen.getByText('Research Agent')).toBeInTheDocument();
    });

    it('displays agent icon when present', () => {
      const conversation = {
        id: 'conv-1',
        primary_agent: 'agent-1'
      };

      const { container } = render(
        <ChatHeader
          showHamburger={true}
          conversation={conversation}
          agents={mockAgents}
        />
      );
      
      expect(screen.getByText('🔬')).toBeInTheDocument();
      expect(container.querySelector('.agent-icon')).toBeInTheDocument();
    });

    it('applies agent color to border', () => {
      const conversation = {
        id: 'conv-1',
        primary_agent: 'agent-1'
      };

      const { container } = render(
        <ChatHeader
          showHamburger={true}
          conversation={conversation}
          agents={mockAgents}
        />
      );
      
      const agentPill = container.querySelector('.agent-pill');
      expect(agentPill).toBeInTheDocument();
      expect(agentPill?.style.borderColor).toBe('rgb(74, 144, 226)'); // #4A90E2 in RGB
    });

    it('uses default color when agent color is not specified', () => {
      const agentsWithoutColor = [
        { id: 'agent-3', name: 'Default Agent', icon: '⚡' }
      ];

      const conversation = {
        id: 'conv-1',
        primary_agent: 'agent-3'
      };

      const { container } = render(
        <ChatHeader
          showHamburger={true}
          conversation={conversation}
          agents={agentsWithoutColor}
        />
      );
      
      const agentPill = container.querySelector('.agent-pill');
      expect(agentPill?.style.borderColor).toBe('rgb(250, 90, 37)'); // #FA5A25 default
    });

    it('does not display agent when conversation has no primary_agent', () => {
      const conversation = {
        id: 'conv-1',
        primary_llm: 'gpt-4'
      };

      render(
        <ChatHeader
          showHamburger={true}
          conversation={conversation}
          agents={mockAgents}
          models={mockModels}
        />
      );
      
      expect(screen.queryByText('Research Agent')).not.toBeInTheDocument();
    });

    it('does not display agent when agent not found in agents array', () => {
      const conversation = {
        id: 'conv-1',
        primary_agent: 'non-existent-agent'
      };

      render(
        <ChatHeader
          showHamburger={true}
          conversation={conversation}
          agents={mockAgents}
        />
      );
      
      expect(screen.queryByText('Research Agent')).not.toBeInTheDocument();
      expect(screen.queryByText('Code Agent')).not.toBeInTheDocument();
    });
  });

  describe('Model Display', () => {
    it('displays model name when conversation has primary_llm', () => {
      const conversation = {
        id: 'conv-1',
        primary_llm: 'gpt-4'
      };

      render(
        <ChatHeader
          showHamburger={true}
          conversation={conversation}
          models={mockModels}
        />
      );
      
      expect(screen.getByText('GPT-4')).toBeInTheDocument();
    });

    it('displays model name when conversation has model_id', () => {
      const conversation = {
        id: 'conv-1',
        model_id: 'claude'
      };

      render(
        <ChatHeader
          showHamburger={true}
          conversation={conversation}
          models={mockModels}
        />
      );
      
      expect(screen.getByText('Claude')).toBeInTheDocument();
    });

    it('prefers primary_llm over model_id', () => {
      const conversation = {
        id: 'conv-1',
        primary_llm: 'gpt-4',
        model_id: 'claude'
      };

      render(
        <ChatHeader
          showHamburger={true}
          conversation={conversation}
          models={mockModels}
        />
      );
      
      expect(screen.getByText('GPT-4')).toBeInTheDocument();
      expect(screen.queryByText('Claude')).not.toBeInTheDocument();
    });

    it('does not display model when not found in models array', () => {
      const conversation = {
        id: 'conv-1',
        primary_llm: 'non-existent-model'
      };

      render(
        <ChatHeader
          showHamburger={true}
          conversation={conversation}
          models={mockModels}
        />
      );
      
      expect(screen.queryByText('GPT-4')).not.toBeInTheDocument();
      expect(screen.queryByText('Claude')).not.toBeInTheDocument();
    });
  });

  describe('Agent and Model Together', () => {
    it('displays both agent and model when both present', () => {
      const conversation = {
        id: 'conv-1',
        primary_agent: 'agent-1',
        primary_llm: 'gpt-4'
      };

      render(
        <ChatHeader
          showHamburger={true}
          conversation={conversation}
          agents={mockAgents}
          models={mockModels}
        />
      );
      
      expect(screen.getByText('Research Agent')).toBeInTheDocument();
      expect(screen.getByText('GPT-4')).toBeInTheDocument();
    });

    it('shows metadata section when agent or model is present', () => {
      const conversation = {
        id: 'conv-1',
        primary_agent: 'agent-1'
      };

      const { container } = render(
        <ChatHeader
          showHamburger={true}
          conversation={conversation}
          agents={mockAgents}
        />
      );
      
      expect(container.querySelector('.chat-header-meta')).toBeInTheDocument();
    });

    it('does not show metadata section when neither agent nor model present', () => {
      const conversation = {
        id: 'conv-1'
      };

      const { container } = render(
        <ChatHeader
          showHamburger={true}
          conversation={conversation}
          agents={mockAgents}
          models={mockModels}
        />
      );
      
      expect(container.querySelector('.chat-header-meta')).not.toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles missing conversation prop', () => {
      render(
        <ChatHeader
          showHamburger={true}
          agents={mockAgents}
          models={mockModels}
        />
      );
      
      expect(screen.getByText('New chat')).toBeInTheDocument();
    });

    it('handles empty agents array', () => {
      const conversation = {
        id: 'conv-1',
        primary_agent: 'agent-1'
      };

      render(
        <ChatHeader
          showHamburger={true}
          conversation={conversation}
          agents={[]}
        />
      );
      
      expect(screen.queryByText('Research Agent')).not.toBeInTheDocument();
    });

    it('handles empty models array', () => {
      const conversation = {
        id: 'conv-1',
        primary_llm: 'gpt-4'
      };

      render(
        <ChatHeader
          showHamburger={true}
          conversation={conversation}
          models={[]}
        />
      );
      
      expect(screen.queryByText('GPT-4')).not.toBeInTheDocument();
    });

    it('handles agent without icon', () => {
      const agentsWithoutIcon = [
        { id: 'agent-3', name: 'No Icon Agent', color: '#000000' }
      ];

      const conversation = {
        id: 'conv-1',
        primary_agent: 'agent-3'
      };

      render(
        <ChatHeader
          showHamburger={true}
          conversation={conversation}
          agents={agentsWithoutIcon}
        />
      );
      
      expect(screen.getByText('No Icon Agent')).toBeInTheDocument();
    });

    it('renders correctly with all props as defaults', () => {
      render(<ChatHeader showHamburger={true} />);
      
      // Should not crash and show default behavior
      expect(screen.getByText('New chat')).toBeInTheDocument();
    });

    it('handles undefined title gracefully', () => {
      render(<ChatHeader title={undefined} showHamburger={true} />);
      
      // Should use default title
      expect(screen.getByText('New chat')).toBeInTheDocument();
    });
  });

  describe('CSS Classes', () => {
    it('applies correct class to header', () => {
      const { container } = render(<ChatHeader />);
      
      expect(container.querySelector('.chat-header-bar')).toBeInTheDocument();
    });

    it('applies agent-pill class to agent display', () => {
      const conversation = {
        id: 'conv-1',
        primary_agent: 'agent-1'
      };

      const { container } = render(
        <ChatHeader
          showHamburger={true}
          conversation={conversation}
          agents={mockAgents}
        />
      );
      
      expect(container.querySelector('.agent-pill')).toBeInTheDocument();
    });

    it('applies model-pill class to model display', () => {
      const conversation = {
        id: 'conv-1',
        primary_llm: 'gpt-4'
      };

      const { container } = render(
        <ChatHeader
          showHamburger={true}
          conversation={conversation}
          models={mockModels}
        />
      );
      
      expect(container.querySelector('.model-pill')).toBeInTheDocument();
    });
  });
});
