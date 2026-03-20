import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import Sidebar from './Sidebar';

describe('Sidebar Component', () => {
  const mockConversations = [
    { id: 'conv-1', title: 'First conversation', primary_agent: 'agent-1', primary_llm: 'gpt-4' },
    { id: 'conv-2', title: 'Second conversation', model_id: 'claude' },
    { id: 'conv-3', title: 'Very long conversation title that should be truncated properly' }
  ];

  const mockAgents = [
    { id: 'agent-1', name: 'Research Agent' },
    { id: 'agent-2', name: 'Code Agent' }
  ];

  const mockModels = [
    { id: 'gpt-4', name: 'GPT-4' },
    { id: 'claude', name: 'Claude' }
  ];

  const mockCurrentUser = {
    username: 'testuser',
    role: 'STANDARD'
  };

  const defaultProps = {
    conversations: mockConversations,
    activeConversationId: 'conv-1',
    onNewChat: vi.fn(),
    onSelectConversation: vi.fn(),
    onDeleteConversation: vi.fn(),
    isOpen: true,
    onClose: vi.fn(),
    agents: mockAgents,
    models: mockModels,
    currentUser: mockCurrentUser,
    onOpenSettings: vi.fn(),
    onLogout: vi.fn()
  };

  describe('Basic Rendering', () => {
    it('renders sidebar with conversations', () => {
      render(<Sidebar {...defaultProps} />);
      
      expect(screen.getByText('First conversation')).toBeInTheDocument();
      expect(screen.getByText('Second conversation')).toBeInTheDocument();
      expect(screen.getByText('Very long conversation title that should be truncated properly')).toBeInTheDocument();
    });

    it('renders New chat button', () => {
      render(<Sidebar {...defaultProps} />);
      
      expect(screen.getByText('New chat')).toBeInTheDocument();
    });

    it('shows active conversation with active class', () => {
      const { container } = render(<Sidebar {...defaultProps} />);
      
      const activeItem = container.querySelector('.sidebar-conversation-item.active');
      expect(activeItem).toBeInTheDocument();
      expect(activeItem?.textContent).toContain('First conversation');
    });

    it('renders empty state when no conversations', () => {
      render(<Sidebar {...defaultProps} conversations={[]} />);
      
      expect(screen.getByText('No conversations yet')).toBeInTheDocument();
    });

    it('applies sidebar-open class when isOpen is true', () => {
      const { container } = render(<Sidebar {...defaultProps} isOpen={true} />);
      
      expect(container.querySelector('.sidebar-open')).toBeInTheDocument();
    });

    it('does not apply sidebar-open class when isOpen is false', () => {
      const { container } = render(<Sidebar {...defaultProps} isOpen={false} />);
      
      expect(container.querySelector('.sidebar-open')).not.toBeInTheDocument();
    });
  });

  describe('Conversation Selection', () => {
    it('calls onSelectConversation when conversation is clicked', () => {
      const onSelectConversation = vi.fn();
      render(<Sidebar {...defaultProps} onSelectConversation={onSelectConversation} />);
      
      fireEvent.click(screen.getByText('Second conversation'));
      
      expect(onSelectConversation).toHaveBeenCalledWith('conv-2');
    });

    it('calls onNewChat when New chat button is clicked', () => {
      const onNewChat = vi.fn();
      render(<Sidebar {...defaultProps} onNewChat={onNewChat} />);
      
      fireEvent.click(screen.getByText('New chat'));
      
      expect(onNewChat).toHaveBeenCalled();
    });
  });

  describe('Conversation Metadata', () => {
    it('displays agent name when conversation has primary_agent', () => {
      render(<Sidebar {...defaultProps} />);
      
      expect(screen.getByText('Research Agent')).toBeInTheDocument();
    });

    it('displays model name when conversation has primary_llm', () => {
      render(<Sidebar {...defaultProps} />);
      
      expect(screen.getByText('GPT-4')).toBeInTheDocument();
    });

    it('displays model name when conversation has model_id', () => {
      render(<Sidebar {...defaultProps} />);
      
      expect(screen.getByText('Claude')).toBeInTheDocument();
    });

    it('shows separator between agent and model', () => {
      const { container } = render(<Sidebar {...defaultProps} />);
      
      const separator = container.querySelector('.meta-separator');
      expect(separator).toBeInTheDocument();
      expect(separator?.textContent).toBe('·');
    });

    it('handles conversation without agent or model', () => {
      render(<Sidebar {...defaultProps} />);
      
      // Third conversation has no agent or model
      expect(screen.getByText('Very long conversation title that should be truncated properly')).toBeInTheDocument();
    });
  });

  describe('Conversation Deletion', () => {
    it('shows delete menu on hover', () => {
      const { container } = render(<Sidebar {...defaultProps} />);
      
      const conversationItem = screen.getByText('First conversation').closest('.sidebar-conversation-item');
      
      // Hover over conversation
      fireEvent.mouseEnter(conversationItem);
      
      // Menu button should appear
      const menuBtn = container.querySelector('.conversation-menu-btn');
      expect(menuBtn).toBeInTheDocument();
    });

    it('hides delete menu when not hovering', () => {
      const { container } = render(<Sidebar {...defaultProps} />);
      
      const conversationItem = screen.getByText('First conversation').closest('.sidebar-conversation-item');
      
      // Not hovering - menu should not be visible
      const menuBtn = container.querySelector('.conversation-menu-btn');
      expect(menuBtn).not.toBeInTheDocument();
    });

    it('calls onDeleteConversation when delete is clicked', () => {
      const onDeleteConversation = vi.fn();
      const { container } = render(<Sidebar {...defaultProps} onDeleteConversation={onDeleteConversation} />);
      
      const conversationItem = screen.getByText('First conversation').closest('.sidebar-conversation-item');
      
      // Hover to show menu
      fireEvent.mouseEnter(conversationItem);
      
      // Click menu button
      const menuBtn = container.querySelector('.conversation-menu-btn');
      fireEvent.click(menuBtn);
      
      // Find and click delete button
      const deleteBtn = screen.getByText('Delete');
      fireEvent.click(deleteBtn);
      
      expect(onDeleteConversation).toHaveBeenCalledWith('conv-1');
    });

    it('does not show delete button when onDeleteConversation is not provided', () => {
      const { container } = render(<Sidebar {...defaultProps} onDeleteConversation={undefined} />);
      
      const conversationItem = screen.getByText('First conversation').closest('.sidebar-conversation-item');
      
      // Hover over conversation
      fireEvent.mouseEnter(conversationItem);
      
      // Menu button should not appear
      const menuBtn = container.querySelector('.conversation-menu-btn');
      expect(menuBtn).not.toBeInTheDocument();
    });
  });

  describe('Collapsed State', () => {
    it('toggles collapsed state when toggle button is clicked', () => {
      const { container } = render(<Sidebar {...defaultProps} />);
      
      // Find toggle button
      const toggleBtn = container.querySelector('.sidebar-toggle-btn');
      expect(toggleBtn).toBeInTheDocument();
      
      // Click to collapse
      fireEvent.click(toggleBtn);
      
      expect(container.querySelector('.sidebar-collapsed')).toBeInTheDocument();
    });

    it('hides New chat text when collapsed', () => {
      const { container } = render(<Sidebar {...defaultProps} />);
      
      // Initially shows text
      expect(screen.getByText('New chat')).toBeInTheDocument();
      
      // Collapse sidebar
      const toggleBtn = container.querySelector('.sidebar-toggle-btn');
      fireEvent.click(toggleBtn);
      
      // Text should be hidden
      expect(screen.queryByText('New chat')).not.toBeInTheDocument();
    });

    it('hides conversation details when collapsed', () => {
      const { container } = render(<Sidebar {...defaultProps} />);
      
      // Collapse sidebar
      const toggleBtn = container.querySelector('.sidebar-toggle-btn');
      fireEvent.click(toggleBtn);
      
      // Conversation details should not be visible
      expect(container.querySelector('.conversation-details')).not.toBeInTheDocument();
    });

    it('shows expand button when collapsed', () => {
      const { container } = render(<Sidebar {...defaultProps} />);
      
      // Collapse sidebar
      const toggleBtn = container.querySelector('.sidebar-toggle-btn');
      fireEvent.click(toggleBtn);
      
      // Should show expand button with icon
      const expandBtn = container.querySelector('.sidebar-logo-toggle-btn');
      expect(expandBtn).toBeInTheDocument();
    });

    it('expands sidebar when expand button is clicked', () => {
      const { container } = render(<Sidebar {...defaultProps} />);
      
      // Collapse sidebar
      const toggleBtn = container.querySelector('.sidebar-toggle-btn');
      fireEvent.click(toggleBtn);
      
      expect(container.querySelector('.sidebar-collapsed')).toBeInTheDocument();
      
      // Click expand button
      const expandBtn = container.querySelector('.sidebar-logo-toggle-btn');
      fireEvent.click(expandBtn);
      
      // Should be expanded now
      expect(container.querySelector('.sidebar-collapsed')).not.toBeInTheDocument();
    });
  });

  describe('User Menu Integration', () => {
    it('renders UserMenu when currentUser is provided', () => {
      render(<Sidebar {...defaultProps} />);
      
      // UserMenu should display the username
      expect(screen.getByText('testuser')).toBeInTheDocument();
    });

    it('does not render UserMenu when currentUser is null', () => {
      render(<Sidebar {...defaultProps} currentUser={null} />);
      
      // Username should not be displayed
      expect(screen.queryByText('testuser')).not.toBeInTheDocument();
    });
    
    it('hides UserMenu when sidebar is collapsed', () => {
      const { container } = render(<Sidebar {...defaultProps} />);
      
      // Collapse sidebar
      const toggleBtn = container.querySelector('.sidebar-toggle-btn');
      fireEvent.click(toggleBtn);
      
      // UserMenu should be hidden
      expect(screen.queryByText('testuser')).not.toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles empty agents array', () => {
      render(<Sidebar {...defaultProps} agents={[]} />);
      
      // Should still render conversations
      expect(screen.getByText('First conversation')).toBeInTheDocument();
    });

    it('handles empty models array', () => {
      render(<Sidebar {...defaultProps} models={[]} />);
      
      // Should still render conversations
      expect(screen.getByText('First conversation')).toBeInTheDocument();
    });

    it('handles missing currentUser', () => {
      render(<Sidebar {...defaultProps} currentUser={null} />);
      
      // Should still render sidebar
      expect(screen.getByText('New chat')).toBeInTheDocument();
    });

    it('handles undefined onClose callback', () => {
      render(<Sidebar {...defaultProps} onClose={undefined} />);
      
      // Should render without error
      expect(screen.getByText('New chat')).toBeInTheDocument();
    });

    it('handles clicking conversation when no active conversation', () => {
      const onSelectConversation = vi.fn();
      render(<Sidebar {...defaultProps} activeConversationId={null} onSelectConversation={onSelectConversation} />);
      
      fireEvent.click(screen.getByText('First conversation'));
      
      expect(onSelectConversation).toHaveBeenCalledWith('conv-1');
    });

    it('handles conversation with undefined title', () => {
      const conversationsWithUndefined = [
        { id: 'conv-1', title: undefined }
      ];
      
      render(<Sidebar {...defaultProps} conversations={conversationsWithUndefined} />);
      
      // Should render without crashing
      expect(screen.getByText('New chat')).toBeInTheDocument();
    });
  });

  describe('Menu Actions', () => {
    it('stops propagation when menu button is clicked', () => {
      const onSelectConversation = vi.fn();
      const { container } = render(<Sidebar {...defaultProps} onSelectConversation={onSelectConversation} />);
      
      const conversationItem = screen.getByText('First conversation').closest('.sidebar-conversation-item');
      
      // Hover to show menu
      fireEvent.mouseEnter(conversationItem);
      
      // Click menu button
      const menuBtn = container.querySelector('.conversation-menu-btn');
      fireEvent.click(menuBtn);
      
      // onSelectConversation should not be called
      expect(onSelectConversation).not.toHaveBeenCalled();
    });

    it('closes menu when clicking delete', () => {
      const { container } = render(<Sidebar {...defaultProps} />);
      
      const conversationItem = screen.getByText('First conversation').closest('.sidebar-conversation-item');
      
      // Hover and open menu
      fireEvent.mouseEnter(conversationItem);
      const menuBtn = container.querySelector('.conversation-menu-btn');
      fireEvent.click(menuBtn);
      
      // Menu should be open
      expect(screen.getByText('Delete')).toBeInTheDocument();
      
      // Click delete
      fireEvent.click(screen.getByText('Delete'));
      
      // Menu should close (delete button should no longer be visible)
      expect(screen.queryByText('Delete')).not.toBeInTheDocument();
    });
  });
});
