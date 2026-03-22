# PRD - B2B E-commerce & ERP Platform (UdyogConnect)

## Original Problem Statement
Build a B2B marketplace for Indian industrial products with seller tools including invoicing, inventory, purchase orders, buyer management, and a configurable Panel System for custom business workflows with workflow automation.

## Core Tech Stack
- **Backend:** FastAPI, MongoDB, Python 3.11
- **Frontend:** Next.js 16, React, TypeScript, Tailwind CSS, Shadcn/UI
- **Auth:** Firebase Admin (email/password)
- **Real-time:** python-socketio + socket.io-client

## System Flow (Panel → Entity Binding → Rule → Execution)
```
1. PANEL CREATION:
   User creates Custom Panel → adds Relation field → picks "Inventory"
   → Binding Variable dropdown shows: Product Name, SKU, Stock, etc.
   → User picks "Product Name"
   → System auto-labels: "Product Name (Linked to Inventory)"
   → Stores: { relatedPanel: "inventory", bindingField: "productName" }

2. DATA ENTRY:
   User selects "Product Name = Cable Drum" → system stores sellerListing ID
   Record also stores entity_id for linking

3. RULE CREATION (all dropdowns, no free text except name):
   Trigger: Custom Panel + Trigger Type (On Create / On Update / Condition Based)
   Condition: field + operator + value (optional / required for condition_based)
   Action Type: Create Record / Create Records Per Item / Update Record
   Via Relation: auto-created relation field → auto-derives Target Panel (locked)
   Field Mapping: Source → Target table with "Select All" auto-map + defaults
   Field Visibility: per-field Visible/Editable toggles

4. EXECUTION:
   On record create/update → match trigger_type → check condition
   → Create: map fields + defaults → duplicate prevention → store entity_id + parent_id
   → Create Per Item: loop line items → create one record per item → chain automations
   → Update: find target via relation → apply operation (increment/decrement/set)
```

## Automation Rule Schema
```json
{
  "name": "Invoice → QC Records",
  "trigger_panel_id": "panel_id",
  "trigger_type": "on_create | on_update | condition_based",
  "condition": { "field": "status", "operator": "equals", "value": "Pass" },
  "action_type": "create_record | create_records_per_item | update_record",
  "target_panel_id": "target_panel_id",
  "relation_field": "product",
  "field_mappings": [
    { "target_field": "product", "source_field": "product", "mapping_type": "field" },
    { "target_field": "qc_status", "default_value": "Pending", "mapping_type": "default" }
  ],
  "field_visibility": [
    { "field": "product", "visible": true, "editable": false },
    { "field": "qc_status", "visible": true, "editable": true }
  ],
  "update_operation": "increment | decrement | set_value",
  "update_field": "stock",
  "update_value_from": "quantity",
  "is_active": true,
  "priority": 0
}
```

## Record Linking (Automation-Created Records)
```json
{
  "panelId": "target_panel_id",
  "data": { "mapped_field": "value" },
  "entity_id": "product_123",
  "parent_id": "source_record_id",
  "source_panel": "source_panel_id",
  "source_rule": "rule_id",
  "createdBy": "automation"
}
```

## Completed Features
1-25. B2B Marketplace, Invoices, Inventory, Panel System Phase 1-3A, RBAC, Employee Permissions
26. Phase 3B: Smart Document Builder (Excel/PDF export)
27. Phase 4 Lite: Basic Automation (now superseded)

28. **Phase 4 Full: Workflow Automation Engine (Mar 2026)** — LATEST:
    - **Trigger Types**: on_create, on_update, condition_based
    - **Action Types**: update_record, create_record, create_records_per_item
    - **Field Mapping**: Source→Target table, "Select All" auto-map, default values, reference mapping
    - **Field Visibility**: Per-field visible/editable toggles
    - **Duplicate Prevention**: entity_id + parent_id + source_rule check
    - **Record Linking**: entity_id, parent_id, source_panel, source_rule on auto-created records
    - **Event Chaining**: Automation-created records trigger further automations (loop prevention)
    - **Per-Item Processing**: create_records_per_item loops line items (invoice products)
    - **Module Fields API**: GET /api/business-tools/panels/module-fields/{module_id}
    - **Binding Variable**: Relation field shows target's fields for binding selection
    - **Panel Config**: "Connect Panel With (Entity)" + binding variable dropdown
    - **System Rules Enforced**: All dropdowns (no free text), locked targets, systemManaged fields

## Prioritized Backlog
### P0 (Next)
1. End-to-end workflow testing: Invoice → QC → Dispatch flow with real data
2. Document Builder Templates: customizable PDF with {{variables}}

### P1
3. Reporting Phase 3: Cash Flow, Tax Liability, Order Fulfillment
4. Seller Reminder Controls

### P2
- GSTR-1 JSON export | Custom Material Report
- White-label toggle | WhatsApp Business API

## Key Files
- `/app/backend/routers/automation_router.py` — Complete engine: CRUD, execution, mapping, dedup, chaining
- `/app/backend/routers/panel_router.py` — Panel CRUD, module-fields API, export, entity_id extraction
- `/app/frontend/src/app/seller/business-tools/automation/page.tsx` — Rule Builder: trigger/action types, field mapping table, visibility
- `/app/frontend/src/app/seller/business-tools/panels/page.tsx` — Panel config: binding variable, systemManaged fields
- `/app/frontend/src/app/seller/business-tools/panels/[panelId]/page.tsx` — Records + export buttons
