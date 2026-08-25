import random
import uuid
from typing import Dict, List, Any
from pydantic import BaseModel
from app.infrastructure.models import (
    World, City, Character, Faction, Resource, Inventory, Relationship, Goal
)

class GeneratorConfig(BaseModel):
    name: str
    seed: int
    cities: int
    characters: int
    factions: int

OCCUPATIONS = ["farmer", "merchant", "worker", "miner", "woodcutter", "soldier", "politician"]
RESOURCE_TYPES = ["Food", "Wood", "Stone", "Iron", "Gold"]

FACTION_TYPES = {
    "merchant": ["Merchant Guild", "Trading Company"],
    "military": ["City Guard", "Mercenary Band", "Royal Army"],
    "worker": ["Miners Union", "Farmers Collective", "Builders Guild"],
    "political": ["City Council", "Noble House"]
}

class WorldGenerator:
    def __init__(self, config: GeneratorConfig):
        self.config = config
        self.rng = random.Random(config.seed)
        
    def generate(self) -> Dict[str, Any]:
        """
        Generates a coherent deterministic world.
        Returns a dictionary containing all generated SQLAlchemy model instances.
        """
        # Create world
        world = World(
            id=uuid.uuid4(),
            name=self.config.name,
            seed=str(self.config.seed),
            current_tick=0,
            simulation_status="initialized"
        )

        # Create resources
        resources = []
        for res_name in RESOURCE_TYPES:
            resources.append(Resource(
                id=uuid.uuid4(),
                world_id=world.id,
                name=res_name,
                current_price=self.rng.uniform(1.0, 10.0),
                total_supply=self.rng.uniform(100.0, 1000.0),
                total_demand=self.rng.uniform(50.0, 800.0)
            ))
            
        resource_map = {r.name: r for r in resources}

        # Create cities
        cities = []
        for i in range(self.config.cities):
            cities.append(City(
                id=uuid.uuid4(),
                world_id=world.id,
                name=f"City_{i+1}",
                population=self.rng.randint(1000, 5000),
                wealth=self.rng.uniform(1000.0, 50000.0),
                stability=self.rng.uniform(0.4, 1.0),
                food_supply=self.rng.uniform(500.0, 2000.0),
                unrest=self.rng.uniform(0.0, 0.5),
                tax_rate=self.rng.uniform(0.05, 0.2)
            ))

        # Create factions
        factions = []
        faction_roles = []
        for i in range(self.config.factions):
            category = self.rng.choice(list(FACTION_TYPES.keys()))
            f_name_template = self.rng.choice(FACTION_TYPES[category])
            factions.append(Faction(
                id=uuid.uuid4(),
                world_id=world.id,
                name=f"{f_name_template} {i+1}",
                type=category,
                ideology=self.rng.choice(["Authoritarian", "Libertarian", "Neutral", "Progressive", "Conservative"]),
                wealth=self.rng.uniform(500.0, 10000.0),
                power=self.rng.uniform(10.0, 100.0),
                leader_id=None # assigned later
            ))
            faction_roles.append(category)

        # Create characters
        characters = []
        inventories = []
        goals = []
        
        for i in range(self.config.characters):
            occ = self.rng.choice(OCCUPATIONS)
            city = self.rng.choice(cities)
            
            # Logic for coherent faction assignment based on occupation
            eligible_factions = [f for f in factions if f.type == self._map_occ_to_faction_type(occ)]
            if not eligible_factions:
                eligible_factions = factions # fallback
                
            faction = self.rng.choice(eligible_factions) if self.rng.random() > 0.3 else None
            
            char_id = uuid.uuid4()
            
            # Consistent traits
            traits = self._generate_traits(occ)
            
            character = Character(
                id=char_id,
                world_id=world.id,
                name=f"Character_{i+1}_{occ}",
                age=self.rng.randint(18, 70),
                occupation=occ,
                wealth=self.rng.uniform(10.0, 1000.0) * (2.0 if occ in ["merchant", "politician"] else 1.0),
                health=self.rng.uniform(50.0, 100.0),
                city_id=city.id,
                faction_id=faction.id if faction else None,
                personality_traits=traits,
                status="alive"
            )
            characters.append(character)

            # Assign resources based on occupation
            self._assign_initial_inventory(character, resource_map, inventories)
            
            # Assign goals based on occupation
            self._assign_goals(character, goals)

        # Assign leaders to factions
        for faction in factions:
            members = [c for c in characters if c.faction_id == faction.id]
            if members:
                # Pick wealthiest or highest influence (politician)
                leader = max(members, key=lambda c: c.wealth + (1000 if c.occupation == "politician" else 0))
                faction.leader = leader
                
        # Generate relationships (ensure deterministic)
        relationships = []
        for i, char1 in enumerate(characters):
            # Connect to 1-3 random characters
            num_links = self.rng.randint(1, 3)
            targets = self.rng.sample(characters, min(num_links + 1, len(characters)))
            for char2 in targets:
                if char1.id == char2.id:
                    continue
                # Check existing
                if any(r.source_character_id == char1.id and r.target_character_id == char2.id for r in relationships):
                    continue
                    
                # Base relationship logic
                friendship = self.rng.uniform(0.0, 100.0)
                hostility = 100.0 - friendship if self.rng.random() > 0.5 else self.rng.uniform(0.0, 50.0)
                
                # Boost if same faction/city
                if char1.faction_id == char2.faction_id and char1.faction_id is not None:
                    friendship += 20.0
                if char1.city_id == char2.city_id:
                    friendship += 10.0
                    
                relationships.append(Relationship(
                    id=uuid.uuid4(),
                    source_character_id=char1.id,
                    target_character_id=char2.id,
                    trust=self.rng.uniform(0.0, min(100.0, friendship + 20)),
                    respect=self.rng.uniform(0.0, 100.0),
                    fear=self.rng.uniform(0.0, hostility),
                    friendship=min(100.0, friendship),
                    hostility=min(100.0, hostility),
                    influence=self.rng.uniform(0.0, 100.0) if char1.occupation in ["politician", "merchant"] else self.rng.uniform(0.0, 30.0)
                ))

        return {
            "world": world,
            "resources": resources,
            "cities": cities,
            "factions": factions,
            "characters": characters,
            "inventories": inventories,
            "goals": goals,
            "relationships": relationships
        }

    def _map_occ_to_faction_type(self, occ: str) -> str:
        if occ in ["merchant"]: return "merchant"
        if occ in ["soldier"]: return "military"
        if occ in ["farmer", "worker", "miner", "woodcutter"]: return "worker"
        if occ in ["politician"]: return "political"
        return "worker"

    def _generate_traits(self, occ: str) -> Dict[str, float]:
        traits = {
            "greed": self.rng.uniform(0.0, 1.0),
            "ambition": self.rng.uniform(0.0, 1.0),
            "loyalty": self.rng.uniform(0.0, 1.0),
            "risk_tolerance": self.rng.uniform(0.0, 1.0),
            "aggression": self.rng.uniform(0.0, 1.0),
            "empathy": self.rng.uniform(0.0, 1.0),
            "sociability": self.rng.uniform(0.0, 1.0),
            "political_alignment": self.rng.uniform(-1.0, 1.0) # -1 left, 1 right
        }
        
        # Adjust for occupation coherence
        if occ == "merchant":
            traits["greed"] = self.rng.uniform(0.6, 1.0)
            traits["sociability"] = self.rng.uniform(0.5, 1.0)
        elif occ == "soldier":
            traits["aggression"] = self.rng.uniform(0.5, 1.0)
            traits["loyalty"] = self.rng.uniform(0.5, 1.0)
        elif occ == "politician":
            traits["ambition"] = self.rng.uniform(0.7, 1.0)
            traits["sociability"] = self.rng.uniform(0.7, 1.0)
        elif occ == "farmer":
            traits["risk_tolerance"] = self.rng.uniform(0.0, 0.4)
            
        return traits

    def _assign_initial_inventory(self, character: Character, resource_map: Dict[str, Resource], inventories: List[Inventory]):
        # Base minimal food
        inventories.append(Inventory(
            id=uuid.uuid4(),
            owner_id=character.id,
            owner_type="character",
            resource_id=resource_map["Food"].id,
            quantity=self.rng.uniform(5.0, 20.0)
        ))
        
        occ = character.occupation
        if occ == "farmer":
            inventories.append(Inventory(id=uuid.uuid4(), owner_id=character.id, owner_type="character", resource_id=resource_map["Food"].id, quantity=self.rng.uniform(50.0, 200.0)))
        elif occ == "woodcutter":
            inventories.append(Inventory(id=uuid.uuid4(), owner_id=character.id, owner_type="character", resource_id=resource_map["Wood"].id, quantity=self.rng.uniform(20.0, 100.0)))
        elif occ == "miner":
            if self.rng.random() > 0.5:
                inventories.append(Inventory(id=uuid.uuid4(), owner_id=character.id, owner_type="character", resource_id=resource_map["Stone"].id, quantity=self.rng.uniform(20.0, 80.0)))
            else:
                inventories.append(Inventory(id=uuid.uuid4(), owner_id=character.id, owner_type="character", resource_id=resource_map["Iron"].id, quantity=self.rng.uniform(10.0, 50.0)))
        elif occ == "merchant":
            inventories.append(Inventory(id=uuid.uuid4(), owner_id=character.id, owner_type="character", resource_id=resource_map["Gold"].id, quantity=self.rng.uniform(50.0, 300.0)))
            # Random resource stock
            random_res = self.rng.choice(list(resource_map.values()))
            inventories.append(Inventory(id=uuid.uuid4(), owner_id=character.id, owner_type="character", resource_id=random_res.id, quantity=self.rng.uniform(20.0, 100.0)))

    def _assign_goals(self, character: Character, goals: List[Goal]):
        occ = character.occupation
        if occ == "politician":
            desc = "Gain more political influence in the city"
        elif occ == "merchant":
            desc = "Amas a fortune of 5000 wealth"
        elif occ == "soldier":
            desc = "Rise through the ranks of the military"
        else:
            desc = "Ensure basic survival and stability"
            
        goals.append(Goal(
            id=uuid.uuid4(),
            character_id=character.id,
            description=desc,
            priority=self.rng.randint(1, 5),
            status="active",
            target_information={"type": "occupation_based", "target": occ}
        ))
