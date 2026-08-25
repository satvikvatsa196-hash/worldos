"""add missing indexes

Revision ID: b2f91a03a85b
Revises: af9a2af3e84d
Create Date: 2026-08-25 00:15:19.079473

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b2f91a03a85b'
down_revision = 'af9a2af3e84d'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add indexes for foreign keys and frequently queried columns
    op.create_index(op.f('ix_cities_world_id'), 'cities', ['world_id'], unique=False)
    op.create_index(op.f('ix_factions_world_id'), 'factions', ['world_id'], unique=False)
    op.create_index(op.f('ix_characters_world_id'), 'characters', ['world_id'], unique=False)
    op.create_index(op.f('ix_resources_world_id'), 'resources', ['world_id'], unique=False)
    op.create_index(op.f('ix_relationships_source_character_id'), 'relationships', ['source_character_id'], unique=False)
    op.create_index(op.f('ix_relationships_target_character_id'), 'relationships', ['target_character_id'], unique=False)
    op.create_index(op.f('ix_goals_character_id'), 'goals', ['character_id'], unique=False)
    op.create_index(op.f('ix_memories_character_id'), 'memories', ['character_id'], unique=False)
    op.create_index(op.f('ix_events_world_id'), 'events', ['world_id'], unique=False)
    op.create_index(op.f('ix_events_tick'), 'events', ['tick'], unique=False)
    op.create_index(op.f('ix_events_type'), 'events', ['type'], unique=False)
    op.create_index(op.f('ix_economic_transactions_world_id'), 'economic_transactions', ['world_id'], unique=False)
    op.create_index(op.f('ix_beliefs_character_id'), 'beliefs', ['character_id'], unique=False)
    op.create_index(op.f('ix_agent_decisions_agent_id'), 'agent_decisions', ['agent_id'], unique=False)
    op.create_index(op.f('ix_agent_decisions_world_id'), 'agent_decisions', ['world_id'], unique=False)
    op.create_index(op.f('ix_agent_decisions_tick'), 'agent_decisions', ['tick'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_agent_decisions_tick'), table_name='agent_decisions')
    op.drop_index(op.f('ix_agent_decisions_world_id'), table_name='agent_decisions')
    op.drop_index(op.f('ix_agent_decisions_agent_id'), table_name='agent_decisions')
    op.drop_index(op.f('ix_beliefs_character_id'), table_name='beliefs')
    op.drop_index(op.f('ix_economic_transactions_world_id'), table_name='economic_transactions')
    op.drop_index(op.f('ix_events_type'), table_name='events')
    op.drop_index(op.f('ix_events_tick'), table_name='events')
    op.drop_index(op.f('ix_events_world_id'), table_name='events')
    op.drop_index(op.f('ix_memories_character_id'), table_name='memories')
    op.drop_index(op.f('ix_goals_character_id'), table_name='goals')
    op.drop_index(op.f('ix_relationships_target_character_id'), table_name='relationships')
    op.drop_index(op.f('ix_relationships_source_character_id'), table_name='relationships')
    op.drop_index(op.f('ix_resources_world_id'), table_name='resources')
    op.drop_index(op.f('ix_characters_world_id'), table_name='characters')
    op.drop_index(op.f('ix_factions_world_id'), table_name='factions')
    op.drop_index(op.f('ix_cities_world_id'), table_name='cities')
