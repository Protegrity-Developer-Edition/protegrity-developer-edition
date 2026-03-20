import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./ChatMessage.css";
import Icon from "../common/Icon";
import Button from "../common/Button";

function ChatMessage({ role, content, pending, protegrityData, agent, llmProvider, agents = [], models = [] }) {
  const isUser = role === "user";
  const [showInspection, setShowInspection] = useState(false); // Start hidden by default
  const showDebugInfo = false;
  
  // Hide inspection when content changes (new message sent)
  useEffect(() => {
    setShowInspection(false);
  }, [content]);
  
  // Check if we have Protegrity data to show
  const hasProtegrityData = protegrityData && (
    (isUser && protegrityData.input_processing) ||
    (!isUser && protegrityData.output_processing)
  );
  
  const inspectionData = isUser 
    ? protegrityData?.input_processing 
    : protegrityData?.output_processing;
  
  // Find agent and model names for assistant messages
  const agentInfo = !isUser && agent ? agents.find(a => a.id === agent) : null;
  const modelInfo = !isUser && llmProvider ? models.find(m => m.id === llmProvider) : null;
  
  return (
    <div className={`chat-msg ${isUser ? "chat-msg-user" : "chat-msg-assistant"}`}>
      <div className="chat-msg-avatar">
        {isUser ? (
          <div className="avatar-user">DJ</div>
        ) : (
          <div className="avatar-assistant">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
          </div>
        )}
      </div>
      <div className="chat-msg-content">
        <div className="chat-msg-header">
          <div className="chat-msg-role">{isUser ? "You" : "Assistant"}</div>
          {!isUser && (agentInfo || modelInfo) && showDebugInfo && (
            <div className="chat-msg-meta-info">
              {agentInfo && <span className="meta-agent">via {agentInfo.name}</span>}
              {modelInfo && <span className="meta-model">· {modelInfo.name}</span>}
            </div>
          )}
        </div>
        <div className="chat-msg-text">
          {pending || (!isUser && !content) ? (
            <div className="thinking-indicator">
              <span className="dot"></span>
              <span className="dot"></span>
              <span className="dot"></span>
            </div>
          ) : isUser ? (
            // User messages: render as plain text
            content
          ) : (
            // Assistant messages: render as markdown
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
          )}
        </div>
        
        {showInspection && inspectionData && (
          <ProtegrityInspection data={inspectionData} isUser={isUser} />
        )}
        
        {hasProtegrityData && !pending && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowInspection(!showInspection)}
            icon={<Icon name={showInspection ? "chevronUp" : "chevronDown"} size={14} />}
            className="inspection-toggle inspection-toggle-bottom"
          >
            {showInspection ? "Hide" : "Show"} Protegrity Analysis
          </Button>
        )}
      </div>
    </div>
  );
}

function ProtegrityInspection({ data, isUser }) {
  return (
    <div className="protegrity-inspection">
      <div className="inspection-header">
        <Icon name="shield" size={16} />
        <span>Protegrity Developer Edition Analysis</span>
      </div>
      
      <div className="inspection-content">
        {/* Original Text */}
        {data.original_text && (
          <InspectionSection
            title={isUser ? "Original Input" : "Original Response"}
            content={data.original_text || data.original_response}
            type="original"
          />
        )}
        
        {/* Guardrails */}
        {data.guardrails && (
          <InspectionSection
            title="Semantic Guardrails"
            type="guardrails"
          >
            <GuardrailsDisplay data={data.guardrails} />
          </InspectionSection>
        )}
        
        {/* Entity Discovery */}
        {data.discovery && Object.keys(data.discovery).length > 0 && (
          <InspectionSection
            title="PII & Entity Discovery"
            type="discovery"
          >
            <EntityDiscoveryDisplay entities={data.discovery} />
          </InspectionSection>
        )}
        
        {/* Protection */}
        {data.protection && data.protection.success !== false && (
          <InspectionSection
            title="Data Protection (Tokenization)"
            type="protection"
          >
            <ProtectionDisplay data={data.protection} />
          </InspectionSection>
        )}
        
        {/* Redaction */}
        {data.redaction && (
          <InspectionSection
            title="Data Redaction"
            type="redaction"
          >
            <RedactionDisplay
              originalText={data.original_text || data.original_response}
              redactedText={data.processed_text || data.processed_response}
            />
          </InspectionSection>
        )}
        
        {/* Processed Text Sent to LLM */}
        {isUser && data.processed_text && (
          <InspectionSection
            title="Text Sent to LLM"
            content={data.processed_text}
            type="processed"
            highlight={true}
          />
        )}
        
        {/* Block Status */}
        {data.should_block && (
          <div className="inspection-alert inspection-alert-danger">
            <Icon name="alert" size={16} />
            <span>This message was blocked by guardrails</span>
          </div>
        )}
        
        {data.should_filter && (
          <div className="inspection-alert inspection-alert-warning">
            <Icon name="alert" size={16} />
            <span>This response triggered security filters</span>
          </div>
        )}
        
        {/* Learn More Link */}
        <div className="inspection-footer">
          <Icon name="shield" size={14} />
          <span>Powered by Protegrity Developer Edition</span>
          <a 
            href="https://www.protegrity.com/developers" 
            target="_blank" 
            rel="noopener noreferrer"
            className="inspection-learn-more"
          >
            Learn more →
          </a>
        </div>
      </div>
    </div>
  );
}

