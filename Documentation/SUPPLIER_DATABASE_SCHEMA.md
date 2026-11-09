# Supplier Database Schema

## Purpose
Define the canonical structure for the Iron House supplier master database used by estimating, RFQs, procurement, and project execution.

## Core Tables
### Suppliers
Fields:
- Supplier ID
- Company Name
- Category
- Subcategory
- Preferred (Y/N)
- Active (Y/N)
- Region Served
- Website
- Main Email
- Main Phone
- Address
- Account Number
- Credit Terms
- Notes

### Contacts
- Contact ID
- Supplier ID
- Name
- Title
- Email
- Phone
- Mobile
- Bid Contact (Y/N)
- Accounting Contact (Y/N)
- Sales Contact (Y/N)
- Last Verified

### Pricing History
- Supplier ID
- Project
- Item
- Unit
- Unit Price
- Quote Date
- Valid Until
- Notes

### RFQ History
- RFQ ID
- Supplier ID
- Project
- Date Sent
- Response Date
- Status
- Quote Value
- Response Time

## Standard Categories
- Pipe
- Precast
- Aggregates
- Asphalt
- Concrete
- Traffic
- Testing
- Coring
- Electrical
- Survey
- Equipment Rental
- Landscaping
- Environmental
- Fuel
- Safety
- Miscellaneous

## Preferred Defaults
PVC Pipe: EMCO
Ductile Iron: EMCO
Catch Basins: Amrize
Manholes: Amrize
Asphalt: Superior Paving
Testing: Advanced Testing
Concrete: JWS
Coring: Performance Coring

## Integrations
The supplier database is the source of truth for:
- RFQ generation
- Estimate workbook supplier selection
- Procurement tracking
- Quote history
- Supplier performance metrics
- Future bid recommendations

## Future Enhancements
- Automated email discovery
- Quote ingestion from email
- Price trend analysis
- Territory mapping
- Credit limit tracking
- Insurance/WCB expiry tracking
- AI supplier recommendations
