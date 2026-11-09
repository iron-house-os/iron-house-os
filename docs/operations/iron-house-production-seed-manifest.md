# Build 177 — Iron House Production Seed Manifest

## Organization
- Name: Iron House Civil Constructors
- Short name: Iron House
- Country: Canada
- Province: British Columbia
- Time zone: America/Vancouver

## Default roles
Create the roles defined in `docs/security/organization-role-model.md` with least-privilege permission assignments.

## Default supplier categories
- PVC and HDPE pipe
- Ductile iron
- Catch basins and manholes
- Aggregate
- Asphalt
- Concrete
- Coring
- Testing
- Traffic control
- Geotechnical
- Equipment rental
- Trucking

## Preferred supplier defaults
- PVC pipe: EMCO
- Ductile iron: EMCO
- Catch basins: Amrize
- Manholes: Amrize
- Asphalt: Superior Paving
- Testing: Advanced Testing
- Concrete subcontracting: JWS
- Coring: Performance Coring

## Execution defaults
Self-perform excavation, trenching, pipe installation, structures, backfill, compaction, subgrade, granular base, topsoil, cleanup and general earthworks. Subcontract concrete placement/finishing, asphalt fine grading, asphalt paving, pavement markings and street lighting unless project-specific instructions override them.

## Seed safety
The seed process must be idempotent, must not overwrite user-edited records and must require explicit bootstrap credentials through environment variables.
