import "./ChatHeader.css";

function ChatHeader({ title = "New chat", showHamburger = false, conversation, agents = [], models = [] }) {
  // Extract agent and model information from conversation
  const primaryAgentId = conversation?.primary_agent;
  const primaryLlmId = conversation?.primary_llm;
  
  const agent = agents.find(a => a.id === primaryAgentId);
  const model = models.find(m => m.id === primaryLlmId || m.id === conversation?.model_id);

  return (
    <header className="chat-header-bar">
      {showHamburger ? (
        <div className="chat-header-title">
          <h1>{title}</h1>
          {(agent || model) && (
            <div className="chat-header-meta">
              {agent && (
                <span className="agent-pill" style={{ borderColor: agent.color || '#FA5A25' }}>
                  {agent.icon && <span className="agent-icon">{agent.icon}</span>}
                  <span className="agent-name">{agent.name}</span>
                </span>
              )}
              {model && (
                <span className="model-pill">
                  <span className="model-name">{model.name}</span>
                </span>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="chat-header-logo">
          <img src="/images/white-logo.svg" alt="Protegrity" className="header-logo-image" />
        </div>
      )}
    </header>
  );
}

export default ChatHeader;
