from typing import List, Tuple
import uuid
from app.domain.event.models import WorldEvent, EventType
from app.domain.relationship.models import CharacterRelationship

class RelationshipEngine:
    """
    Evaluates events and updates character relationships.
    Generates RELATIONSHIP_CHANGED events.
    """
    def __init__(self):
        pass

    def process_event(
        self, 
        event: WorldEvent, 
        current_relationships: List[CharacterRelationship]
    ) -> Tuple[List[CharacterRelationship], List[WorldEvent]]:
        """
        Processes an event, returning updated relationships and any generated relationship events.
        """
        generated_events = []
        updated_rels = list(current_relationships)

        if event.type == EventType.TRADE:
            amount = event.payload.get("amount", 0)
            if event.actor_id and event.target_id:
                # Both parties experience a successful trade
                generated_events.extend(self._update_relationship(
                    updated_rels, event.actor_id, event.target_id, event.world_id, event.tick,
                    trust_change=0.1, respect_change=0.05
                ))
                generated_events.extend(self._update_relationship(
                    updated_rels, event.target_id, event.actor_id, event.world_id, event.tick,
                    trust_change=0.1, respect_change=0.05
                ))
                
        elif event.type == EventType.CONFLICT:
            is_betrayal = event.payload.get("betrayal", False)
            if event.actor_id and event.target_id:
                # Actor attacked/betrayed Target
                if is_betrayal:
                    generated_events.extend(self._update_relationship(
                        updated_rels, event.target_id, event.actor_id, event.world_id, event.tick,
                        trust_change=-0.8, hostility_change=0.6, friendship_change=-0.5
                    ))
                else:
                    generated_events.extend(self._update_relationship(
                        updated_rels, event.target_id, event.actor_id, event.world_id, event.tick,
                        trust_change=-0.2, hostility_change=0.3, fear_change=0.2
                    ))

        elif event.type == EventType.CHARACTER_ACTION:
            action = event.payload.get("action")
            if action == "HELP" and event.actor_id and event.target_id:
                is_crisis = event.payload.get("crisis", False)
                if is_crisis:
                    generated_events.extend(self._update_relationship(
                        updated_rels, event.target_id, event.actor_id, event.world_id, event.tick,
                        trust_change=0.5, friendship_change=0.4, obligation_change=0.6
                    ))
                else:
                    generated_events.extend(self._update_relationship(
                        updated_rels, event.target_id, event.actor_id, event.world_id, event.tick,
                        trust_change=0.2, friendship_change=0.1, obligation_change=0.2
                    ))
            elif action == "POLITICAL_DISAGREEMENT" and event.actor_id and event.target_id:
                generated_events.extend(self._update_relationship(
                    updated_rels, event.target_id, event.actor_id, event.world_id, event.tick,
                    respect_change=-0.2, friendship_change=-0.1
                ))
                generated_events.extend(self._update_relationship(
                    updated_rels, event.actor_id, event.target_id, event.world_id, event.tick,
                    respect_change=-0.2, friendship_change=-0.1
                ))

        return updated_rels, generated_events

    def _update_relationship(
        self,
        relationships: List[CharacterRelationship],
        source_id: uuid.UUID,
        target_id: uuid.UUID,
        world_id: uuid.UUID,
        tick: int,
        trust_change: float = 0.0,
        respect_change: float = 0.0,
        fear_change: float = 0.0,
        friendship_change: float = 0.0,
        hostility_change: float = 0.0,
        influence_change: float = 0.0,
        obligation_change: float = 0.0
    ) -> List[WorldEvent]:
        
        rel = next((r for r in relationships if r.source_character_id == source_id and r.target_character_id == target_id), None)
        if not rel:
            rel = CharacterRelationship(source_character_id=source_id, target_character_id=target_id)
            relationships.append(rel)

        def clamp(val, min_val, max_val):
            return max(min_val, min(val, max_val))
            
        old_trust = rel.trust
        
        rel.trust = clamp(rel.trust + trust_change, -1.0, 1.0)
        rel.respect = clamp(rel.respect + respect_change, -1.0, 1.0)
        rel.fear = clamp(rel.fear + fear_change, 0.0, 1.0)
        rel.friendship = clamp(rel.friendship + friendship_change, -1.0, 1.0)
        rel.hostility = clamp(rel.hostility + hostility_change, 0.0, 1.0)
        rel.influence = clamp(rel.influence + influence_change, -1.0, 1.0)
        rel.obligation = clamp(rel.obligation + obligation_change, -1.0, 1.0)

        events = []
        if (trust_change != 0 or respect_change != 0 or fear_change != 0 or 
            friendship_change != 0 or hostility_change != 0 or influence_change != 0 or obligation_change != 0):
            
            events.append(WorldEvent(
                world_id=world_id,
                tick=tick,
                type=EventType.RELATIONSHIP_CHANGED,
                actor_id=source_id,
                target_id=target_id,
                payload={
                    "trust_change": trust_change,
                    "respect_change": respect_change,
                    "fear_change": fear_change,
                    "friendship_change": friendship_change,
                    "hostility_change": hostility_change,
                    "influence_change": influence_change,
                    "obligation_change": obligation_change,
                    "old_trust": old_trust,
                    "new_trust": rel.trust
                }
            ))

        return events
