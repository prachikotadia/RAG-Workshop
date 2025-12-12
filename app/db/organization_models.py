"""
Database models for multi-tenant organization/workspace support.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Table
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base

# Many-to-many relationship for organization members
organization_members = Table(
    'organization_members',
    Base.metadata,
    Column('organization_id', Integer, ForeignKey('organizations.id', ondelete='CASCADE'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
)


class OrganizationRole(str, enum.Enum):
    """Roles within an organization."""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Organization(Base):
    """
    Model for organizations/workspaces.
    
    Supports multi-tenant architecture with team collaboration.
    """
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)  # URL-friendly identifier
    description = Column(Text, nullable=True)
    
    # Ownership
    owner_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Settings
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    members = relationship("User", secondary=organization_members, backref="organizations")
    # documents relationship commented out - Document.organization_id column doesn't exist yet
    # documents = relationship("Document", back_populates="organization")
    workspaces = relationship("Workspace", back_populates="organization")
    
    def __repr__(self):
        return f"<Organization(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class Workspace(Base):
    """
    Model for workspaces within an organization.
    
    Workspaces allow further organization of documents and collaboration.
    """
    __tablename__ = "workspaces"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Access control
    is_private = Column(Boolean, default=False)  # Private workspaces are only accessible to members
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="workspaces")
    # documents relationship commented out - Document.workspace_id column doesn't exist yet
    # documents = relationship("Document", back_populates="workspace")
    members = relationship("User", secondary="workspace_members", backref="workspaces")
    
    def __repr__(self):
        return f"<Workspace(id={self.id}, name='{self.name}', organization_id={self.organization_id})>"


class OrganizationMember(Base):
    """
    Model for organization membership with roles.
    """
    __tablename__ = "organization_member_roles"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    role = Column(String(20), default=OrganizationRole.MEMBER.value)
    
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<OrganizationMember(org_id={self.organization_id}, user_id={self.user_id}, role='{self.role}')>"


# Workspace members table
workspace_members = Table(
    'workspace_members',
    Base.metadata,
    Column('workspace_id', Integer, ForeignKey('workspaces.id', ondelete='CASCADE'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role', String(20), default=OrganizationRole.MEMBER.value),
)
