# Iron House Estimate Workbook Template

## Purpose

This folder defines the standard Iron House estimate workbook structure. The workbook is the central pricing tool for bids and should connect tender intake, drawing takeoff, supplier RFQs, subcontractor quotes, production assumptions, markup, risk, and final bid submission.

## Workbook Tabs

The standard estimate workbook should include these tabs:

1. `Project_Info`
2. `Bid_Summary`
3. `Quantity_Takeoff`
4. `Self_Perform`
5. `Materials`
6. `Subcontractors`
7. `Equipment_Rentals`
8. `Trucking_Disposal`
9. `Traffic_Control`
10. `Testing_QC`
11. `Indirects`
12. `Markup_Contingency`
13. `RFQ_Log`
14. `Supplier_Quotes`
15. `Risk_Register`
16. `Clarifications_Exclusions`
17. `Submission_Checklist`
18. `Field_Turnover`

## Tab Descriptions

### Project_Info
Stores project identity and tender metadata.

Fields:
- Project code
- Project name
- Owner
- Engineer
- Location
- Tender number
- Closing date
- Closing time
- Addenda received
- Drawing set date
- Specification date
- Completion date
- Bonding requirements
- Insurance requirements

### Bid_Summary
Rolls up the total bid.

Sections:
- Self-perform total
- Materials total
- Subcontractor total
- Equipment/rentals total
- Trucking/disposal total
- Testing/QC total
- Traffic control total
- Indirects total
- Overhead
- Profit
- Contingency
- Final bid price

### Quantity_Takeoff
Stores measured quantities with traceability.

Fields:
- Item number
- Description
- Drawing reference
- Specification reference
- Unit
- Quantity
- Waste factor
- Adjusted quantity
- Notes
- Source / assumption

### Self_Perform
Prices Iron House labour and production-based work.

Fields:
- Scope item
- Quantity
- Unit
- Crew size
- Production rate
- Labour hours
- Labour rate
- Equipment required
- Equipment cost
- Total direct cost
- Unit cost
- Notes

### Materials
Tracks material supply pricing.

Fields:
- Material item
- Supplier
- Quantity
- Unit
- Waste factor
- Unit price
- Delivery included
- Lead time
- Quote reference
- Total cost

### Subcontractors
Tracks subcontractor pricing.

Fields:
- Scope
- Subcontractor
- Contact
- Quote received
- Quote value
- Included items
- Exclusions
- Addenda acknowledged
- Selected price
- Notes

### Equipment_Rentals
Tracks owned/rented equipment costing.

Fields:
- Equipment
- Supplier
- Duration
- Rate type
- Rate
- Delivery/pickup
- Fuel allowance
- Attachments
- Damage waiver
- Total cost

### Trucking_Disposal
Tracks trucking, hauling, disposal, and import materials.

Fields:
- Material type
- Quantity
- Unit
- Truck type
- Haul distance
- Rate
- Disposal site
- Tipping fee
- Wait time allowance
- Total cost

### Traffic_Control
Tracks traffic management requirements.

Fields:
- Requirement
- Supplier/subcontractor
- Duration
- Rate
- Devices/signage
- Permit allowance
- TCP hours
- Total cost

### Testing_QC
Tracks testing and quality-control requirements.

Fields:
- Test type
- Supplier
- Frequency
- Quantity
- Unit rate
- Reporting included
- Total cost

### Indirects
Tracks general project costs.

Fields:
- Mobilization
- Demobilization
- Supervision
- Project management
- Administration
- Small tools
- Safety
- Temporary works
- Layout
- Documentation
- Insurance burden
- Bonding allowance

### Markup_Contingency
Stores business-level pricing logic.

Fields:
- Direct cost subtotal
- Indirect cost subtotal
- Overhead percentage
- Profit percentage
- Contingency percentage
- Startup recovery allowance
- Truck burden allowance
- Financing/LOC allowance
- Final bid total

### RFQ_Log
Tracks RFQs sent to suppliers and subcontractors.

Fields:
- Supplier/subcontractor
- Category
- Contact
- Email
- Date sent
- Due date
- Attachments sent
- Status
- Follow-up date
- Notes

### Supplier_Quotes
Tracks quote data received.

Fields:
- Supplier
- Quote date
- Quote amount
- Scope covered
- Delivery included
- Taxes included/excluded
- Addenda acknowledged
- Validity period
- Exclusions
- Quote file reference

### Risk_Register
Tracks bid risks and required allowances.

Fields:
- Risk item
- Description
- Probability
- Impact
- Cost allowance
- Schedule impact
- Mitigation
- Include/Exclude/Clarify

### Clarifications_Exclusions
Stores bid qualifications.

Fields:
- Item
- Type
- Description
- Reason
- Included in price
- Submitted with bid

### Submission_Checklist
Confirms the final bid package is complete.

Fields:
- Requirement
- Responsible person
- Complete
- Notes

### Field_Turnover
Transfers estimating knowledge to execution.

Fields:
- Key scope items
- Major quantities
- Suppliers used
- Subcontractors used
- Production assumptions
- Long-lead items
- Risks
- Required inspections
- Testing requirements
- Exclusions / clarifications

## Default Formula Logic

The workbook should calculate:

- Adjusted quantity = quantity x waste factor.
- Line total = adjusted quantity x unit price.
- Labour hours = quantity / production rate x crew hours.
- Self-perform total = labour + equipment + materials + trucking + rentals.
- Direct cost subtotal = self-perform + materials + subcontractors + trucking + testing + traffic control.
- Bid total = direct costs + indirects + overhead + profit + contingency + allowances.

## Versioning

Use this naming convention:

```text
Iron_House_Estimate_Workbook_v1.0.xlsx
PROJECTCODE_Project_Name_Estimate_v01.xlsx
```

## Operating Rule

The estimate workbook must remain practical, traceable, and field-ready. Every bid number should connect back to a quantity, quote, production assumption, allowance, or documented risk decision.
