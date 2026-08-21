# Dashboard Polish Pass Implementation Plan

## Current State Audit (vs DASHBOARD_POLISH_GUIDE.md)

### 1. Global Shell
- **Status**: Mostly DONE. 
- **Missing**: None. Persistent navigation, active states, and connection status are all implemented and consistent.

### 2. Plan View
- **Status**: Mostly DONE.
- **Missing**: The split-flap animation exists (`rotateX`), and state pills/signal lights are wired up perfectly. Search filtering exists, but we can explicitly add a dropdown to filter by state as operators "want to jump straight to 'show me everyone in maintenance'."

### 3. Alerts View
- **Status**: PARTIALLY DONE.
- **Missing**: **INFEASIBLE handling**. The backend can now return `status: "INFEASIBLE"`. We need to detect this from the backend response (either via `plan.status` or a custom flag) and render a prominent alert explaining *why* the plan failed, instead of swallowing the error or showing a generic toast.

### 4. Yard (Digital Twin) View
- **Status**: NEEDS UPDATE.
- **Missing**: 
  - **Muttom Zones**: Frontend `YARD_LAYOUT` still uses old synthetic names. Needs updating to match backend (Stabling L1-L5, Major Repair M1, Inspection I1, Overhaul O1, Wheel Profiling P1, Wash W1).
  - **Fake Shunt Paths**: We currently inject a hardcoded fake shunt for `T05` if no shunts exist. This must be REMOVED to honestly reflect the data.

### 5. What-If View
- **Status**: PARTIALLY DONE.
- **Missing**:
  - **INFEASIBLE handling**: Needs a dedicated empty/error state when a what-if scenario returns INFEASIBLE.
  - **TrainLoader**: Uses `SignalSweep` instead of the `TrainLoader` specified in the guide.

### 6. Explain View
- **Status**: PARTIALLY DONE.
- **Missing**: Missing the signal-light constraint-type indicator for the assignment being explained.

### 7. Cross-Cutting
- **Status**: NEEDS UPDATE.
- **Missing**: 
  - `prefers-reduced-motion` needs to be consistently applied to `AnimatePresence` in PlanTable and What-If.
  - **Mobile/Responsive**: `App.css` needs a media query pass to stack the sidebar, grids, and adjust margins on mobile devices.

---

## Proposed Changes

### 1. Infeasible State UI (Priority)
#### [MODIFY] [App.jsx](file:///c:/Users/abhig/OneDrive/Desktop/MetGo/kmrl-frontend/src/App.jsx)
- Update `loadDashboard` and `runScenario` to gracefully catch HTTP 400 (if the API throws an error) or parse a `status === 'INFEASIBLE'` returned by the API.
- Create a new component `<InfeasibleState reason={...} />` rendering a calm, explicit message (e.g., "Cannot meet minimum service floor") using `PAToast` or a dedicated panel in the Alerts / WhatIf views.

### 2. Yard View Digital Twin Update
#### [MODIFY] [App.jsx](file:///c:/Users/abhig/OneDrive/Desktop/MetGo/kmrl-frontend/src/App.jsx)
- Replace `YARD_LAYOUT` with the new real zones (I1, O1, P1, M1, W1).
- Strip out the `T05` fake shunt injection. Render the shunt section conditionally only if `plan.shunts_required` has actual data.

### 3. Component & Polish Updates
#### [MODIFY] [App.jsx](file:///c:/Users/abhig/OneDrive/Desktop/MetGo/kmrl-frontend/src/App.jsx)
- Swap `SignalSweep` for `<TrainLoader />` in the What-If view.
- Add `<ConstraintLight />` to the Explain view header next to the StateBadge.
- Ensure all Framer Motion `<motion.div>` elements respect `useReducedMotion()`.

#### [MODIFY] [App.css](file:///c:/Users/abhig/OneDrive/Desktop/MetGo/kmrl-frontend/src/App.css)
- Add `@media (max-width: 768px)` rules to restructure `.app-shell` to `flex-direction: column`, convert `.sidebar` to a bottom nav bar or top hamburger menu, and ensure tables scroll horizontally.

## Verification Plan

### Automated Tests
1. Trigger a What-If scenario that we know results in INFEASIBLE (e.g. Breakdown T01 in `test_breakdown_enforcement.py`).
2. Verify the frontend renders the INFEASIBLE alert cleanly without crashing.
3. Check the Yard view for real zone names and no fake animations.
4. Test responsiveness by resizing the browser window to mobile width.
