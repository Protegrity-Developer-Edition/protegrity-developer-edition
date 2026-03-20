import "./Button.css";

function Button({ 
  variant = "primary", // primary, secondary, icon, ghost
  size = "md", // sm, md, lg
  icon,
  children,
  className = "",
  disabled = false,
  ...props 
}) {
  const classNames = [
    "btn",
    `btn-${variant}`,
    `btn-${size}`,
    icon && !children && "btn-icon-only",
    className
  ].filter(Boolean).join(" ");

  return (
    <button 
      className={classNames}
      disabled={disabled}
      {...props}
    >
      {icon && <span className="btn-icon-wrapper">{icon}</span>}
      {children && <span className="btn-text">{children}</span>}
    </button>
  );
}

export default Button;
