INSERT INTO municipalities (name, region, standards_uri, notes)
VALUES
    ('City of Surrey', 'Lower Mainland', 'https://www.surrey.ca/', 'Seed municipality for tender and standards workflows.'),
    ('City of Vancouver', 'Lower Mainland', 'https://vancouver.ca/', 'Seed municipality for future standards engine.')
ON CONFLICT (name) DO NOTHING;

INSERT INTO suppliers (name, category, service_area, website, notes)
VALUES
    ('Pacific Pipe Supply', 'Pipe and fittings', 'Lower Mainland', 'https://example.com/pacific-pipe', 'Phase 1 sample supplier.'),
    ('Fraser Valley Aggregates', 'Aggregates', 'Fraser Valley', 'https://example.com/fraser-aggregates', 'Phase 1 sample supplier.'),
    ('Coastal Traffic Control', 'Traffic management', 'Metro Vancouver', 'https://example.com/coastal-traffic', 'Phase 1 sample supplier.')
ON CONFLICT DO NOTHING;

INSERT INTO contacts (supplier_id, first_name, last_name, email, phone, role)
SELECT id, 'Sam', 'Estimator', 'estimating@example.com', '604-555-0100', 'Estimator'
FROM suppliers
WHERE name = 'Pacific Pipe Supply'
ON CONFLICT DO NOTHING;

INSERT INTO projects (name, project_number, status, municipality_id, description)
SELECT 'Phase 1 Demonstration Project', 'IHO-0001', 'planning', id, 'Seed project for scaffold validation.'
FROM municipalities
WHERE name = 'City of Surrey'
ON CONFLICT (project_number) DO NOTHING;

INSERT INTO tenders (municipality_id, source, reference_number, title, status, source_url, summary)
SELECT id, 'manual', 'T-0001', 'Sample Civil Works Tender', 'watching', 'https://example.com/tenders/t-0001', 'Seed tender for Phase 2 tracker design.'
FROM municipalities
WHERE name = 'City of Surrey'
ON CONFLICT (reference_number) DO NOTHING;

INSERT INTO equipment (name, equipment_type, identifier, status, hourly_rate)
VALUES
    ('Excavator 210', 'Excavator', 'EQ-210', 'available', 185.00),
    ('Tandem Dump Truck', 'Truck', 'EQ-TD-01', 'available', 130.00)
ON CONFLICT (identifier) DO NOTHING;

INSERT INTO employees (first_name, last_name, email, role, status)
VALUES
    ('Iron', 'Admin', 'admin@ironhouse.local', 'Administrator', 'active')
ON CONFLICT (email) DO NOTHING;
