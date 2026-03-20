import { useState, useEffect, useRef } from "react";
import "./App.css";
import "./styles/loading.css";
import Sidebar from "./components/Sidebar/Sidebar";
import ChatHeader from "./components/ChatHeader/ChatHeader";
import ChatMessage from "./components/ChatMessage/ChatMessage";
import ChatInput from "./components/ChatInput/ChatInput";
import WelcomeScreen from "./components/WelcomeScreen/WelcomeScreen";
import ErrorBanner from "./components/ErrorBanner/ErrorBanner";
import UserSettingsModal from "./components/UserSettingsModal";
import LoginForm from "./components/LoginForm";
import Button from "./components/common/Button";
import Icon from "./components/common/Icon";
import { POLLING } from "./constants/ui";
import useAuthSession from "./hooks/useAuthSession";
import { 
  sendChatMessage, 
  pollConversation, 
} from "./api/client";
import { 
  fetchConversations, 
  deleteConversation as deleteConversationAPI,
  transformConversation 
} from "./api/conversations";

function App() {
  // State
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState(null); // { code, message } or null
  const [pendingMessageIndex, setPendingMessageIndex] = useState(null);
  const [availableModels, setAvailableModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState(null);
  const [availableAgents, setAvailableAgents] = useState([]);
  const [selectedAgents, setSelectedAgents] = useState([]); // Multi-select for agents
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [userSettingsOpen, setUserSettingsOpen] = useState(false);
  
  // Refs
  const pollingIntervalRef = useRef(null);
  const messagesEndRef = useRef(null);

  const activeConversation = conversations.find(
    (conv) => conv.id === activeConversationId
  );

  const {
    currentUser,
    isAuthenticated,
    authLoading,
    loginError,
    loginSubmitting,
    handleLogin,
    handleLogout,
  } = useAuthSession({
    onLogoutCleanup: () => {
      setConversations([]);
      setActiveConversationId(null);
      setMessages([]);
      setError(null);
      setSelectedModel(null);
      setSelectedAgents([]);
    },
  });

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const updateConversationTitle = (convId, firstMessage) => {
    return firstMessage.slice(0, 50) + (firstMessage.length > 50 ? "..." : "");
  };

  const updateConversationWithMessages = (convId, newMessages, newTitle = null) => {
    setConversations((prev) =>
      prev.map((conv) => {
        if (conv.id === convId) {
          const updates = { ...conv, messages: newMessages };
          if (newTitle && conv.title === "New chat") {
            updates.title = newTitle;
          }
          return updates;
        }
        return conv;
      })
    );
  };

  const handleNewChat = () => {
    setActiveConversationId(null);
    setMessages([]);
  };

  const handleSelectConversation = async (conversationId) => {
    // Check if conversation exists in local state
    const conversation = conversations.find((c) => c.id === conversationId);
    if (!conversation) {
      return;
    }
    
    // Set active conversation immediately
    setActiveConversationId(conversationId);
    
    // If conversation already has messages loaded, use them
    if (conversation.messages && conversation.messages.length > 0) {
      setMessages(conversation.messages);
      return;
    }
    
    // Otherwise, fetch full conversation with messages from API
    try {
      const { fetchConversation: fetchConv } = await import('./api/conversations');
      const fullConversation = await fetchConv(conversationId);
      
      // Transform messages from snake_case to camelCase
      const transformedMessages = (fullConversation.messages || []).map((msg) => {
        return {
          role: msg.role,
          content: msg.content,
          pending: msg.pending || false,
          blocked: msg.blocked || false,
          protegrityData: msg.protegrity_data || {},
          agent: msg.agent || null,
          llm_provider: msg.llm_provider || null,
        };
      });
      
      // Update local state with fetched messages
      setMessages(transformedMessages);
      
      // Update conversations array to cache the messages
      setConversations((prev) =>
        prev.map((conv) =>
          conv.id === conversationId
            ? { ...conv, messages: transformedMessages }
            : conv
        )
      );
      
    } catch (error) {
      setMessages([]);
    }
  };

  const handleDeleteConversation = async (conversationId) => {
    try {
      await deleteConversationAPI(conversationId);
      
      if (conversationId === activeConversationId) {
        setActiveConversationId(null);
        setMessages([]);
      }
      
      setConversations(prev => prev.filter(conv => conv.id !== conversationId));
    } catch (error) {
      setError({
        code: "conversation_delete_failed",
        message: "Failed to delete conversation. Please try again.",
      });
    }
  };

  const handleSendMessage = async (content) => {
    if (!content.trim()) return;
    if (isSending) return; // Prevent double send
    
    // Validate model selection for new conversations
    if (!activeConversationId && !selectedModel) {
      setError({
        code: 'no_model_selected',
        message: 'Please select a model before starting a new chat.',
      });
      return;
    }
    
    setError(null); // Clear any existing errors
    setIsSending(true);
    
    let conversationId = activeConversationId;
    
    const userMessage = { role: "user", content };
    const pendingAssistantMsg = { role: "assistant", content: "", pending: true };
    
    // Use functional update to get the LATEST messages state
    setMessages((currentMessages) => {
      const optimisticMessages = [...currentMessages, userMessage, pendingAssistantMsg];
      setPendingMessageIndex(optimisticMessages.length - 1);
      
      if (!conversationId) {
        // Create optimistic placeholder conversation (will be replaced with real UUID from backend)
        const tempId = `temp-${Date.now()}`;
        const newConversation = {
          id: tempId,
          title: "New chat",
          messages: optimisticMessages,
          createdAt: new Date(),
        };
        setConversations([newConversation, ...conversations]);
        setActiveConversationId(tempId);
        conversationId = null; // Send null to backend to create new conversation
      } else {
        // Update existing conversation with new messages
        setConversations((prev) =>
          prev.map((conv) =>
            conv.id === conversationId
              ? { ...conv, messages: optimisticMessages }
              : conv
          )
        );
      }
      
      return optimisticMessages;
    });
    
    setIsLoading(true);
    
    // Scroll to bottom after message is added
    setTimeout(scrollToBottom, 100);

    try {
      const response = await sendChatMessage({
        conversationId: conversationId, // Will be null for new conversations
        message: content,
        modelId: selectedModel?.id, // Always send selected model
        agentId: selectedAgents.length > 0 ? selectedAgents[0].id : null, // Send first agent (backend expects single agent)
        protegrityMode: "redact", // Can be "redact", "protect", or "none"
      });

      // Get the real conversation ID from backend (could be db_conversation_id for Fin or conversation_id for Bedrock)
      const realConversationId = response.db_conversation_id || response.conversation_id;
      
      // If this was a new conversation, update with real UUID from backend
      if (!activeConversationId) {
        setActiveConversationId(realConversationId);
        setConversations((prev) =>
          prev.map((conv) =>
            conv.id.startsWith("temp-")
              ? { ...conv, id: realConversationId }
              : conv
          )
        );
        conversationId = realConversationId;
      }

      // Store Protegrity data with the conversation
      const protegrityData = response.protegrity_data || {};

      // Check if message was blocked by guardrails
      if (response.status === "blocked") {
        setMessages((currentMessages) => {
          const userMsgWithData = { ...userMessage, protegrityData };
          const blockedMsg = response.messages?.find(m => m.role === "system") || {
            role: "system",
            content: "This message was blocked by security guardrails.",
            blocked: true
          };
          const blockedMsgWithData = { ...blockedMsg, protegrityData };
          const allMessages = [...currentMessages.slice(0, -2), userMsgWithData, blockedMsgWithData];
          
          updateConversationWithMessages(conversationId, allMessages, updateConversationTitle(conversationId, content));
          return allMessages;
        });
        
        setIsLoading(false);
        setPendingMessageIndex(null);
        return;
      }

      // Check if response is pending (Fin AI still processing)
      if (response.status === "pending") {
        setMessages((currentMessages) => {
          const userMsgWithData = { ...userMessage, protegrityData };
          const pendingMsgWithData = { role: "assistant", content: "", pending: true, protegrityData };
          const allMessages = [...currentMessages.slice(0, -2), userMsgWithData, pendingMsgWithData];
          
          updateConversationWithMessages(conversationId, allMessages, updateConversationTitle(conversationId, content));
          return allMessages;
        });
        
        setIsSending(false);
        startPolling(conversationId);
      } else {
        // Immediate response (e.g., Bedrock)
        setMessages((currentMessages) => {
          const backendMessages = response.messages || [];
          const messagesWithData = backendMessages.map(msg => ({ ...msg, protegrityData }));
          const allMessages = [...currentMessages.slice(0, -2), ...messagesWithData];
          
          updateConversationWithMessages(conversationId, allMessages, updateConversationTitle(conversationId, content));
          return allMessages;
        });
        
        setPendingMessageIndex(null);
      }
    } catch (error) {
      // Handle 401 unauthorized - auto logout
      if (error.httpStatus === 401) {
        handleLogout();
        setError({
          code: "session_expired",
          message: "Your session has expired. Please log in again."
        });
        return;
      }
      
      // Error is already structured by API client with code, message, httpStatus
      setError({
        code: error.code || "unknown_error",
        message: error.message || "Sorry, there was an error communicating with the backend."
      });
      
      // Remove pending message
      setMessages((currentMessages) => currentMessages.slice(0, -2));
      setPendingMessageIndex(null);
    } finally {
      setIsLoading(false);
      setIsSending(false);
    }
  };

  const startPolling = (convId) => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    setIsPolling(true);
    let pollCount = 0;

    pollingIntervalRef.current = setInterval(async () => {
      pollCount++;

      try {
        const result = await pollConversation(convId);

        if (result.status === "completed") {
          const protegrityOutput = result.protegrity_output || {};
          
          setMessages((prev) => {
            const updated = [...prev];
            if (pendingMessageIndex !== null && updated[pendingMessageIndex]) {
              const existingProtegrity = updated[pendingMessageIndex].protegrityData || {};
              updated[pendingMessageIndex] = {
                role: "assistant",
                content: result.response,
                pending: false,
                protegrityData: {
                  ...existingProtegrity,
                  output_processing: protegrityOutput
                }
              };
            }
            
            setConversations((prevConvs) =>
              prevConvs.map((conv) =>
                conv.id === activeConversationId ? { ...conv, messages: updated } : conv
              )
            );
            
            return updated;
          });

          setPendingMessageIndex(null);
          setIsPolling(false);
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        } else if (pollCount >= POLLING.maxAttempts) {
          setError({
            code: "poll_timeout",
            message: "Response timeout. Please try again."
          });
          
          // Remove pending message
          setMessages((prev) => prev.slice(0, -1));
          
          setPendingMessageIndex(null);
          setIsPolling(false);
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
      } catch (err) {
        // Error is already structured by API client
        setError({
          code: err.code || "poll_failed",
          message: err.message || "Failed to get response from assistant."
        });
        
        // Remove pending message
        setMessages((prev) => prev.slice(0, -1));
        
        setPendingMessageIndex(null);
        setIsPolling(false);
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    }, POLLING.interval);
  };

  // Restore messages when active conversation ID changes (for switching conversations)
  useEffect(() => {
    if (activeConversationId) {
      const conversation = conversations.find((c) => c.id === activeConversationId);
      if (conversation && conversation.messages) {
        setMessages(conversation.messages);
      }
    }
  }, [activeConversationId]);

  // Fetch conversations from database when user authenticates
  useEffect(() => {
    if (!isAuthenticated) {
      return; // Don't fetch if not authenticated
    }

    const loadConversations = async () => {
      try {
        const response = await fetchConversations(1, 100); // Get first 100 conversations
        const dbConversations = response.results || [];
        
        // Transform and sort by updated_at (most recent first)
        const transformed = dbConversations
          .map(transformConversation)
          .sort((a, b) => b.updatedAt - a.updatedAt);
        
        setConversations(transformed);
        
        // If user has conversations, automatically select the most recent one
        if (transformed.length > 0) {
          const mostRecentConv = transformed[0]; // Already sorted by updated_at DESC
          handleSelectConversation(mostRecentConv.id);
        }
      } catch (error) {
        // Start with empty conversations if load fails
        setConversations([]);
      }
    };
    
    loadConversations();
  }, [isAuthenticated]); // Run when authentication status changes

  // Fetch available models and agents on mount (only when authenticated)
  useEffect(() => {
    if (!isAuthenticated) return;
    
    const fetchModels = async () => {
      try {
        const { apiGet } = await import('./api/client');
        const data = await apiGet("/api/models/");
        const models = data.models || [];
        setAvailableModels(models);

        if (models.length === 0) {
          setSelectedModel(null);
          return;
        }

        // Keep current selection if still available; otherwise select first valid model.
        const currentSelectedId = selectedModel?.id;
        const selectedStillExists = currentSelectedId
          ? models.some((model) => model.id === currentSelectedId)
          : false;

        if (!selectedStillExists) {
          setSelectedModel(models[0]);
        }
      } catch (error) {
        setAvailableModels([]);
        setSelectedModel(null);
      }
    };

    const fetchAgents = async () => {
      try {
        const { apiGet } = await import('./api/client');
        const data = await apiGet("/api/agents/");
        setAvailableAgents(data.agents || []);
      } catch (error) {
        setAvailableAgents([]);
      }
    };

    fetchModels();
    fetchAgents();
  }, [isAuthenticated]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  // Auth gating - show loading or login before main app
  if (authLoading) {
    return (
      <div className="app-loading">
        <div className="app-loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <LoginForm
        onLogin={handleLogin}
        error={loginError}
        loading={loginSubmitting}
      />
    );
  }

  return (
    <div className="app-layout">
      {isSidebarOpen && (
        <div 
          className="sidebar-backdrop" 
          onClick={() => setIsSidebarOpen(false)}
        />
      )}
      
      {conversations.length > 0 && !isSidebarOpen && (
        <Button
          variant="icon"
          size="md"
          icon={<Icon name="chevronRight" size={16} />}
          onClick={() => setIsSidebarOpen(true)}
          title="Open menu"
          className="mobile-sidebar-open-btn"
        />
      )}
      
      {conversations.length > 0 && (
        <Sidebar
          conversations={conversations}
          activeConversationId={activeConversationId}
          onNewChat={handleNewChat}
          onSelectConversation={(id) => {
            handleSelectConversation(id);
            setIsSidebarOpen(false);
          }}
          onDeleteConversation={handleDeleteConversation}
          isOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
          agents={availableAgents}
          models={availableModels}
          currentUser={currentUser}
          onOpenSettings={() => setUserSettingsOpen(true)}
          onLogout={handleLogout}
        />
      )}
      
      <main className="app-main-content">
        <ChatHeader 
          title={activeConversation?.title || "New chat"} 
          showHamburger={messages.length > 0}
          conversation={activeConversation}
          agents={availableAgents}
          models={availableModels}
        />
        
        <div className="app-chat-area">
          {messages.length === 0 ? (
            <WelcomeScreen 
              userName="Dan" 
              onSend={handleSendMessage} 
              isLoading={isLoading}
              selectedModel={selectedModel}
              onModelChange={setSelectedModel}
              availableModels={availableModels}
              selectedAgents={selectedAgents}
              onAgentsChange={setSelectedAgents}
              availableAgents={availableAgents}
            />
          ) : (
            <div className="chat-messages-list">
              {messages.map((msg, idx) => (
                <ChatMessage 
                  key={idx} 
                  role={msg.role} 
                  content={msg.content}
                  pending={msg.pending}
                  protegrityData={msg.protegrityData}
                  agent={msg.agent}
                  llmProvider={msg.llm_provider}
                  agents={availableAgents}
                  models={availableModels}
                />
              ))}
              {isPolling && (
                <div className="chat-message chat-message-assistant pending">
                  <div className="chat-message-content">
                    <span className="typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {messages.length > 0 && (
          <ChatInput
            onSend={handleSendMessage}
            isLoading={isLoading}
            isSending={isSending}
            isPolling={isPolling}
            placeholder="What are we working on today?"
            selectedModel={selectedModel}
            onModelChange={setSelectedModel}
            availableModels={availableModels}
            selectedAgents={selectedAgents}
            onAgentsChange={setSelectedAgents}
            availableAgents={availableAgents}
          />
        )}
      </main>
      
      {error && <ErrorBanner error={error} onClose={() => setError(null)} />}
      
      <UserSettingsModal
        isOpen={userSettingsOpen}
        onClose={() => setUserSettingsOpen(false)}
        user={currentUser}
      />
    </div>
  );
}

export default App;
