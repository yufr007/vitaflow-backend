"""
VitaFlow API - Legacy SQLAlchemy Base (for model definitions only).

NOTE: This app uses MongoDB via Beanie ODM (see database.py in root).
This file exists only to provide SQLAlchemy Base for legacy model files
that haven't been migrated to Beanie documents.

DO NOT USE THIS FOR ACTUAL DATABASE OPERATIONS.
Use MongoDB documents from app/models/mongodb.py instead.
"""

from sqlalchemy.orm import declarative_base

# Declarative base for legacy ORM model definitions
# These models are NOT used - MongoDB documents are the actual data layer
Base = declarative_base()


def get_db():
    """
    Legacy dependency - raises error if called.
    
    Use MongoDB instead via Beanie ODM.
    """
    raise NotImplementedError(
        "SQLAlchemy get_db() is deprecated. "
        "Use MongoDB documents from app/models/mongodb.py"
    )

