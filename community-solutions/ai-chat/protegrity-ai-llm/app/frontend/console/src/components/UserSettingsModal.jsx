import "./UserSettingsModal.css";

/**
 * UserSettingsModal displays user profile and role information.
 * Read-only modal showing account details and permissions.
 * 
 * @param {Object} props
 * @param {boolean} props.isOpen - Whether modal is open
 * @param {Function} props.onClose - Callback to close modal
 * @param {Object} props.user - Current user object { id, username, email, first_name, last_name, role, is_protegrity }
 */
function UserSettingsModal({ isOpen, onClose, user }) {
  if (!isOpen || !user) {
    return null;
  }

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const displayName = user.first_name && user.last_name
    ? `${user.first_name} ${user.last_name}`
    : "";

  const roleDescriptions = {
    PROTEGRITY: "Full access to all models, agents, and tools. Can use advanced features and protegrity data protection.",
    STANDARD: "Access to Fin AI model only. Limited to basic chat functionality without agents or custom tools."
  };

  const rolePermissions = {
    PROTEGRITY: [
      "Access all LLM models (Fin AI, Claude, GPT-4, etc.)",
      "Use custom agents and tools",
      "Enable Protegrity data protection modes",
      "View and manage all conversations"
    ],
    STANDARD: [
      "Access Fin AI model only",
      "Basic chat functionality",
      "View own conversations"
    ]
  };

  return (
    <div className="settings-modal__backdrop" onClick={handleBackdropClick}>
      <div className="settings-modal__container">
        <div className="settings-modal__header">
          <h2 className="settings-modal__title">User Settings</h2>
          <button
            className="settings-modal__close"
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div className="settings-modal__content">
          {/* Profile Section */}
          <section className="settings-modal__section">
            <h3 className="settings-modal__section-title">Profile</h3>
            <div className="settings-modal__field-group">
              {displayName && (
                <div className="settings-modal__field">
                  <label className="settings-modal__label">Name</label>
                  <div className="settings-modal__value">{displayName}</div>
                </div>
              )}
              <div className="settings-modal__field">
                <label className="settings-modal__label">Username</label>
                <div className="settings-modal__value">{user.username}</div>
              </div>
              <div className="settings-modal__field">
                <label className="settings-modal__label">Email</label>
                <div className="settings-modal__value">{user.email || "Not provided"}</div>
              </div>
            </div>
          </section>

          {/* Role & Permissions Section */}
          <section className="settings-modal__section">
            <h3 className="settings-modal__section-title">Role & Permissions</h3>
            <div className="settings-modal__field-group">
              <div className="settings-modal__field">
                <label className="settings-modal__label">Role</label>
                <div className="settings-modal__value">
                  <span className={`settings-modal__role-badge settings-modal__role-badge--${user.role.toLowerCase()}`}>
                    {user.role}
                  </span>
                </div>
              </div>
              <div className="settings-modal__field">
                <label className="settings-modal__label">Description</label>
                <div className="settings-modal__value settings-modal__value--description">
                  {roleDescriptions[user.role] || "Standard user access"}
                </div>
              </div>
              <div className="settings-modal__field">
                <label className="settings-modal__label">Permissions</label>
                <ul className="settings-modal__permissions-list">
                  {(rolePermissions[user.role] || []).map((permission, index) => (
                    <li key={index} className="settings-modal__permission-item">
                      <span className="settings-modal__permission-icon">✓</span>
                      {permission}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>

          {/* Security Notice */}
          {user.is_protegrity && (
            <section className="settings-modal__section settings-modal__section--security">
              <div className="settings-modal__security-notice">
                <span className="settings-modal__security-icon">🔒</span>
                <div className="settings-modal__security-text">
                  <strong>Protegrity User</strong>
                  <p>You have access to Protegrity data protection features including input/output tokenization and secure data handling.</p>
                </div>
              </div>
            </section>
          )}
        </div>

        <div className="settings-modal__footer">
          <button
            className="settings-modal__button"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default UserSettingsModal;
