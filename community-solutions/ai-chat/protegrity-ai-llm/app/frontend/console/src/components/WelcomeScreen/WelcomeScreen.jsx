import ChatInput from "../ChatInput/ChatInput";
import "./WelcomeScreen.css";

function WelcomeScreen({ userName = "Dan", onSend, isLoading = false, selectedModel, onModelChange, availableModels = [], selectedAgents, onAgentsChange, availableAgents = [] }) {
  return (
    <div className="welcome-screen">
      <div className="welcome-content">
        <h1 className="welcome-greeting">Hello!</h1>
        <h2 className="welcome-name">{userName}</h2>
        <p className="welcome-subtitle">What are we working on today?</p>
        
        <div className="welcome-input-container">
          <ChatInput
            onSend={onSend}
            isLoading={isLoading}
            placeholder="I am typing my input right now"
            selectedModel={selectedModel}
            onModelChange={onModelChange}
            availableModels={availableModels}
            selectedAgents={selectedAgents}
            onAgentsChange={onAgentsChange}
            availableAgents={availableAgents}
          />
        </div>
      </div>
    </div>
  );
}

export default WelcomeScreen;
