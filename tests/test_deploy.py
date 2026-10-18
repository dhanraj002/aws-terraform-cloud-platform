import unittest
from scripts.deploy import task_revision, assert_release

IMAGE = '123456789012.dkr.ecr.eu-central-1.amazonaws.com/release-platform@sha256:' + 'a' * 64

class ReleaseTest(unittest.TestCase):
    def test_task_preserves_security_and_drops_read_only_metadata(self):
        original = {'family': 'lab', 'revision': 3, 'status': 'ACTIVE', 'taskRoleArn': 'task-role',
                    'containerDefinitions': [{'name': 'app', 'image': 'old', 'readonlyRootFilesystem': True,
                                              'environment': [{'name': 'EXISTING', 'value': 'keep'}]}]}
        result = task_revision(original, IMAGE, 'commit123', True)
        self.assertNotIn('revision', result)
        self.assertEqual(result['taskRoleArn'], 'task-role')
        self.assertTrue(result['containerDefinitions'][0]['readonlyRootFilesystem'])
        env = {e['name']:e['value'] for e in result['containerDefinitions'][0]['environment']}
        self.assertEqual(env, {'EXISTING':'keep', 'APP_REVISION':'commit123', 'FAIL_READINESS':'true'})
        self.assertEqual(original['containerDefinitions'][0]['image'], 'old')

    def test_reject_mutable_image(self):
        with self.assertRaises(ValueError):
            task_revision({}, 'image:latest', 'revision')

    def service(self, arn='new', state='COMPLETED'):
        return {'desiredCount':2, 'runningCount':2, 'pendingCount':0,
                'deployments':[{'status':'PRIMARY', 'taskDefinition':arn, 'rolloutState':state}]}

    def test_success(self):
        assert_release(self.service(), 'new')

    def test_healthy_rollback_is_failure(self):
        with self.assertRaises(RuntimeError):
            assert_release(self.service('old'), 'new')

    def test_in_progress_is_failure(self):
        with self.assertRaises(RuntimeError):
            assert_release(self.service(state='IN_PROGRESS'), 'new')

    def test_zero_capacity_is_failure(self):
        service = self.service()
        service.update(desiredCount=0, runningCount=0)
        with self.assertRaises(RuntimeError):
            assert_release(service, 'new')
