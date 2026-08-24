import uuid
from typing import List, Any
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.agents.models import AgentAction, ActionType
from app.infrastructure.models import Character, City, Faction, Resource, Inventory
from app.domain.event.models import WorldEvent, EventType
from app.core.telemetry import TraceLogger

logger = TraceLogger(__name__)

class ExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    REJECTED = "REJECTED"
    FAILED = "FAILED"

class ActionExecutionResult(BaseModel):
    action_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    status: ExecutionStatus
    reason: str
    events_generated: List[WorldEvent] = Field(default_factory=list)

class ActionExecutionEngine:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute(self, action: AgentAction, world_id: uuid.UUID, current_tick: int) -> ActionExecutionResult:
        try:
            async with self.session.begin_nested():
                # Fetch Actor
                actor_stmt = select(Character).where(Character.id == action.actor_id)
                actor_result = await self.session.execute(actor_stmt)
                actor = actor_result.scalar_one_or_none()
                
                if not actor:
                    return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Actor does not exist")
                if actor.world_id != world_id:
                    return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Actor does not belong to this world")

                result = None
                
                if action.action_type == ActionType.BUY_RESOURCE:
                    result = await self._execute_buy(actor, action, current_tick)
                elif action.action_type == ActionType.SELL_RESOURCE:
                    result = await self._execute_sell(actor, action, current_tick)
                elif action.action_type == ActionType.MOVE:
                    result = await self._execute_move(actor, action, current_tick)
                elif action.action_type == ActionType.JOIN_FACTION:
                    result = await self._execute_join_faction(actor, action, current_tick)
                elif action.action_type == ActionType.LEAVE_FACTION:
                    result = await self._execute_leave_faction(actor, action, current_tick)
                elif action.action_type == ActionType.GIVE_MONEY:
                    result = await self._execute_give_money(actor, action, current_tick)
                elif action.action_type == ActionType.WORK:
                    result = await self._execute_work(actor, action, current_tick)
                elif action.action_type == ActionType.PROTEST:
                    result = await self._execute_protest(actor, action, current_tick)
                elif action.action_type in (ActionType.SUPPORT_POLICY, ActionType.OPPOSE_POLICY):
                    result = await self._execute_policy(actor, action, current_tick)
                elif action.action_type == ActionType.DO_NOTHING:
                    result = ActionExecutionResult(status=ExecutionStatus.SUCCESS, reason="Did nothing")
                else:
                    return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Unsupported action type")

                if result.status == ExecutionStatus.REJECTED:
                    # Rollback changes if validation inside handlers failed
                    await self.session.rollback()
                    logger.warning("Action execution rejected", world_id=str(world_id), tick=current_tick, action_id=str(result.action_id), actor_id=str(action.actor_id), action_type=action.action_type.value, reason=result.reason)
                else:
                    logger.info("Action execution successful", world_id=str(world_id), tick=current_tick, action_id=str(result.action_id), actor_id=str(action.actor_id), action_type=action.action_type.value, events_count=len(result.events_generated))
                    
                return result
                
        except Exception as e:
            await self.session.rollback()
            logger.error("Action execution failed", world_id=str(world_id), tick=current_tick, actor_id=str(action.actor_id), action_type=action.action_type.value, error=str(e))
            return ActionExecutionResult(status=ExecutionStatus.FAILED, reason=f"Execution error: {str(e)}")

    async def _execute_buy(self, actor: Character, action: AgentAction, tick: int) -> ActionExecutionResult:
        resource_id = action.parameters.get("resource_id")
        quantity = action.parameters.get("quantity", 1.0)
        
        if not resource_id:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Missing resource_id")
            
        try:
            resource_uuid = uuid.UUID(resource_id)
        except ValueError:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Invalid resource_id format")

        res_stmt = select(Resource).where(Resource.id == resource_uuid)
        res_result = await self.session.execute(res_stmt)
        resource = res_result.scalar_one_or_none()
        
        if not resource:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Resource does not exist")
            
        cost = resource.current_price * quantity
        if actor.wealth < cost:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Insufficient wealth")
            
        actor.wealth -= cost
        
        inv_stmt = select(Inventory).where(Inventory.owner_id == actor.id, Inventory.resource_id == resource_uuid)
        inv_result = await self.session.execute(inv_stmt)
        inventory = inv_result.scalar_one_or_none()
        
        if inventory:
            inventory.quantity += quantity
        else:
            inventory = Inventory(owner_id=actor.id, owner_type="character", resource_id=resource_uuid, quantity=quantity)
            self.session.add(inventory)
            
        event = WorldEvent(
            world_id=actor.world_id,
            tick=tick,
            type=EventType.TRADE,
            actor_id=actor.id,
            city_id=actor.city_id,
            payload={"action": "BUY", "resource_id": str(resource_id), "quantity": quantity, "cost": cost}
        )
        return ActionExecutionResult(status=ExecutionStatus.SUCCESS, reason="Bought resource", events_generated=[event])

    async def _execute_sell(self, actor: Character, action: AgentAction, tick: int) -> ActionExecutionResult:
        resource_id = action.parameters.get("resource_id")
        quantity = action.parameters.get("quantity", 1.0)
        
        if not resource_id:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Missing resource_id")

        try:
            resource_uuid = uuid.UUID(resource_id)
        except ValueError:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Invalid resource_id format")

        inv_stmt = select(Inventory).where(Inventory.owner_id == actor.id, Inventory.resource_id == resource_uuid)
        inv_result = await self.session.execute(inv_stmt)
        inventory = inv_result.scalar_one_or_none()
        
        if not inventory or inventory.quantity < quantity:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Insufficient inventory")
            
        res_stmt = select(Resource).where(Resource.id == resource_uuid)
        res_result = await self.session.execute(res_stmt)
        resource = res_result.scalar_one_or_none()
        
        if not resource:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Resource does not exist")
            
        revenue = resource.current_price * quantity
        actor.wealth += revenue
        inventory.quantity -= quantity
        
        event = WorldEvent(
            world_id=actor.world_id,
            tick=tick,
            type=EventType.TRADE,
            actor_id=actor.id,
            city_id=actor.city_id,
            payload={"action": "SELL", "resource_id": str(resource_id), "quantity": quantity, "revenue": revenue}
        )
        return ActionExecutionResult(status=ExecutionStatus.SUCCESS, reason="Sold resource", events_generated=[event])

    async def _execute_move(self, actor: Character, action: AgentAction, tick: int) -> ActionExecutionResult:
        city_id = action.parameters.get("city_id")
        if not city_id:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Missing city_id")

        try:
            city_uuid = uuid.UUID(city_id)
        except ValueError:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Invalid city_id format")

        city_stmt = select(City).where(City.id == city_uuid)
        city_result = await self.session.execute(city_stmt)
        city = city_result.scalar_one_or_none()
        
        if not city:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="City does not exist")
            
        if actor.city_id == city_uuid:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Already in that city")
            
        old_city = actor.city_id
        actor.city_id = city_uuid
        
        event = WorldEvent(
            world_id=actor.world_id,
            tick=tick,
            type=EventType.MIGRATION,
            actor_id=actor.id,
            payload={"from_city": str(old_city) if old_city else None, "to_city": str(city_uuid)}
        )
        return ActionExecutionResult(status=ExecutionStatus.SUCCESS, reason="Moved to city", events_generated=[event])

    async def _execute_join_faction(self, actor: Character, action: AgentAction, tick: int) -> ActionExecutionResult:
        faction_id = action.parameters.get("faction_id")
        if not faction_id:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Missing faction_id")

        try:
            faction_uuid = uuid.UUID(faction_id)
        except ValueError:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Invalid faction_id format")

        faction_stmt = select(Faction).where(Faction.id == faction_uuid)
        faction_result = await self.session.execute(faction_stmt)
        faction = faction_result.scalar_one_or_none()
        
        if not faction:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Faction does not exist")
            
        if actor.faction_id == faction_uuid:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Already in faction")
            
        actor.faction_id = faction_uuid
        
        event = WorldEvent(
            world_id=actor.world_id,
            tick=tick,
            type=EventType.FACTION_ACTION,
            actor_id=actor.id,
            faction_id=faction_uuid,
            payload={"action": "JOIN"}
        )
        return ActionExecutionResult(status=ExecutionStatus.SUCCESS, reason="Joined faction", events_generated=[event])

    async def _execute_leave_faction(self, actor: Character, action: AgentAction, tick: int) -> ActionExecutionResult:
        if not actor.faction_id:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Not in any faction")
            
        old_faction = actor.faction_id
        actor.faction_id = None
        
        event = WorldEvent(
            world_id=actor.world_id,
            tick=tick,
            type=EventType.FACTION_ACTION,
            actor_id=actor.id,
            faction_id=old_faction,
            payload={"action": "LEAVE"}
        )
        return ActionExecutionResult(status=ExecutionStatus.SUCCESS, reason="Left faction", events_generated=[event])

    async def _execute_give_money(self, actor: Character, action: AgentAction, tick: int) -> ActionExecutionResult:
        target_id = action.target_id
        amount = action.parameters.get("amount", 0.0)
        
        if not target_id:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Missing target_id")
            
        if amount <= 0:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Amount must be positive")
            
        if actor.wealth < amount:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Insufficient wealth")
            
        target_stmt = select(Character).where(Character.id == target_id)
        target_result = await self.session.execute(target_stmt)
        target = target_result.scalar_one_or_none()
        
        if not target:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Target does not exist")
            
        actor.wealth -= amount
        target.wealth += amount
        
        event = WorldEvent(
            world_id=actor.world_id,
            tick=tick,
            type=EventType.CHARACTER_ACTION,
            actor_id=actor.id,
            target_id=target.id,
            payload={"action": "GIVE_MONEY", "amount": amount}
        )
        return ActionExecutionResult(status=ExecutionStatus.SUCCESS, reason="Gave money", events_generated=[event])

    async def _execute_work(self, actor: Character, action: AgentAction, tick: int) -> ActionExecutionResult:
        # Simple implementation: earn base wage from city
        wage = 10.0
        
        city_stmt = select(City).where(City.id == actor.city_id)
        city_result = await self.session.execute(city_stmt)
        city = city_result.scalar_one_or_none()
        
        if not city:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="Actor not in a city")
            
        if city.wealth < wage:
            return ActionExecutionResult(status=ExecutionStatus.REJECTED, reason="City has insufficient funds to pay wage")
            
        city.wealth -= wage
        actor.wealth += wage
        
        event = WorldEvent(
            world_id=actor.world_id,
            tick=tick,
            type=EventType.CHARACTER_ACTION,
            actor_id=actor.id,
            payload={"action": "WORK", "earned": wage}
        )
        return ActionExecutionResult(status=ExecutionStatus.SUCCESS, reason="Worked", events_generated=[event])
        
    async def _execute_protest(self, actor: Character, action: AgentAction, tick: int) -> ActionExecutionResult:
        event = WorldEvent(
            world_id=actor.world_id,
            tick=tick,
            type=EventType.PROTEST,
            actor_id=actor.id,
            city_id=actor.city_id,
            payload={"reason": action.justification_summary}
        )
        return ActionExecutionResult(status=ExecutionStatus.SUCCESS, reason="Protested", events_generated=[event])

    async def _execute_policy(self, actor: Character, action: AgentAction, tick: int) -> ActionExecutionResult:
        policy_id = action.parameters.get("policy_id", "unknown")
        
        event = WorldEvent(
            world_id=actor.world_id,
            tick=tick,
            type=EventType.POLITICAL_CHANGE,
            actor_id=actor.id,
            payload={
                "action": action.action_type.value,
                "policy_id": policy_id, 
                "reason": action.justification_summary
            }
        )
        return ActionExecutionResult(status=ExecutionStatus.SUCCESS, reason="Policy stance declared", events_generated=[event])