function InspectionSection({ title, content, children, type, highlight }) {
  return (
    <div className={`inspection-section inspection-section-${type}`}>
      <div className="inspection-section-title">{title}</div>
      <div className={`inspection-section-content ${highlight ? 'highlight' : ''}`}>
        {content ? (
          <pre className="inspection-text">{content}</pre>
        ) : (
          children
        )}
      </div>
    </div>
  );
}

function GuardrailsDisplay({ data }) {
  const outcome = data.outcome || "unknown";
  const riskScore = data.risk_score || 0;
  const signals = data.policy_signals || [];
  
  return (
    <div className="guardrails-display">
      <div className="guardrails-row">
        <span className="label">Outcome:</span>
        <span className={`badge badge-${outcome === 'rejected' ? 'danger' : 'success'}`}>
          {outcome.toUpperCase()}
        </span>
      </div>
      <div className="guardrails-row">
        <span className="label">Risk Score:</span>
        <span className="risk-score">{riskScore.toFixed(2)}</span>
        <div className="risk-bar">
          <div 
            className="risk-bar-fill" 
            style={{ width: `${riskScore * 100}%` }}
          />
        </div>
      </div>
      {signals.length > 0 && (
        <div className="guardrails-row">
          <span className="label">Policy Signals:</span>
          <div className="policy-signals">
            {signals.map((signal, idx) => (
              <span key={idx} className="badge badge-warning">{signal}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function EntityDiscoveryDisplay({ entities }) {
  const entityTypes = Object.keys(entities);
  
  if (entityTypes.length === 0) {
    return <div className="no-data">No sensitive entities detected</div>;
  }
  
  return (
    <div className="entity-discovery">
      {entityTypes.map(entityType => (
        <div key={entityType} className="entity-type-group">
          <div className="entity-type-header">
            <span className="badge badge-info">{entityType}</span>
            <span className="entity-count">
              {entities[entityType].length} found
            </span>
          </div>
          <div className="entity-instances">
            {entities[entityType].slice(0, 3).map((instance, idx) => (
              <div key={idx} className="entity-instance">
                <span className="entity-score">
                  {(instance.score * 100).toFixed(0)}% confidence
                </span>
                <span className="entity-location">
                  Position: {instance.location?.start_index}-{instance.location?.end_index}
                </span>
              </div>
            ))}
            {entities[entityType].length > 3 && (
              <div className="entity-more">
                +{entities[entityType].length - 3} more
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function ProtectionDisplay({ data }) {
  if (data.error || data.success === false) {
    return (
      <div className="protection-error">
        <Icon name="alert" size={16} />
        <span>Protection failed: {data.error || "Unknown error"}</span>
        <div className="error-hint">
          Ensure DEV_EDITION_EMAIL, DEV_EDITION_PASSWORD, and DEV_EDITION_API_KEY are configured.
        </div>
      </div>
    );
  }
  
  return (
    <div className="protection-success">
      <Icon name="check" size={16} />
      <span>Sensitive data tokenized successfully</span>
    </div>
  );
}

function RedactionDisplay({ originalText, redactedText }) {
  return (
    <div className="redaction-display">
      <div className="redaction-compare">
        <div className="redaction-before">
          <div className="redaction-label">Before Redaction:</div>
          <pre className="inspection-text">{originalText}</pre>
        </div>
        <div className="redaction-arrow">→</div>
        <div className="redaction-after">
          <div className="redaction-label">After Redaction:</div>
          <pre className="inspection-text highlight">{redactedText}</pre>
        </div>
      </div>
    </div>
  );
}

export default ChatMessage;
