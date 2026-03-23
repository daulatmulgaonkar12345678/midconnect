# PRD - B2B E-commerce & ERP Platform (UdyogConnect)

## Original Problem Statement
Build a B2B marketplace for Indian industrial products with seller tools including invoicing, inventory, purchase orders, buyer management, and a configurable Panel System for custom business workflows with workflow automation.

## Core Tech Stack
- **Backend:** FastAPI, MongoDB, Python 3.11
- **Frontend:** Next.js 16, React, TypeScript, Tailwind CSS, Shadcn/UI
- **Auth:** Firebase Admin (email/password)
- **Real-time:** python-socketio + socket.io-client

## System Architecture: Decoupled Panels + Rules

### Core Principle
- **Panels = Data Layer** (schema + records only, no workflow logic)
- **Rules = Workflow Layer** (triggers, conditions, multi-target actions)
- **Single Source of Truth:** Data always flows from Source Panel -> Target Panels

### Automation Rule Contract (LOCKED)
```json
{
  "name": "string",
  "trigger_panel_id": "string (source panel ObjectId)",
  "trigger_type": "on_create | on_update | condition_based",
  "condition": { "field": "string", "operator": "string", "value": "string" },
  "targets": [
    {
      "target_panel_id": "string (custom panel ObjectId or system module ID)",
      "action_type": "create_record | create_records_per_item | update_record",
      "data_mode": "smart_sync | manual_only | full_copy",
      "relation_field": "string (optional)",
      "update_operation": "increment | decrement | set_value",
      "update_field": "string",
      "update_value_from": "string",
      "field_mappings": [
        { "target_field": "string", "source_field": "string", "default_value": "string", "mapping_type": "field | default | reference" }
      ],
      "field_visibility": [
        { "field": "string", "visible": true, "editable": true }
      ]
    }
  ],
  "is_active": true,
  "priority": 0
}
```

### Data Mode Behavior (LOCKED)
- **smart_sync** (default): Explicit mappings priority. Remaining target fields (ALL types incl. relations) auto-fill from matching source field names.
- **manual_only**: Only explicitly mapped fields transfer. Most restrictive.
- **full_copy**: For each target field that exists in source, copy value. Explicit mappings override.

### System Modules Supported as Targets
inventory, invoices, buyers, suppliers, purchase_orders, quotations, composite_products, employees

## Completed Features
1-25. B2B Marketplace, Invoices, Inventory, Panel System Phase 1-3A, RBAC, Employee Permissions
26. Phase 3B: Smart Document Builder (Excel/PDF export)
27. Phase 4 Lite: Basic Automation (superseded)
28. **Phase 4 Full: Multi-Target Workflow Automation Engine (Mar 2026)**
    - Backend: Multi-target support, per-target field mapping/visibility
    - Frontend: Contract-first approach, TargetCard components
29. **Phase 4.1: Data Mode + Preview (Mar 2026)**
    - 3 data modes per target: smart_sync, manual_only, full_copy
    - Preview endpoint: dry-run showing exact data output before saving
    - Frontend: Data Mode toggle, mode-specific info messages, Preview Data button
30. **Bug Fix: Smart Sync relation field matching (Mar 2026)**
    - Root cause: `get_target_field_keys()` excluded relation-type fields from matching
    - Fix: Include ALL field types in target_field_keys
31. **Bug Fix: Update Record lookup field (Mar 2026)**
    - Root cause: "Relation Field" dropdown showed only data fields (excluded relation fields); label was confusing
    - Fixes:
      1. Dropdown now shows all source fields — relation fields linking to target shown FIRST with "(linked)" label
      2. Label renamed to "Lookup Key *" for update_record with guidance text
      3. Made lookup key REQUIRED for update_record with validation
      4. Preview shows lookup resolution + operation
32. **ARCHITECTURE UPGRADE: Relational Update Engine (Mar 2026)**
    - Replaced single "Lookup Key" with proper **MATCH + UPDATE** model
    - **MATCH**: `[Target Field] = [Source Field]` — identifies WHICH record to update
      - e.g., `Inventory.product_name = QC.product_name`
    - **UPDATE**: `[Target Field] = Operation(Source Value)` — what to change
      - e.g., `stock = increment(quantity)`
    - Backend: New fields `match_target_field` + `match_source_field` on RuleTarget
    - Backend: `update_system_record` now supports field-based matching (by _id, productName, sku, or any field)
    - Frontend: Two-section UI with blue MATCH box + orange UPDATE box
    - Auto-detect: When target = Inventory and source has relation to inventory, auto-fills match fields
    - Clear error messages when match fails
    - End-to-end verified: QC(pass) → Inventory stock increment. Stock 7 → 32 correctly
    - Tests: 18/18 passed (100%)

## Prioritized Backlog
### P0 (Next)
1. Apply field_visibility in records UI (records page respects visible/editable settings from rules)
2. Document Builder Templates: customizable PDF with {{variables}}

### P1
3. Reporting Phase 3: Cash Flow, Tax Liability, Order Fulfillment
4. Seller Reminder Controls

### P2
- GSTR-1 JSON export | Custom Material Report
- White-label toggle | WhatsApp Business API

## Key Files
- `/app/backend/routers/automation_router.py` — Multi-target engine + data modes + preview
- `/app/backend/routers/panel_router.py` — Panel CRUD, module-fields API, record validation
- `/app/frontend/src/app/seller/business-tools/automation/page.tsx` — Multi-target Rule Builder UI with data modes
- `/app/frontend/src/app/seller/business-tools/panels/page.tsx` — Panel config
- `/app/frontend/src/app/seller/business-tools/panels/[panelId]/page.tsx` — Records + export
- `/app/backend/tests/test_automation_data_mode_preview.py` — 18 backend tests
