# Sidebar Feature Documentation

## Overview
The chat interface now includes a sleek sidebar with expand/collapse functionality, matching the modern design aesthetic.

## Features

### 1. **Expandable/Collapsible Sidebar**
- **Expanded**: 260px wide - shows full content
- **Collapsed**: 60px wide - shows only icons
- Smooth animation transitions (0.3s ease)
- Does NOT disappear - just slims down

### 2. **Toggle Button**
- Located in sidebar header
- Shows arrow icon (left arrow when expanded, right arrow when collapsed)
- Hover effect with background highlight
- Tooltip on hover

### 3. **Add Personal Context Button** (NEW)
- Premium featured button with red gradient background
- User icon (profile silhouette)
- Positioned above New Chat button
- Unique styling with glowing red shadow
- Hover effects: Lifts up slightly, stronger glow
- Icon remains visible when sidebar is collapsed
- Placeholder for adding user context/preferences

### 4. **New Chat Button**
- Creates a fresh conversation
- Clears all messages and resets session
- Shows icon + text when expanded
- Shows only icon when collapsed
- Dark background with red border on hover
- Plus (+) icon

### 5. **About Section**
- Visible only when sidebar is expanded
- Shows brief description of the assistant
- Styled with dark background card

## Design Details

### Colors
- **Background**: `#1a1a1a` (main sidebar)
- **Border**: `#2a2a2a`
- **Hover states**: `#333`
- **Red accent**: `#cc0033`
- **Personal Context Button**: Red gradient `#cc0033` → `#990025`
- **Personal Context Glow**: `rgba(204, 0, 51, 0.3-0.5)`
- **Text**: `#ffffff` (primary), `#888` (secondary)

### Layout
- Sidebar: Fixed width, full height
- Chat container: Flexible width, adjusts based on sidebar state
- Smooth transitions on all interactive elements

## User Interactions

### Minimize Sidebar
1. Click the arrow button in sidebar header
2. Sidebar shrinks to 60px
3. Text labels hide, only icons remain
4. Chat area expands to fill space

### Maximize Sidebar
1. Click the arrow button (now pointing right)
2. Sidebar expands to 260px
3. All text and content appears
4. Chat area adjusts width

### Add Personal Context
1. Click the prominent red "Add Personal Context" button
2. Currently shows placeholder alert
3. Future: Opens modal/form for user preferences

### New Chat
1. Click "New Chat" button (dark button below context button)
2. All messages cleared
3. Session resets
4. Welcome screen appears

## Responsive Design

### Desktop (>768px)
- Expanded sidebar: 260px
- Full functionality

### Mobile (≤768px)
- Expanded sidebar: 220px (slightly narrower)
- Collapsed sidebar: 60px (same)
- All features maintained

## Technical Implementation

### State Management
```typescript
const [sidebarExpanded, setSidebarExpanded] = useState(true)
```

### CSS Classes
- `.sidebar.expanded` - Wide sidebar
- `.sidebar.collapsed` - Slim sidebar
- `.chat-container.with-sidebar-expanded` - Adjusted chat width
- `.chat-container.with-sidebar-collapsed` - Adjusted chat width

### Smooth Transitions
All width changes use CSS transitions for smooth animations:
```css
transition: width 0.3s ease;
```

## Future Enhancements

- Add conversation history list
- Recent chats section
- Settings panel
- Theme switcher
- User profile section
