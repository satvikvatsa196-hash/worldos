from datetime import datetime
import uuid
from typing import Optional, List, Any
from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, JSON, Enum, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.infrastructure.database import Base

class World(Base):
    __tablename__ = "worlds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    seed: Mapped[str] = mapped_column(String, nullable=False)
    current_tick: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    simulation_status: Mapped[str] = mapped_column(String, nullable=False, default="initialized")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    cities: Mapped[List["City"]] = relationship(back_populates="world", cascade="all, delete-orphan")
    characters: Mapped[List["Character"]] = relationship(back_populates="world", cascade="all, delete-orphan")
    factions: Mapped[List["Faction"]] = relationship(back_populates="world", cascade="all, delete-orphan")
    resources: Mapped[List["Resource"]] = relationship(back_populates="world", cascade="all, delete-orphan")
    events: Mapped[List["Event"]] = relationship(back_populates="world", cascade="all, delete-orphan")
    decisions: Mapped[List["AgentDecisionRecord"]] = relationship(back_populates="world", cascade="all, delete-orphan")


class City(Base):
    __tablename__ = "cities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    population: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wealth: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    stability: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    food_supply: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unrest: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tax_rate: Mapped[float] = mapped_column(Float, default=0.1, nullable=False)

    world: Mapped["World"] = relationship(back_populates="cities")
    characters: Mapped[List["Character"]] = relationship(back_populates="city")


class Faction(Base):
    __tablename__ = "factions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    ideology: Mapped[str] = mapped_column(String, nullable=False)
    wealth: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    power: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    leader_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("characters.id", use_alter=True, name="fk_faction_leader_id", ondelete="SET NULL"), nullable=True)

    world: Mapped["World"] = relationship(back_populates="factions")
    leader: Mapped[Optional["Character"]] = relationship(foreign_keys=[leader_id], post_update=True)
    members: Mapped[List["Character"]] = relationship(back_populates="faction", foreign_keys="[Character.faction_id]")


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    occupation: Mapped[str] = mapped_column(String, nullable=False)
    wealth: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    health: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    city_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("cities.id", ondelete="SET NULL"), nullable=True)
    faction_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("factions.id", ondelete="SET NULL"), nullable=True)
    personality_traits: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)

    world: Mapped["World"] = relationship(back_populates="characters")
    city: Mapped[Optional["City"]] = relationship(back_populates="characters")
    faction: Mapped[Optional["Faction"]] = relationship(back_populates="members", foreign_keys=[faction_id])
    
    goals: Mapped[List["Goal"]] = relationship(back_populates="character", cascade="all, delete-orphan")
    memories: Mapped[List["Memory"]] = relationship(back_populates="character", cascade="all, delete-orphan")
    beliefs: Mapped[List["Belief"]] = relationship(back_populates="character", cascade="all, delete-orphan")
    decisions: Mapped[List["AgentDecisionRecord"]] = relationship(back_populates="character", cascade="all, delete-orphan")
    
    relationships_out: Mapped[List["Relationship"]] = relationship(
        back_populates="source_character",
        foreign_keys="[Relationship.source_character_id]",
        cascade="all, delete-orphan"
    )
    relationships_in: Mapped[List["Relationship"]] = relationship(
        back_populates="target_character",
        foreign_keys="[Relationship.target_character_id]",
        cascade="all, delete-orphan"
    )


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    current_price: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    total_supply: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_demand: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    world: Mapped["World"] = relationship(back_populates="resources")


class Inventory(Base):
    __tablename__ = "inventories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    owner_type: Mapped[str] = mapped_column(String, nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    resource: Mapped["Resource"] = relationship()


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_character_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    target_character_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    trust: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    respect: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    fear: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    friendship: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    hostility: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    influence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    obligation: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    source_character: Mapped["Character"] = relationship(back_populates="relationships_out", foreign_keys=[source_character_id])
    target_character: Mapped["Character"] = relationship(back_populates="relationships_in", foreign_keys=[target_character_id])

    __table_args__ = (
        UniqueConstraint("source_character_id", "target_character_id", name="uq_relationship_source_target"),
        CheckConstraint("source_character_id != target_character_id", name="chk_no_self_relationship")
    )


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    target_information: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    character: Mapped["Character"] = relationship(back_populates="goals")


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(String, nullable=False)
    importance: Mapped[float] = mapped_column(Float, nullable=False)
    tick: Mapped[int] = mapped_column(Integer, nullable=False)
    related_entities: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    source_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("events.id", ondelete="SET NULL"), nullable=True)

    character: Mapped["Character"] = relationship(back_populates="memories")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False)
    tick: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    target_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    city_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("cities.id", ondelete="SET NULL"), nullable=True)
    faction_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("factions.id", ondelete="SET NULL"), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    parent_event_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("events.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    world: Mapped["World"] = relationship(back_populates="events")


class EconomicTransaction(Base):
    __tablename__ = "economic_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False)
    buyer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    seller_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    buyer_type: Mapped[str] = mapped_column(String, nullable=False)
    seller_type: Mapped[str] = mapped_column(String, nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_value: Mapped[float] = mapped_column(Float, nullable=False)
    tick: Mapped[int] = mapped_column(Integer, nullable=False)

    world: Mapped["World"] = relationship()
    resource: Mapped["Resource"] = relationship()

class Belief(Base):
    __tablename__ = "beliefs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    subject_type: Mapped[str] = mapped_column(String, nullable=False) 
    belief_type: Mapped[str] = mapped_column(String, nullable=False) 
    value: Mapped[float] = mapped_column(Float, nullable=False) 
    confidence: Mapped[float] = mapped_column(Float, nullable=False) 

    character: Mapped["Character"] = relationship(back_populates="beliefs")

class AgentDecisionRecord(Base):
    __tablename__ = "agent_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), nullable=False)
    world_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), nullable=False)
    tick: Mapped[int] = mapped_column(Integer, nullable=False)
    decision_summary: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    latency: Mapped[float] = mapped_column(Float, nullable=False)
    token_usage: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    world: Mapped["World"] = relationship(back_populates="decisions")
    character: Mapped["Character"] = relationship(back_populates="decisions")
