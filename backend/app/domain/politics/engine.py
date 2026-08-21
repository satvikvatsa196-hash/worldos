import uuid
from typing import List, Tuple, Dict, Any
from app.domain.politics.models import Government, Policy, PolicyType
from app.domain.event.models import WorldEvent, EventType
from app.agents.models import ActionType

class PoliticalEngine:
    """
    Evaluates policies, processes political actions, and updates government stability/approval.
    """
    def __init__(self):
        self.base_protest_probability = 0.05

    def clamp(self, value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        return max(min_val, min(value, max_val))

    def evaluate_policies(
        self, 
        government: Government, 
        current_tick: int,
        economic_indicators: Dict[str, float]
    ) -> Tuple[Government, List[WorldEvent]]:
        """
        Deterministically evaluates the effects of active policies on the government and generates events.
        """
        events = []
        approval_delta = 0.0
        stability_delta = 0.0
        
        # We calculate the aggregate effect of policies
        for policy in government.active_policies:
            if not policy.active:
                continue
                
            if policy.type == PolicyType.TAX:
                # High tax -> decreases approval, increases government funds (abstracted here), lowers stability slightly
                if policy.value > 0.2: # arbitrary threshold for high tax
                    approval_delta -= 0.05 * policy.value
                    stability_delta -= 0.02 * policy.value
                else:
                    stability_delta += 0.01 * policy.value
                    
                events.append(WorldEvent(
                    world_id=government.world_id,
                    tick=current_tick,
                    type=EventType.POLICY_CHANGED,
                    payload={"policy_id": str(policy.id), "effect": "tax_applied", "value": policy.value}
                ))
                
            elif policy.type == PolicyType.FOOD_PRICE:
                # High food price -> high citizen dissatisfaction -> massive approval drop -> protest probability up
                if policy.value > 1.5: 
                    approval_delta -= 0.1 * (policy.value - 1.0)
                    stability_delta -= 0.05 * (policy.value - 1.0)
                else:
                    approval_delta += 0.05
                    
            elif policy.type == PolicyType.MILITARY_SPENDING:
                # High military spending -> high security capacity, potential stability increase, slight approval drop
                government.security_capacity = self.clamp(government.security_capacity + (0.05 * policy.value))
                stability_delta += 0.02 * policy.value
                approval_delta -= 0.01 * policy.value

            elif policy.type == PolicyType.SUBSIDY:
                # Subsidy increases approval but might drain wealth
                approval_delta += 0.05 * policy.value
                
            elif policy.type == PolicyType.WAGE:
                if policy.value < 1.0:
                    approval_delta -= 0.08
                else:
                    approval_delta += 0.05
                    
        # Apply deltas deterministically
        government.approval = self.clamp(government.approval + approval_delta)
        government.stability = self.clamp(government.stability + stability_delta)
        
        # If approval gets too low, generate a protest event probability/trigger
        protest_prob = self.base_protest_probability + (1.0 - government.approval) * 0.8
        # We can deterministically trigger if protest_prob > threshold instead of random
        if protest_prob > 0.6:
            events.append(WorldEvent(
                world_id=government.world_id,
                tick=current_tick,
                type=EventType.PROTEST,
                payload={"reason": "low_approval", "severity": protest_prob}
            ))
            
        return government, events

    def process_political_actions(
        self,
        government: Government,
        actions: List[Dict[str, Any]],
        current_tick: int
    ) -> Tuple[Government, List[WorldEvent]]:
        """
        Process explicit political actions like PROTEST, SUPPORT_POLICY, etc.
        """
        events = []
        for action in actions:
            action_type = action.get("type")
            actor_id = action.get("actor_id")
            
            if action_type == ActionType.PROTEST:
                # Protest lowers stability and approval
                intensity = action.get("parameters", {}).get("intensity", 0.1)
                government.stability = self.clamp(government.stability - (0.1 * intensity))
                government.approval = self.clamp(government.approval - (0.05 * intensity))
                events.append(WorldEvent(
                    world_id=government.world_id,
                    tick=current_tick,
                    type=EventType.PROTEST,
                    actor_id=actor_id,
                    payload={"intensity": intensity, "effect": "destabilization"}
                ))
                
            elif action_type == ActionType.FUND_PROTEST:
                funding = action.get("parameters", {}).get("amount", 100)
                # Funding a protest heavily impacts stability deterministically based on amount
                impact = min(0.2, funding / 5000.0)
                government.stability = self.clamp(government.stability - impact)
                
            elif action_type == ActionType.SUPPORT_POLICY:
                government.approval = self.clamp(government.approval + 0.02)
                government.political_influence = self.clamp(government.political_influence + 0.01)
                
            elif action_type == ActionType.OPPOSE_POLICY:
                government.approval = self.clamp(government.approval - 0.02)
                government.political_influence = self.clamp(government.political_influence - 0.01)
                
            elif action_type == ActionType.DEPLOY_SECURITY:
                # Deploying security raises stability but severely lowers approval
                force_level = action.get("parameters", {}).get("force_level", 0.5)
                # Only effective if capacity exists
                effective_force = min(force_level, government.security_capacity)
                government.stability = self.clamp(government.stability + (0.2 * effective_force))
                government.approval = self.clamp(government.approval - (0.15 * effective_force))
                
            elif action_type == ActionType.THREATEN_STRIKE:
                government.stability = self.clamp(government.stability - 0.05)
                
        return government, events
