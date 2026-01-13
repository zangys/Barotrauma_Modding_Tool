
import unittest
import shutil
from pathlib import Path
from Code.handlers.user_rules import UserRulesManager
from Code.app_vars import AppConfig

# Mock AppConfig for test
class MockAppConfig:
    @staticmethod
    def get_data_root_path():
        return Path("./test_data")

# Patching
UserRulesManager.init = classmethod(lambda cls: None) 
UserRulesManager._file_path = Path("./test_data/user_rules.json")

class TestUserRules(unittest.TestCase):
    def setUp(self):
        if not Path("./test_data").exists():
            Path("./test_data").mkdir()
        UserRulesManager._rules = []

    def tearDown(self):
        if Path("./test_data").exists():
            shutil.rmtree("./test_data")

    def test_add_rule_simple(self):
        success, msg = UserRulesManager.add_rule("A", "B")
        self.assertTrue(success)
        self.assertEqual(len(UserRulesManager.get_rules()), 1)

    def test_self_dependency(self):
        success, msg = UserRulesManager.add_rule("A", "A")
        self.assertFalse(success)
        self.assertIn("Self-dependency", msg)

    def test_duplicate_rule(self):
        UserRulesManager.add_rule("A", "B")
        success, msg = UserRulesManager.add_rule("A", "B")
        self.assertFalse(success)
        self.assertIn("already exists", msg)

    def test_immediate_cycle(self):
        UserRulesManager.add_rule("A", "B")
        success, msg = UserRulesManager.add_rule("B", "A") # Cycle: A->B->A
        self.assertFalse(success)
        # Should be caught by the specialized immediate check or the generic one
        # Current implementation has explicit immediate check
        
    def test_complex_cycle(self):
        # A -> B -> C
        UserRulesManager.add_rule("A", "B")
        UserRulesManager.add_rule("B", "C")
        
        # Try adding C -> A (Cycle: A->B->C->A)
        # add_rule(C, A) means C must load before A.
        # Check path: Is there path from A (target) to C (subject)?
        # Original logic: add_rule(before, after)
        # _check_path(start=after, end=before)
        # _check_path(start=A, end=C)?
        # Graph: A->B, B->C. Path A->...->C exists.
        # So yes, it should return True and prevent adding.
        
        success, msg = UserRulesManager.add_rule("C", "A") 
        self.assertFalse(success)
        self.assertIn("Circular", msg)
        print(f"Cycle blocked: {msg}")

if __name__ == "__main__":
    unittest.main()
