import { useState, useRef, useEffect } from "react";
import "./UserMenu.css";

/**
 * UserMenu component displays user information and actions (Settings, Logout).
 * Shows as a clickable chip in the bottom-left of the sidebar.
 * 
 * @param {Object} props
 * @param {Object} props.user - Current user object { id, username, email, first_name, last_name, role, is_protegrity }
 * @param {Function} props.onOpenSettings - Callback when Settings is clicked
 * @param {Function} props.onLogout - Callback when Logout is clicked
 */
function UserMenu({ user, onOpenSettings, onLogout }) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => {
        document.removeEventListener("mousedown", handleClickOutside);
      };
    }
  }, [isOpen]);

  if (!user) {
    return null;
  }

  // Get user display name and initials
  const displayName = user.first_name && user.last_name
    ? `${user.first_name} ${user.last_name}`
    : user.username;
  
  const initials = user.first_name && user.last_name
    ? `${user.first_name[0]}${user.last_name[0]}`.toUpperCase()
    : user.username.substring(0, 2).toUpperCase();

  const handleToggle = () => {
    setIsOpen(!isOpen);
  };

  const handleSettingsClick = () => {
    setIsOpen(false);
    onOpenSettings();
  };

  const handleLogoutClick = () => {
    setIsOpen(false);
    onLogout();
  };

  return (
    <div className="user-menu" ref={menuRef}>
      <button
        className="user-menu__chip"
        onClick={handleToggle}
        aria-label="User menu"
        aria-expanded={isOpen}
      >
        <div className="user-menu__avatar">
          {initials}
        </div>
        <div className="user-menu__info">
          <div className="user-menu__name">{displayName}</div>
          <div className="user-menu__role">{user.role}</div>
        </div>
      </button>

      {isOpen && (
        <div className="user-menu__dropdown">
          <button
            className="user-menu__item"
            onClick={handleSettingsClick}
          >
            <span className="user-menu__item-icon">⚙️</span>
            Settings
          </button>
          <button
            className="user-menu__item user-menu__item--logout"
            onClick={handleLogoutClick}
          >
            <span className="user-menu__item-icon">🚪</span>
            Logout
          </button>
        </div>
      )}
    </div>
  );
}

export default UserMenu;
