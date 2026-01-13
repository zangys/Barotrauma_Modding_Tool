
import unittest
from dataclasses import dataclass, field
from typing import Set, List

# Mocking the minimal ModUnit structure needed for the test
@dataclass
class MockModUnit:
    id: str
    name: str
    override_id: Set[str] = field(default_factory=set)

class TestConflictLogic(unittest.TestCase):
    def test_conflict_detection(self):
        # Setup mock mods
        mod1 = MockModUnit(id="mod1", name="Mod One", override_id={"Characters/Human.xml", "Items/Tools.xml"})
        mod2 = MockModUnit(id="mod2", name="Mod Two", override_id={"Characters/Human.xml"}) # Conflict with mod1
        mod3 = MockModUnit(id="mod3", name="Mod Three", override_id={"Map/Outpost.xml"}) # No Conflict
        
        active_mods = [mod1, mod2, mod3]
        
        # Logic to be implemented in ConflictsTab
        from collections import defaultdict
        
        override_map = defaultdict(list)
        for mod in active_mods:
            for oid in mod.override_id:
                override_map[oid].append(mod)
                
        conflicts = {oid: mods for oid, mods in override_map.items() if len(mods) > 1}
        
        # Assertions
        self.assertIn("Characters/Human.xml", conflicts)
        self.assertEqual(len(conflicts["Characters/Human.xml"]), 2)
        self.assertNotIn("Items/Tools.xml", conflicts)
        self.assertNotIn("Map/Outpost.xml", conflicts)
        
        print("Conflict detected:", conflicts.keys())

if __name__ == "__main__":
    unittest.main()
