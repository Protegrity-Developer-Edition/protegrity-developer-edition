# Frontend Architecture Documentation

A comprehensive guide to the React-based frontend for the Protegrity AI chat interface.

---

## Table of Contents

1. [Overview](#overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Data Flow & State Management](#data-flow--state-management)
5. [Component Architecture](#component-architecture)
6. [API Integration](#api-integration)
7. [Data Interfaces](#data-interfaces)
8. [Design System](#design-system)
9. [Key Patterns](#key-patterns)
10. [React Concepts Explained](#react-concepts-explained)
11. [Development Workflow](#development-workflow)

---

## Overview

This is a **ChatGPT-style conversational interface** that allows users to interact with multiple LLM providers (Intercom Fin AI and Amazon Bedrock). The app manages conversations, handles real-time message streaming via polling, and provides a responsive UI that works on desktop and mobile.

**Key Features:**
- Multi-conversation management
- Model switching (Fin AI vs Bedrock)
- Real-time polling for async responses
- Mobile-responsive sidebar
- Persistent conversation history (in-memory)

---

## Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 19.0.0 | UI framework |
| Vite | 6.0.3 | Build tool & dev server |
| CSS Modules | Built-in | Component-scoped styling |
| Fetch API | Native | HTTP requests |

**No additional libraries** - This keeps the bundle small and reduces complexity.

---

## Project Structure

```
frontend/console/
├── public/
│   ├── images/              # Logo assets
│   │   ├── protegrity-icon.svg
│   │   ├── protegrity-icon-black.svg
│   │   └── white-logo.svg
│   └── vite.svg
├── src/
│   ├── main.jsx             # App entry point (React mounting)
│   ├── App.jsx              # Root component (state orchestration)
│   ├── App.css              # Global app layout styles
│   ├── index.css            # CSS reset & global styles
│   │
│   ├── api/
│   │   └── client.js        # API client (fetch wrapper)
│   │
│   ├── components/
│   │   ├── common/          # Reusable components
│   │   │   ├── Button.jsx   # Universal button component
│   │   │   ├── Button.css
│   │   │   └── Icon.jsx     # SVG icon system
│   │   │
│   │   ├── Sidebar/         # Conversation list sidebar
│   │   │   ├── Sidebar.jsx
│   │   │   └── Sidebar.css
│   │   │
│   │   ├── ChatHeader/      # Top navigation bar
│   │   │   ├── ChatHeader.jsx
│   │   │   └── ChatHeader.css
│   │   │
│   │   ├── ChatInput/       # Message input + model selector
│   │   │   ├── ChatInput.jsx
│   │   │   └── ChatInput.css
│   │   │
│   │   ├── ChatMessage/     # Individual message bubble
│   │   │   ├── ChatMessage.jsx
│   │   │   └── ChatMessage.css
│   │   │
│   │   └── WelcomeScreen/   # Empty state screen
│   │       ├── WelcomeScreen.jsx
│   │       └── WelcomeScreen.css
│   │
│   ├── hooks/
│   │   └── useClickOutside.js  # Custom hook for dropdown menus
│   │
│   ├── styles/
│   │   └── scrollbar.css    # Shared scrollbar styling
│   │
│   └── constants/
│       └── ui.js            # UI constants (breakpoints, sizes)
│
├── package.json
├── vite.config.js
├── eslint.config.js
└── index.html
```

### File Organization Pattern

- **Common components** (`/components/common/`) - Reusable UI primitives (Button, Icon)
- **Feature components** (`/components/{Feature}/`) - Domain-specific components with co-located CSS
- **Utilities** (`/hooks/`, `/styles/`, `/constants/`) - Shared logic and styling
- **API layer** (`/api/`) - Backend communication abstraction

---

## Data Flow & State Management

### State Architecture

This app uses **React hooks** for state management with a **unidirectional data flow** pattern. There's no Redux or external state library - all state lives in React components.

```
┌─────────────────────────────────────────────────────┐
│                     App.jsx                         │
│  (Root State Container)                             │
│                                                      │
│  State:                                              │
│  - conversations: Conversation[]                     │
│  - activeConversationId: string | null              │
│  - messages: Message[]                              │
│  - isLoading: boolean                               │
│  - selectedModel: Model                             │
│  - availableModels: Model[]                         │
│  - isSidebarOpen: boolean (mobile)                  │
│                                                      │
│  Methods:                                            │
│  - handleNewChat()                                   │
│  - handleSelectConversation(id)                     │
│  - handleSendMessage(content)                       │
│  - startPolling(conversationId)                     │
└─────────────────────────────────────────────────────┘
        │                    │                   │
        ▼                    ▼                   ▼
   ┌─────────┐        ┌──────────┐      ┌──────────────┐
   │ Sidebar │        │ChatHeader│      │  ChatInput   │
   │         │        │          │      │              │
   │ Props:  │        │ Props:   │      │ Props:       │
   │ - conv. │        │ - title  │      │ - onSend     │
   │ - onNew │        │          │      │ - isLoading  │
   │ - onSel │        │          │      │ - selected   │
   └─────────┘        └──────────┘      │   Model      │
                                         └──────────────┘
```

### State Location Decisions

**Why state lives in `App.jsx`:**

1. **Conversations** - Shared between Sidebar (list) and main area (display)
2. **Messages** - Displayed in ChatMessage components, updated by ChatInput
3. **selectedModel** - Affects ChatInput UI and backend requests
4. **isLoading** - Controls ChatInput submit button and WelcomeScreen

This is **"lifting state up"** - when multiple components need access to the same data, we move it to their common ancestor.

### Event Flow Example: Sending a Message

```
User types message in ChatInput
         ↓
ChatInput calls props.onSend(content)
         ↓
App.handleSendMessage() receives content
         ↓
1. Create user message object
2. Update local messages state
3. Call API: sendChatMessage()
         ↓
Backend returns response:
         ↓
IF response.status === "pending":
  - Add assistant message with pending: true
  - Start polling with startPolling()
         ↓
Poll every 1s (up to 60s):
  - Call pollConversation(id)
  - Check if response.status === "completed"
  - Update message with actual content
         ↓
ELSE (immediate response):
  - Add assistant message with content
         ↓
Update conversations array with new messages
         ↓
Re-render ChatMessage components with new data
```

---

## Component Architecture

### Component Hierarchy

```
App (root)
├── Sidebar
│   ├── Logo (button or image)
│   ├── Button (New Chat)
│   ├── Button (Collapse)
│   └── Conversation List Items
│
├── ChatHeader
│   └── Logo or Title
│
├── Main Content Area
│   ├── WelcomeScreen (if messages.length === 0)
│   │   ├── Greeting
│   │   ├── Suggested Prompts
│   │   └── ChatInput
│   │
│   └── Chat View (if messages.length > 0)
│       ├── ChatMessage (user)
│       ├── ChatMessage (assistant)
│       ├── ChatMessage (user)
│       └── ChatInput
│
└── Mobile Sidebar Toggle Button
```

---

## Component Reference

### 1. Common Components

#### `Button.jsx`

**Purpose:** Universal button component with multiple variants and sizes.

**Props:**

```javascript
{
  variant: 'primary' | 'secondary' | 'icon' | 'ghost',  // default: 'primary'
  size: 'sm' | 'md' | 'lg',                              // default: 'md'
  icon: ReactNode,                                       // Icon component
  children: ReactNode,                                   // Button text
  className: string,                                     // Additional CSS classes
  disabled: boolean,                                     // default: false
  ...props                                               // Any other <button> props
}
```

**Variants:**
- `primary` - Orange background, white text (CTAs)
- `secondary` - Transparent with border (secondary actions)
- `icon` - Icon with background/border (icon buttons)
- `ghost` - Transparent, no border (subtle actions)

**Sizes:**
- `sm` - 28px height
- `md` - 36px height
- `lg` - 44px height

**Usage Examples:**

```jsx
// Primary button
<Button variant="primary" onClick={handleSubmit}>
  Send
</Button>

// Icon button
<Button 
  variant="icon" 
  icon={<Icon name="plus" />}
  onClick={handleClick}
/>

// Icon + Text
<Button 
  variant="secondary"
  icon={<Icon name="chevronLeft" />}
>
  Back
</Button>
```

**Key Pattern:** This component uses the **composition pattern** - you can pass an icon, text, or both. The component automatically applies the right CSS classes based on what you provide.

---

#### `Icon.jsx`

**Purpose:** Centralized SVG icon system. Prevents inline SVG duplication.

**Props:**

```javascript
{
  name: 'plus' | 'chevronLeft' | 'chevronRight' | 'send' | 'check' | 'message',
  size: number,           // default: 16
  className: string,      // Additional CSS classes
  ...props                // Any other <svg> props
}
```

**Available Icons:**
- `plus` - Plus sign (add/new)
- `chevronLeft` - Left arrow
- `chevronRight` - Right arrow
- `send` - Paper airplane
- `check` - Checkmark
- `message` - Chat bubble

**Usage:**

```jsx
<Icon name="send" size={20} />
<Icon name="chevronRight" size={16} className="custom-class" />
```

**Implementation:** Icons are stored as SVG path strings in the `ICONS` object. The component generates an `<svg>` with the appropriate path.

---

### 2. Feature Components

#### `Sidebar.jsx`

**Purpose:** Collapsible sidebar showing conversation history and logo.

**Props:**

```javascript
{
  conversations: Conversation[],      // Array of conversation objects
  activeConversationId: string | null,
  onNewChat: () => void,
  onSelectConversation: (id: string) => void,
  isOpen: boolean,                    // Mobile sidebar state
  onClose: () => void                 // Close mobile sidebar
}
```

**Internal State:**

```javascript
const [isCollapsed, setIsCollapsed] = useState(false);  // Desktop collapse state
```

**Behavior:**
- **Desktop:** Hover to expand when collapsed (CSS-only), click logo to toggle
- **Mobile (< 768px):** Controlled by `isOpen` prop, overlay backdrop
- **Animations:** Smooth width transition (0.3s), text fade-in/out

**Event Handlers:**
- `handleToggle()` - Toggle collapsed state (desktop)
- Props callbacks trigger state changes in parent (App.jsx)

---

#### `ChatHeader.jsx`

**Purpose:** Top navigation bar showing logo (welcome) or conversation title (active chat).

**Props:**

```javascript
{
  title: string,          // Conversation title or "New chat"
  showHamburger: boolean  // Show mobile menu button (unused currently)
}
```

**Behavior:**
- Shows Protegrity logo when on welcome screen
- Shows conversation title when chat is active
- Fixed height: 70px (matches sidebar header)

---

#### `ChatInput.jsx`

**Purpose:** Message input with model selector dropdown.

**Props:**

```javascript
{
  onSend: (content: string) => void,
  isLoading: boolean,                 // Disables submit when true
  placeholder: string,                // default: "What are we working on today?"
  selectedModel: Model | null,
  onModelChange: (model: Model) => void,
  availableModels: Model[]
}
```

**Internal State:**

```javascript
const [input, setInput] = useState("");           // Textarea value
const [showMenu, setShowMenu] = useState(false);  // Dropdown visibility
const [menuTab, setMenuTab] = useState("models"); // Active tab (models/agents)
```

**Key Features:**
- **Auto-resize textarea** - Grows with content (via useEffect)
- **Enter to send** - Shift+Enter for new line
- **Model selector** - Dropdown with tabs (models/agents)
- **Click-outside detection** - Uses `useClickOutside` hook

**Event Handlers:**
- `handleSubmit()` - Calls `onSend(trimmedInput)`, resets input
- `handleKeyDown()` - Detects Enter key (without Shift)

**DOM Refs:**
- `textareaRef` - Used for auto-height calculation
- `menuRef` - Used for click-outside detection (from hook)

---

#### `ChatMessage.jsx`

**Purpose:** Individual message bubble (user or assistant).

**Props:**

```javascript
{
  role: 'user' | 'assistant',
  content: string,
  pending: boolean           // Show "thinking" animation
}
```

**Behavior:**
- **User messages** - Right-aligned, avatar with initials "DJ"
- **Assistant messages** - Left-aligned, bot icon avatar
- **Pending state** - Shows animated dots ("thinking" indicator)
- **Empty content** - Also shows "thinking" for assistant

**Styling:** Role-based CSS classes (`.chat-msg-user`, `.chat-msg-assistant`)

---

#### `WelcomeScreen.jsx`

**Purpose:** Empty state shown when no messages exist.

**Props:**

```javascript
{
  userName: string,
  onSend: (content: string) => void,
  isLoading: boolean,
  selectedModel: Model | null,
  onModelChange: (model: Model) => void,
  availableModels: Model[]
}
```

**Features:**
- Greeting message with user name
- Suggested prompt buttons (quick-start questions)
- Embedded ChatInput component

**Pattern:** This is a **container component** - it composes ChatInput but doesn't manage its own complex state.

---

## API Integration

### API Client (`api/client.js`)

**Purpose:** Abstraction layer for backend communication.

**Base Configuration:**

```javascript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";
```

**Functions:**

#### `apiGet(path)`
Generic GET request wrapper.

```javascript
const response = await apiGet("/health/");
// Returns parsed JSON
```

#### `apiPost(path, body)`
Generic POST request wrapper.

```javascript
const response = await apiPost("/chat/", { message: "Hello", model_id: "fin" });
// Returns parsed JSON
```

#### `sendChatMessage({ conversationId, message, modelId })`
Send a chat message to the backend.

**Request:**
```javascript
POST /api/chat/
{
  conversation_id: "conv-1234567890",  // Optional for new conversations
  message: "What is React?",
  model_id: "fin"                      // or "bedrock"
}
```

**Response (Immediate - Bedrock):**
```javascript
{
  status: "completed",
  conversation_id: "conv-1234567890",
  messages: [
    { role: "user", content: "What is React?" },
    { role: "assistant", content: "React is a JavaScript library..." }
  ]
}
```

**Response (Pending - Fin AI):**
```javascript
{
  status: "pending",
  conversation_id: "fin-abc123"
}
```

#### `pollConversation(conversationId)`
Poll for Fin AI response completion.

**Request:**
```javascript
GET /api/chat/poll/fin-abc123/
```

**Response (Pending):**
```javascript
{
  status: "pending"
}
```

**Response (Completed):**
```javascript
{
  status: "completed",
  response: "React is a JavaScript library for building user interfaces..."
}
```

### Error Handling

All API functions use a shared `handleResponse()` function:

```javascript
async function handleResponse(response) {
  if (!response.ok) {
    // Parse error response
    const data = await response.json();
    const error = new Error(data.detail || "Request failed");
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return response.json();
}
```

**Pattern:** Errors are thrown and caught in component `try/catch` blocks.

---

## Data Interfaces

### Core Data Structures

#### `Conversation`

```javascript
{
  id: string,              // e.g., "conv-1701234567890"
  title: string,           // First message content (truncated)
  messages: Message[],
  createdAt: Date
}
```

**Created in:** `App.handleNewChat()`, `App.handleSendMessage()`

---

#### `Message`

```javascript
{
  role: 'user' | 'assistant',
  content: string,
  pending?: boolean        // Only for assistant messages being polled
}
```

**User Message:**
```javascript
{ role: "user", content: "Hello!" }
```

**Assistant Message (Complete):**
```javascript
{ role: "assistant", content: "Hi! How can I help?" }
```

**Assistant Message (Pending):**
```javascript
{ role: "assistant", content: "", pending: true }
```

---

#### `Model`

```javascript
{
  id: string,              // e.g., "fin", "bedrock"
  name: string,            // Display name
  description: string      // Model description
}
```

**Example:**
```javascript
{
  id: "fin",
  name: "Fin AI",
  description: "Intercom Fin AI with knowledge base"
}
```

**Fetched from:** `GET /api/models/` on app mount

---

### State Shape in App.jsx

```javascript
// All state variables in App component
const [conversations, setConversations] = useState([]);
// Type: Conversation[]
// Example: [
//   {
//     id: "conv-1701234567890",
//     title: "What is React?",
//     messages: [/* Message[] */],
//     createdAt: Date
//   }
// ]

const [activeConversationId, setActiveConversationId] = useState(null);
// Type: string | null
// Example: "conv-1701234567890"

const [messages, setMessages] = useState([]);
// Type: Message[]
// Example: [
//   { role: "user", content: "Hello" },
//   { role: "assistant", content: "Hi there!", pending: false }
// ]

const [isLoading, setIsLoading] = useState(false);
// Type: boolean

const [pendingMessageIndex, setPendingMessageIndex] = useState(null);
// Type: number | null
// Tracks which message is being polled

const [availableModels, setAvailableModels] = useState([]);
// Type: Model[]

const [selectedModel, setSelectedModel] = useState(null);
// Type: Model | null

const [isSidebarOpen, setIsSidebarOpen] = useState(false);
// Type: boolean (mobile only)

const pollingIntervalRef = useRef(null);
// Type: React.MutableRefObject<number | null>
// Stores setInterval ID for cleanup
```

---

## Design System

### CSS Variables (Global)

Defined in `index.css`:

```css
:root {
  /* Colors */
  --pg-orange: #fa5a25;    /* Primary brand color */
  --pg-bg: #0b0c10;        /* Dark background */
  --pg-surface: #151820;   /* Cards, panels */
  --pg-border: #252a36;    /* Borders */
  --pg-slate: #6d758d;     /* Secondary text */
  --pg-text: #e4e6eb;      /* Primary text */
  
  /* Spacing */
  --spacing-sm: 0.5rem;    /* 8px */
  --spacing-md: 1rem;      /* 16px */
  --spacing-lg: 1.5rem;    /* 24px */
  --spacing-xl: 2rem;      /* 32px */
}
```

### Responsive Breakpoints (JS Constants)

From `constants/ui.js`:

```javascript
export const BREAKPOINTS = {
  mobile: 768,      // < 768px = mobile
  tablet: 1024,     // 768-1024px = tablet
  desktop: 1280     // > 1280px = desktop
};
```

**Usage in CSS:**
```css
@media (max-width: 768px) {
  /* Mobile styles */
}
```

**Usage in JS:**
```javascript
import { BREAKPOINTS } from './constants/ui';

useEffect(() => {
  const isMobile = window.innerWidth < BREAKPOINTS.mobile;
}, []);
```

### Size Constants

```javascript
export const SIZES = {
  iconButton: 36,      // Default icon button
  iconButtonSm: 28,    // Small icon button
  iconButtonLg: 44,    // Large icon button
  icon: 16,            // Default icon size
  iconLg: 20,          // Large icon
  iconSm: 12,          // Small icon
};

export const HEADER_HEIGHT = "70px";  // Consistent header height
```

### Animation Patterns

**Sidebar Collapse:**
```css
.sidebar {
  width: 260px;
  transition: width 0.3s ease;
}

.sidebar.collapsed {
  width: 68px;
}

.sidebar-text {
  opacity: 1;
  transition: opacity 0.2s ease 0.1s; /* Delay on expand */
}

.sidebar.collapsed .sidebar-text {
  opacity: 0;
  transition: opacity 0.15s ease;     /* Faster fade on collapse */
}
```

**Thinking Indicator:**
```css
@keyframes dot-pulse {
  0%, 100% { opacity: 0.2; }
  50% { opacity: 1; }
}

.dot {
  animation: dot-pulse 1.4s infinite;
  animation-delay: calc(var(--delay) * 0.2s);
}
```

---

## Key Patterns

### 1. Custom Hooks

#### `useClickOutside(callback)`

**Purpose:** Detect clicks outside a DOM element (for closing dropdowns).

**How it works:**

1. Creates a `ref` to attach to the target element
2. Adds `mousedown` event listener to document
3. Checks if click target is outside `ref.current`
4. Calls `callback()` if click is outside
5. Cleans up listener on unmount

**Usage:**

```javascript
import useClickOutside from '../../hooks/useClickOutside';

function Dropdown() {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useClickOutside(() => setIsOpen(false));
  
  return (
    <div ref={ref}>
      {/* Dropdown content */}
    </div>
  );
}
```

**Why this pattern?** Avoids duplicating click-outside logic across components.

---

### 2. Component Composition

**Problem:** Button needs to support icons, text, or both.

**Solution:** Composition pattern - accept `icon` and `children` props.

```jsx
function Button({ icon, children, ...props }) {
  return (
    <button {...props}>
      {icon && <span className="btn-icon-wrapper">{icon}</span>}
      {children && <span className="btn-text">{children}</span>}
    </button>
  );
}
```

**Usage variations:**
```jsx
<Button icon={<Icon name="send" />} />           {/* Icon only */}
<Button>Send</Button>                             {/* Text only */}
<Button icon={<Icon name="send" />}>Send</Button> {/* Both */}
```

---

### 3. State Lifting

**Problem:** Both Sidebar and ChatInput need access to `selectedModel`.

**Solution:** Lift state to common parent (App.jsx).

```
App
├── selectedModel (state)
├── setSelectedModel (setter)
│
├── Sidebar (doesn't need it)
│
└── ChatInput
    ├── selectedModel (prop)
    └── onModelChange={setSelectedModel} (prop)
```

**Key Rule:** State should live in the **lowest common ancestor** of all components that need it.

---

### 4. Controlled Components

**Pattern:** Parent component controls child's state via props.

**Example:** ChatInput is controlled by App.jsx

```jsx
// App.jsx
<ChatInput
  onSend={handleSendMessage}     // Parent handles submission
  isLoading={isLoading}          // Parent controls loading state
  selectedModel={selectedModel}  // Parent controls selection
  onModelChange={setSelectedModel}
/>
```

**ChatInput doesn't know:**
- What happens when message is sent
- Whether backend request succeeded
- How to update conversation history

**ChatInput only knows:**
- How to render a textarea
- How to validate input
- How to call `props.onSend()`

This is the **separation of concerns** principle.

---

### 5. Polling Pattern

**Problem:** Fin AI responses are asynchronous (can take 10-60 seconds).

**Solution:** Client-side polling.

```javascript
const startPolling = (conversationId) => {
  let pollCount = 0;
  
  pollingIntervalRef.current = setInterval(async () => {
    pollCount++;
    
    const result = await pollConversation(conversationId);
    
    if (result.status === "completed") {
      // Update message with response
      clearInterval(pollingIntervalRef.current);
    } else if (pollCount >= POLLING.maxAttempts) {
      // Timeout after 60 seconds
      clearInterval(pollingIntervalRef.current);
    }
  }, POLLING.interval); // 1000ms
};
```

**Why `useRef` for interval ID?**
- Refs persist across re-renders
- Updating a ref doesn't trigger re-render
- Allows cleanup in `useEffect` on unmount

---

## React Concepts Explained

For developers new to React, here are the key concepts used in this app:

### JSX (JavaScript XML)

**What it is:** A syntax extension that lets you write HTML-like code in JavaScript.

```jsx
const element = <div className="box">Hello</div>;
```

**Behind the scenes:** This gets compiled to:

```javascript
const element = React.createElement('div', { className: 'box' }, 'Hello');
```

**Why it matters:** JSX makes UI code more readable and allows embedding JavaScript expressions.

**Examples in this app:**

```jsx
// Conditional rendering
{messages.length === 0 ? <WelcomeScreen /> : <ChatView />}

// List rendering
{messages.map((msg, idx) => <ChatMessage key={idx} {...msg} />)}

// Embedding variables
<div className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}>
```

---

### Props (Properties)

**What they are:** Data passed from parent to child component (like function parameters).

```jsx
// Parent
<ChatMessage role="user" content="Hello" />

// Child
function ChatMessage({ role, content }) {
  return <div>{role}: {content}</div>;
}
```

**Key rules:**
1. Props are **read-only** (cannot be modified by child)
2. Props flow **down** (parent → child, never child → parent)
3. Use **callbacks** for child → parent communication

**Example:**

```jsx
// Parent passes callback
<ChatInput onSend={handleSendMessage} />

// Child calls it
function ChatInput({ onSend }) {
  const handleSubmit = () => {
    onSend(input); // Call parent's function
  };
}
```

---

### State (useState)

**What it is:** Data that can change over time and triggers re-renders.

```jsx
const [count, setCount] = useState(0);
//     ↑       ↑             ↑
//   value  setter    initial value
```

**How it works:**

1. Component renders with initial state
2. User action calls `setCount(newValue)`
3. React re-renders component with new value

**Example from App.jsx:**

```jsx
const [messages, setMessages] = useState([]);

// Add a message
setMessages([...messages, newMessage]);
// This creates a new array (React detects change and re-renders)
```

**Why not just use a regular variable?**

```jsx
let count = 0;
count = count + 1; // ❌ Won't trigger re-render
```

State changes **tell React to update the UI**.

---

### Effects (useEffect)

**What it is:** Run side effects (API calls, timers, subscriptions) after render.

```jsx
useEffect(() => {
  // Code to run after render
  
  return () => {
    // Cleanup (optional)
  };
}, [dependencies]);
```

**Example 1: Run once on mount**

```jsx
useEffect(() => {
  fetchModels();  // Load data from API
}, []);  // Empty array = run once
```

**Example 2: Run when state changes**

```jsx
useEffect(() => {
  textareaRef.current.style.height = `${scrollHeight}px`;
}, [input]);  // Runs whenever 'input' changes
```

**Example 3: Cleanup on unmount**

```jsx
useEffect(() => {
  const interval = setInterval(() => poll(), 1000);
  
  return () => clearInterval(interval);  // Cleanup
}, []);
```

**When does cleanup run?**
- When component unmounts
- Before running effect again (if dependencies changed)

---

### Refs (useRef)

**What they are:** Persistent values that **don't trigger re-renders** when changed.

```jsx
const ref = useRef(initialValue);
ref.current = newValue;  // Update value
```

**Two main uses:**

**1. Access DOM elements directly**

```jsx
const inputRef = useRef(null);

useEffect(() => {
  inputRef.current.focus();  // Focus the input
}, []);

return <input ref={inputRef} />;
```

**2. Store mutable values across renders**

```jsx
const pollingIntervalRef = useRef(null);

// Start polling
pollingIntervalRef.current = setInterval(() => {}, 1000);

// Stop polling
clearInterval(pollingIntervalRef.current);
```

**Why not use state?** Changing a ref doesn't cause re-render (good for timers, counters).

---

### Event Handlers

**Pattern:** Functions that respond to user actions.

```jsx
function ChatInput() {
  const handleSubmit = (e) => {
    e.preventDefault();  // Prevent page reload
    onSend(input);
  };
  
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <textarea onKeyDown={handleKeyDown} />
    </form>
  );
}
```

**Naming convention:** `handle{Event}` (e.g., `handleClick`, `handleChange`)

---

## Development Workflow

### Running the App

```bash
cd frontend/console
npm run dev
```

Vite dev server starts on http://localhost:5173

### Hot Module Replacement (HMR)

When you save a file, changes appear **instantly** without full page reload.

**What gets updated:**
- Component code → Preserves state
- CSS → Instant style changes
- Adding/removing components → May require refresh

### Component Development Workflow

**1. Create component file**
```bash
touch src/components/MyComponent/MyComponent.jsx
touch src/components/MyComponent/MyComponent.css
```

**2. Write component**
```jsx
function MyComponent({ title }) {
  return <div className="my-component">{title}</div>;
}

export default MyComponent;
```

**3. Import CSS**
```jsx
import "./MyComponent.css";
```

**4. Use in parent**
```jsx
import MyComponent from "./components/MyComponent/MyComponent";

<MyComponent title="Hello" />
```

### Debugging Tips

**1. Console logging**
```jsx
console.log("State:", messages);
console.log("Props:", { role, content });
```

**2. React DevTools (Browser Extension)**
- Inspect component tree
- View props/state of any component
- Track re-renders

**3. Network tab**
- Check API requests
- Verify request/response payloads

**4. Breakpoints**
- In browser DevTools, click line number in source code
- Execution pauses at that line

---

## Future Considerations

### Adding New Features

**Where to add different types of changes:**

| Change Type | Location | Example |
|-------------|----------|---------|
| New API endpoint | `api/client.js` | `export async function deleteConversation(id)` |
| New component | `components/{Name}/` | `components/Settings/` |
| New hook | `hooks/` | `useLocalStorage.js` |
| New state | `App.jsx` | `const [theme, setTheme] = useState('dark')` |
| New constant | `constants/ui.js` | `export const THEMES = { ... }` |
| Global style | `index.css` | CSS variables |

### Extending Components

**Example: Add a new Button variant**

1. **Update Button.jsx** (no code change needed, it already accepts `variant`)
2. **Update Button.css:**
   ```css
   .btn-danger {
     background: var(--red);
     color: white;
   }
   ```
3. **Use it:**
   ```jsx
   <Button variant="danger">Delete</Button>
   ```

### State Management at Scale

**Current approach works well for:**
- < 10 components
- < 5 levels of nesting
- Simple data relationships

**When to consider external state management (Redux, Zustand):**
- > 15 components need same data
- Deeply nested components (> 5 levels)
- Complex data relationships (normalized data)
- Need for time-travel debugging

**For this app:** Current approach is sufficient. Conversations are simple, and most state is related to UI.

### Performance Optimization

**Current state: Not needed yet.**

**When to optimize:**
- > 100 messages rendering slowly
- Noticeable lag when typing
- Sidebar with > 50 conversations

**Potential optimizations:**
1. **Memoization** - Use `React.memo()` for ChatMessage
2. **Virtualization** - Only render visible messages (react-window)
3. **Code splitting** - Lazy load WelcomeScreen
4. **Debouncing** - Delay auto-resize calculations

**Rule:** Don't optimize prematurely. Measure first.

---

## Summary

**Key Takeaways:**

1. **State flows down, events flow up** - Parent controls child via props, child communicates via callbacks
2. **Lift state to common ancestor** - When multiple components need data
3. **Components are functions** - They take props, return JSX
4. **State changes trigger re-renders** - React updates UI automatically
5. **Effects handle side effects** - API calls, timers, subscriptions
6. **Refs are for non-render values** - DOM access, mutable values

**This architecture is:**
- ✅ Simple (no external libraries)
- ✅ Maintainable (clear component boundaries)
- ✅ Scalable (can add features without major refactor)
- ✅ Testable (components are pure functions)

**Next Steps:**
- Add persistence (localStorage or backend)
- Implement authentication
- Add message editing/deletion
- Implement conversation search
- Add user settings

---

## Questions?

If you're unclear on any concept, here's how to learn more:

1. **Open the file** - Read the actual implementation
2. **Add console.logs** - See what data looks like
3. **Modify and break things** - Best way to learn
4. **Use React DevTools** - Inspect live component tree

**Remember:** This documentation reflects the current state. As you build new features, update this file to keep it accurate.
