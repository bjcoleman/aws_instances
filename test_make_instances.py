

from moto import mock_ec2

from create_instances import create_ec2_instances


"""
I created this test to facilitate refactoring.
The test captures the output of create_ec2_instances() and compares it to
the expected output.
"""

@mock_ec2
def test_create_instances(capsys):
    create_ec2_instances('devops', 'names.txt')

    captured = capsys.readouterr().out.splitlines()

    assert len(captured) == 19

    assert 'Fetching the most recent Amazon Linux 2 AMI ID...' in captured.pop(0)
    assert 'Using AMI ID:' in captured.pop(0)
    assert 'Security group created with ID:' in captured.pop(0)
    assert 'Creating EC2 instance for \'coleman\'...' in captured.pop(0)
    assert 'Instance \'coleman\' created with ID' in captured.pop(0)
    assert 'Creating EC2 instance for \'caine\'...' in captured.pop(0)
    assert 'Instance \'caine\' created with ID:' in captured.pop(0)
    assert 'Creating EC2 instance for \'lansing\'...' in captured.pop(0)
    assert 'Instance \'lansing\' created with ID:' in captured.pop(0)
    assert 'Creating EC2 instance for \'freedman\'...' in captured.pop(0)
    assert 'Instance \'freedman\' created with ID:' in captured.pop(0)
    assert 'Waiting for instances to be running...' in captured.pop(0)
    assert 'Instances are running.' in captured.pop(0)
    # ignore blank line
    captured.pop(0)
    assert 'Student names and corresponding public IPv4 addresses:' in captured.pop(0)
    assert 'coleman:' in captured.pop(0)
    assert 'caine:' in captured.pop(0)
    assert 'lansing:' in captured.pop(0)
    assert 'freedman:' in captured.pop(0)