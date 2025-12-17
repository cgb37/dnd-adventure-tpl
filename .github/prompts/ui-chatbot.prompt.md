---
name: ui-chatbot
description: Design prompt for a dual-panel website layout with an integrated chatbot (desktop split view + mobile drawer).
argument-hint: "Describe any constraints (colors/components), target breakpoints, and required UI behaviors"
tools: []
---

**Figma Design Prompt: Dual-Panel Website with Integrated AI Chatbot**

Create a modern, responsive web application interface with the following layout and components:

**Overall Layout:**
- Design for a standard desktop viewport (1440px width recommended)
- Split-screen layout with two main panels:
  - **Left Panel (70% width)**: Main website content viewport
  - **Right Panel (30% width)**: AI chatbot interface with show/hide functionality

**Left Panel - Main Content Viewport:**
- Clean, spacious design for displaying standard website pages
- Include a subtle vertical divider/resize handle between panels
- Design should accommodate typical web content (headers, text, images, navigation)
- Consider showing sample content like a dashboard, article page, or product listing

**Right Panel - AI Chatbot Interface:**

*Header Section (15% of chatbot height):*
- Title: "AI Assistant" or similar
- Toggle button (show/hide) positioned in top-right corner
  - Icon: chevron-right when expanded, chevron-left when collapsed
  - Smooth collapse animation should hide panel off-screen to the right
- Optional: Model selection dropdown showing current model
- Clean, minimal header with subtle border/shadow

*Chat Display Area (85% of chatbot height):*
- Scrollable message container with comfortable padding
- Message bubbles:
  - User messages: Right-aligned, distinct color (e.g., blue/primary color)
  - AI responses: Left-aligned, neutral/light background
  - Include avatar/icons for user and AI
- Typography: Clear, readable font with good line spacing
- Timestamp display (optional)
- Loading indicator for AI responses (typing dots animation)

*Input Section (Bottom, ~100-120px height):*
- Multi-line text input field with placeholder: "Ask me anything..."
- Auto-expanding textarea (grows with content, max 4-5 lines)
- Action icons row positioned to the left of or below input:
  1. **Attach File Icon**: Paperclip or upload icon
  2. **Model Selector Icon**: Gear/settings or dropdown icon
  3. **MCP Tool Selector Icon**: Tool/plugin icon or grid icon
  4. **Generate Dropdown**: Generate commands for NPCs, Monsters, etc.
- **Send Button**: Prominent button on the right (arrow/paper plane icon)
- Subtle border separating from chat area above

**Collapsed State:**
- When hidden, show a floating toggle button on the right edge of viewport
- Button should have an icon (chat bubble or chevron-left)
- Smooth slide-in/out animation

**Design Style Guidelines:**
- Modern, clean aesthetic with ample whitespace
- Consistent color palette: primary color for accents, neutral grays for backgrounds
- Subtle shadows and borders for depth
- Rounded corners on buttons and message bubbles (4-8px radius)
- Icon size: 20-24px for toolbar icons
- Responsive considerations: Show mobile/tablet breakpoints if possible

**Interactive States to Include:**
- Hover states for all buttons and icons
- Active/focused state for text input
- Disabled states for buttons
- Loading/thinking state in chat area

---
