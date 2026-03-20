import { useState } from "react";
import Icon from "../common/Icon";
import Button from "../common/Button";
import UserMenu from "../UserMenu";
import { BREAKPOINTS } from "../../constants/ui";
import "./Sidebar.css";

function Sidebar({ 
  conversations, 
  activeConversationId, 
  onNewChat, 
  onSelectConversation, 
  onDeleteConversation,
  isOpen = false, 
  onClose,
  agents = [],
  models = [],
  currentUser = null,
  onOpenSettings,
  onLogout
}) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [hoveredConvId, setHoveredConvId] = useState(null);
  const [openMenuId, setOpenMenuId] = useState(null);

  const handleToggle = () => {
    // On mobile, close the sidebar; on desktop, toggle collapse
    if (window.innerWidth <= BREAKPOINTS.mobile) {
      onClose?.();
    } else {
      setIsCollapsed(!isCollapsed);
    }
  };

  const handleDeleteConversation = (e, conversationId) => {
    e.stopPropagation();
    if (onDeleteConversation) {
      onDeleteConversation(conversationId);
    }
    setOpenMenuId(null);
  };

  const handleToggleMenu = (e, conversationId) => {
    e.stopPropagation();
    setOpenMenuId(openMenuId === conversationId ? null : conversationId);
  };

  const handleShareConversation = (e, conversationId) => {
    e.stopPropagation();
    void conversationId;
    alert('Share functionality coming soon!');
    setOpenMenuId(null);
  };

  return (
    <aside className={`sidebar ${isOpen ? "sidebar-open" : ""} ${isCollapsed ? "sidebar-collapsed" : ""}`}>
      <div className="sidebar-header">
        <div className="sidebar-logo">
          {isCollapsed ? (
            <button
              type="button"
              className="sidebar-logo-toggle-btn"
              onClick={handleToggle}
              title="Expand sidebar"
            >
              <img src="/images/protegrity-icon.svg" alt="Protegrity" className="logo-icon-small" />
              <span className="sidebar-logo-toggle-overlay">
                <Icon name="chevronRight" size={16} />
              </span>
            </button>
          ) : (
            <img src="/images/white-logo.svg" alt="Protegrity" className="logo-image" />
          )}
        </div>
        {!isCollapsed && (
          <Button
            type="button"
            variant="icon"
            size="md"
            icon={<Icon name="chevronLeft" size={16} />}
            onClick={handleToggle}
            title="Collapse sidebar"
            className="sidebar-toggle-btn"
          />
        )}
      </div>

      <div className="sidebar-content">
        <Button
          type="button"
          variant="primary"
          size="md"
          icon={<Icon name="plus" size={20} />}
          onClick={onNewChat}
          className="sidebar-new-chat-btn"
        >
          {!isCollapsed && "New chat"}
        </Button>

        <div className="sidebar-divider" />

        <div className="sidebar-conversations">
          {conversations.length === 0 && (
            <div className="sidebar-empty">No conversations yet</div>
          )}
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className={`sidebar-conversation-item ${
                activeConversationId === conv.id ? "active" : ""
              }`}
              onMouseEnter={() => setHoveredConvId(conv.id)}
              onMouseLeave={() => setHoveredConvId(null)}
            >
              <button
                type="button"
                className="conversation-item-btn"
                onClick={() => {
                  onSelectConversation(conv.id);
                  // Close sidebar on mobile after selecting a conversation
                  if (window.innerWidth <= BREAKPOINTS.mobile) {
                    onClose?.();
                  }
                }}
                title={conv.title}
              >
                <Icon name="message" size={16} />
                {!isCollapsed && (
                  <div className="conversation-details">
                    <span className="conversation-title">{conv.title}</span>
                    {(conv.primary_agent || conv.primary_llm || conv.model_id) && (
                      <span className="conversation-meta">
                        {agents.find(a => a.id === conv.primary_agent)?.name && (
                          <span className="conversation-agent">
                            {agents.find(a => a.id === conv.primary_agent)?.name}
                          </span>
                        )}
                        {models.find(m => m.id === conv.primary_llm || m.id === conv.model_id)?.name && (
                          <>
                            {agents.find(a => a.id === conv.primary_agent) && <span className="meta-separator">·</span>}
                            <span className="conversation-model">
                              {models.find(m => m.id === conv.primary_llm || m.id === conv.model_id)?.name}
                            </span>
                          </>
                        )}
                      </span>
                    )}
                  </div>
                )}
              </button>
              {!isCollapsed && hoveredConvId === conv.id && onDeleteConversation && (
                <div className="conversation-menu-container">
                  <button
                    type="button"
                    className="conversation-menu-btn"
                    onClick={(e) => handleToggleMenu(e, conv.id)}
                    title="More options"
                    aria-label="More options"
                  >
                    <Icon name="moreHorizontal" size={16} />
                  </button>
                  {openMenuId === conv.id && (
                    <div className="conversation-dropdown-menu">
                      <button
                        type="button"
                        className="dropdown-menu-item"
                        onClick={(e) => handleShareConversation(e, conv.id)}
                      >
                        <Icon name="share" size={16} />
                        <span>Share</span>
                      </button>
                      <button
                        type="button"
                        className="dropdown-menu-item delete"
                        onClick={(e) => handleDeleteConversation(e, conv.id)}
                      >
                        <Icon name="trash" size={16} />
                        <span>Delete</span>
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {!isCollapsed && currentUser && (
        <UserMenu
          user={currentUser}
          onOpenSettings={onOpenSettings}
          onLogout={onLogout}
        />
      )}
    </aside>
  );
}

export default Sidebar;
