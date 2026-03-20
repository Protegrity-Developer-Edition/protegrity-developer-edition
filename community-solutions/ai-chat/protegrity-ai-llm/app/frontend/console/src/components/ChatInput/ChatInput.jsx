import { useState, useRef, useEffect } from "react";
import Icon from "../common/Icon";
import Button from "../common/Button";
import useClickOutside from "../../hooks/useClickOutside";
import "./ChatInput.css";

function ChatInput({ onSend, isLoading = false, isSending = false, isPolling = false, placeholder = "What are we working on today?", selectedModel, onModelChange, availableModels = [], selectedAgents = [], onAgentsChange, availableAgents = [] }) {
  const [input, setInput] = useState("");
  const [showMenu, setShowMenu] = useState(false);
  const [menuTab, setMenuTab] = useState("models"); // "models" or "agents"
  const menuRef = useClickOutside(() => setShowMenu(false));
  const textareaRef = useRef(null);

  const disabled = isSending || isPolling;

  const toggleAgentSelection = (agent) => {
    const isSelected = selectedAgents.some(a => a.id === agent.id);
    if (isSelected) {
      // Remove agent
      onAgentsChange(selectedAgents.filter(a => a.id !== agent.id));
    } else {
      // Add agent
      onAgentsChange([...selectedAgents, agent]);
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading || disabled) return;
    
    onSend(trimmed);
    setInput("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="chat-input-container">
      <form className="chat-input-form" onSubmit={handleSubmit}>
        <div className="chat-input-wrapper">
          <div className="input-controls" ref={menuRef}>
            <Button
              type="button"
              variant="icon"
              size="md"
              icon={<Icon name="plus" size={20} />}
              onClick={() => setShowMenu(!showMenu)}
              title="Models & Agents"
              className="chat-input-menu-btn"
            />

            {showMenu && (
              <div className="unified-menu">
                <div className="menu-tabs">
                  <button
                    type="button"
                    className={`menu-tab ${menuTab === "models" ? "active" : ""}`}
                    onClick={() => setMenuTab("models")}
                  >
                    Models
                  </button>
                  <button
                    type="button"
                    className={`menu-tab ${menuTab === "agents" ? "active" : ""}`}
                    onClick={() => setMenuTab("agents")}
                  >
                    Agents
                  </button>
                </div>

                <div className="menu-content">
                  {menuTab === "models" ? (
                    <div className="menu-section">
                      {availableModels.map((model) => (
                        <button
                          key={model.id}
                          type="button"
                          className={`menu-option ${selectedModel?.id === model.id ? "selected" : ""}`}
                          onClick={() => {
                            onModelChange(model);
                            setShowMenu(false);
                          }}
                        >
                          <div className="menu-option-content">
                            <span className="menu-option-name">{model.name}</span>
                            <span className="menu-option-desc">{model.description}</span>
                          </div>
                          {selectedModel?.id === model.id && (
                            <Icon name="check" size={16} />
                          )}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="menu-section">
                      {availableAgents.length > 0 ? (
                        <>
                          <div className="menu-section-header">
                            <span className="menu-section-label">Select one or more agents (optional)</span>
                            {selectedAgents.length > 0 && (
                              <button
                                type="button"
                                className="menu-clear-btn"
                                onClick={() => onAgentsChange([])}
                              >
                                Clear all
                              </button>
                            )}
                          </div>
                          {availableAgents.map((agent) => {
                            const isSelected = selectedAgents.some(a => a.id === agent.id);
                            return (
                              <button
                                key={agent.id}
                                type="button"
                                className={`menu-option ${isSelected ? "selected" : ""}`}
                                onClick={() => toggleAgentSelection(agent)}
                              >
                                <div className="menu-option-content">
                                  <span className="menu-option-name">{agent.name}</span>
                                  <span className="menu-option-desc">{agent.description}</span>
                                </div>
                                {isSelected && (
                                  <Icon name="check" size={16} />
                                )}
                              </button>
                            );
                          })}
                        </>
                      ) : (
                        <div className="menu-option disabled">
                          <div className="menu-option-content">
                            <span className="menu-option-name">No agents available</span>
                            <span className="menu-option-desc">Configure agents in Django admin</span>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          <textarea
            ref={textareaRef}
            className="chat-input-field"
            placeholder={disabled ? "Thinking..." : placeholder}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={disabled}
          />

          <Button
            type="submit"
            variant="primary"
            size="md"
            icon={disabled ? (
              <svg className="spinner" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" opacity="0.25" />
                <path d="M21 12a9 9 0 01-9 9" strokeLinecap="round" />
              </svg>
            ) : (
              <Icon name="send" size={20} />
            )}
            disabled={!input.trim() || disabled}
            title={disabled ? "Thinking..." : "Send message"}
            className="chat-input-send-btn"
          />
        </div>
      </form>

      <div className="chat-input-footer">
        <span className="input-footer-text">
          Protegrity AI can make mistakes. Check important info.
        </span>
      </div>
    </div>
  );
}

export default ChatInput;
