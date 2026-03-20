const ICONS = {
  plus: "M12 5v14M5 12h14",
  chevronLeft: "M15 18l-6-6 6-6",
  chevronRight: "M9 18l6-6-6-6",
  chevronUp: "M18 15l-6-6-6 6",
  chevronDown: "M6 9l6 6 6-6",
  send: "M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z",
  check: "M20 6L9 17l-5-5",
  message: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",
  shield: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
  alert: "M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01",
  alertCircle: "M12 2a10 10 0 1 0 0 20 10 10 0 1 0 0-20zM12 8v4M12 16h.01",
  x: "M18 6L6 18M6 6l12 12",
  moreVertical: "M12 5v.01M12 12v.01M12 19v.01",
  moreHorizontal: "M5 12h.01M12 12h.01M19 12h.01",
  share: "M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8M16 6l-4-4-4 4M12 2v13",
  trash: "M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6",
};

function Icon({ name, size = 16, className = "", ...props }) {
  const path = ICONS[name];
  
  if (!path) {
    console.warn(`Icon "${name}" not found`);
    return null;
  }

  // Split multi-path definitions by 'M' and create separate paths
  const paths = path.split('M').filter(p => p.trim());
  
  return (
    <svg 
      width={size} 
      height={size} 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      {...props}
    >
      {paths.length > 1 ? (
        paths.map((p, i) => <path key={i} d={`M${p}`} />)
      ) : (
        <path d={path} />
      )}
    </svg>
  );
}

export default Icon;
