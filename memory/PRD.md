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

### System Modules Supported as Targets
inventory, invoices, buyers, suppliers, purchase_orders, quotations, composite_products, employees

## Completed Features
1-25. B2B Marketplace, Invoices, Inventory, Panel System Phase 1-3A, RBAC, Employee Permissions
26. Phase 3B: Smart Document Builder (Excel/PDF export)
27. Phase 4 Lite: Basic Automation (superseded)
28. **Phase 4 Full: Multi-Target Workflow Automation Engine (Mar 2026)**
    - Backend: Complete rewrite with multi-target support, per-target field mapping/visibility
    - Frontend: Complete rewrite with contract-first approach, TargetCard components
    - Trigger Types: on_create, on_update, condition_based
    - Action Types: create_record, create_records_per_item, update_record
    - Duplicate prevention, execution logging, loop prevention
    - Backend tested: 16/16 tests passed (100%)
    - Backend lint: All checks passed

## Prioritized Backlog
### P0 (Next)
1. End-to-end workflow testing: Invoice -> QC -> Dispatch flow with real data
2. Document Builder Templates: customizable PDF with {{variables}}

### P1
3. Reporting Phase 3: Cash Flow, Tax Liability, Order Fulfillment
4. Seller Reminder Controls

### P2
- GSTR-1 JSON export | Custom Material Report
- White-label toggle | WhatsApp Business API

## Key Files
- `/app/backend/routers/automation_router.py` — Multi-target engine: CRUD, execution, mapping, dedup, chaining
- `/app/backend/routers/panel_router.py` — Panel CRUD, module-fields API, export, entity_id extraction
- `/app/frontend/src/app/seller/business-tools/automation/page.tsx` — Multi-target Rule Builder UI
- `/app/frontend/src/app/seller/business-tools/panels/page.tsx` — Panel config: binding variable, systemManaged fields
- `/app/frontend/src/app/seller/business-tools/panels/[panelId]/page.tsx` — Records + export buttons
