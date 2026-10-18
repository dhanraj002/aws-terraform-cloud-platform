import unittest
from scripts.check_plan import violations, REQUIRED
class TagTest(unittest.TestCase):
    def plan(self, tags=None, actions=None, kind='aws_vpc'):
        return {'resource_changes':[{'address':'test.resource', 'mode':'managed', 'type':kind,
            'change':{'actions':actions or ['create'], 'after':{'tags_all':tags}}}]}
    def test_valid(self):
        self.assertEqual(violations(self.plan(dict.fromkeys(REQUIRED,'lab'))), [])
    def test_missing_and_unknown_fail(self):
        self.assertTrue(violations(self.plan()))
        self.assertTrue(violations(self.plan({'Owner':''})))
    def test_delete_and_untaggable_ignored(self):
        self.assertEqual(violations(self.plan(actions=['delete'])), [])
        self.assertEqual(violations(self.plan(kind='aws_route_table_association')), [])
