import "./ErrorBanner.css";
import Icon from "../common/Icon";

function ErrorBanner({ error, onClose }) {
  if (!error) return null;

  return (
    <div className="error-banner">
      <div className="error-banner-content">
        <Icon name="alertCircle" size={20} className="error-icon" />
        <div className="error-text">
          <strong>Error:</strong> {error.message || "Something went wrong"}
        </div>
      </div>
      <button 
        className="error-close-btn" 
        onClick={onClose}
        aria-label="Close error banner"
      >
        <Icon name="x" size={18} />
      </button>
    </div>
  );
}

export default ErrorBanner;
