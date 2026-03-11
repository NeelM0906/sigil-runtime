# Chat UI Fixes - 2026-03-09

**Branch:** `fix/chat-multiline-alignment-and-mention-routing`
**File:** `mission-control/src/components/ChatWindow.jsx`

---

## Bug 1: Multi-line message alignment broken

### Problem
When a user sends a multi-line message in the Comms chat, the first line displays
correctly but subsequent lines align to the right side of the message bubble instead
of the left.

### Root Cause
The `MessageBubble` component applies `text-right` on the outer wrapper for user
messages (line 86) to right-align the header and timestamp. This CSS property
cascades into the message content bubble, causing multi-line text to right-align
inside the bubble.

### Fix
Added explicit `text-left` to the message content `<div>` (the bubble) so that
text inside always aligns left regardless of the parent's `text-right` alignment.

```diff
- <div className={`text-sm leading-relaxed px-3 py-2 rounded-lg ${
+ <div className={`text-sm leading-relaxed px-3 py-2 rounded-lg text-left ${
```

---

## Bug 2: @mention messages not routed to agents

### Problem
When a user types `@SAI give me a brief...` in the chat input and presses Enter,
the message is stored but the agent (SAI/Prime) never receives or processes it.
No response is returned.

### Root Cause
The `targets` array (which determines which beings receive the message) was only
populated when the user **clicked** a being from the mention dropdown. If the user
typed `@SAI` inline and pressed Enter without selecting from the dropdown, `targets`
remained empty (`[]`).

On the server side, routing is driven by the targets array:
```python
for tid in targets:
    dashboard_svc.route_to_being(tid, content, sender=sender)
```
With an empty `targets`, the loop never executes and no being processes the message.

### Fix
Added @mention parsing in `handleSend()` that scans the message content for
`@mentions`, resolves them to being IDs by matching against registered beings
(by name or ID, case-insensitive), and adds them to the targets array before
sending. This ensures routing works regardless of whether the user selected
from the dropdown or typed the mention inline.

```javascript
// Resolve @mentions from content into targets
const resolvedTargets = [...targets]
const mentionMatches = content.match(/@(\w+)/g) || []
for (const mention of mentionMatches) {
  const name = mention.slice(1).toLowerCase()
  const being = beings.find(b =>
    CHAT_ROUTABLE_TYPES.has(b.type) && (
      b.name.toLowerCase() === name ||
      b.id.toLowerCase() === name
    )
  )
  if (being && !resolvedTargets.includes(being.id)) {
    resolvedTargets.push(being.id)
  }
}
```

---

## Summary of Changes

| Change | Location | Lines |
|--------|----------|-------|
| Add `text-left` to message bubble | `MessageBubble` component | ~118 |
| Parse @mentions into targets on send | `handleSend()` in `ChatWindow` | ~389-403 |
