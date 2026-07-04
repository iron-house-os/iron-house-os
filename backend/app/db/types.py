from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

JSONType = JSONB().with_variant(JSON(), "sqlite")
