"""Tests for SNS alert handler."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from cloud_optimizer.alerting.client import Alert, AlertResponse
from cloud_optimizer.alerting.config import AlertConfig, AlertPlatform, AlertSeverity
from cloud_optimizer.alerting.sns_handler import (
    CloudWatchAlarmMessage,
    SNSAlertHandler,
    parse_cloudwatch_alarm,
    _determine_severity,
)


class TestParseCloudWatchAlarm:
    """Tests for parse_cloudwatch_alarm function."""

    def test_parse_basic_alarm(self) -> None:
        """Test parsing a basic CloudWatch alarm message."""
        message = {
            "AlarmName": "test-alarm",
            "AlarmDescription": "Test description",
            "AWSAccountId": "123456789012",
            "Region": "us-east-1",
            "NewStateValue": "ALARM",
            "OldStateValue": "OK",
            "NewStateReason": "Threshold exceeded",
        }
        result = parse_cloudwatch_alarm(message)

        assert result.alarm_name == "test-alarm"
        assert result.alarm_description == "Test description"
        assert result.aws_account_id == "123456789012"
        assert result.region == "us-east-1"
        assert result.new_state == "ALARM"
        assert result.old_state == "OK"
        assert result.new_state_reason == "Threshold exceeded"

    def test_parse_json_string(self) -> None:
        """Test parsing JSON string input."""
        message = json.dumps({
            "AlarmName": "test-alarm",
            "NewStateValue": "ALARM",
        })
        result = parse_cloudwatch_alarm(message)
        assert result.alarm_name == "test-alarm"

    def test_parse_nested_sns_message(self) -> None:
        """Test parsing nested SNS Message field."""
        sns_envelope = {
            "Message": json.dumps({
                "AlarmName": "nested-alarm",
                "NewStateValue": "ALARM",
            }),
        }
        result = parse_cloudwatch_alarm(sns_envelope)
        assert result.alarm_name == "nested-alarm"

    def test_parse_with_trigger(self) -> None:
        """Test parsing alarm with Trigger details."""
        message = {
            "AlarmName": "cpu-alarm",
            "NewStateValue": "ALARM",
            "Trigger": {
                "MetricName": "CPUUtilization",
                "Namespace": "AWS/EC2",
                "Threshold": 80.0,
                "ComparisonOperator": "GreaterThanThreshold",
                "EvaluationPeriods": 3,
                "Period": 300,
                "Statistic": "Average",
                "Dimensions": [
                    {"name": "InstanceId", "value": "i-1234567890abcdef0"},
                ],
            },
        }
        result = parse_cloudwatch_alarm(message)

        assert result.metric_name == "CPUUtilization"
        assert result.namespace == "AWS/EC2"
        assert result.threshold == 80.0
        assert result.comparison_operator == "GreaterThanThreshold"
        assert result.evaluation_periods == 3
        assert result.period == 300
        assert result.statistic == "Average"
        assert result.dimensions == {"InstanceId": "i-1234567890abcdef0"}

    def test_parse_with_state_change_time(self) -> None:
        """Test parsing alarm with StateChangeTime."""
        message = {
            "AlarmName": "test-alarm",
            "NewStateValue": "ALARM",
            "StateChangeTime": "2025-12-04T16:00:00.000Z",
        }
        result = parse_cloudwatch_alarm(message)
        assert result.state_change_time is not None
        assert result.state_change_time.year == 2025
        assert result.state_change_time.month == 12
        assert result.state_change_time.day == 4

    def test_parse_invalid_json(self) -> None:
        """Test parsing invalid JSON raises error."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_cloudwatch_alarm("not valid json")


class TestDetermineSeverity:
    """Tests for _determine_severity function."""

    def test_critical_from_name(self) -> None:
        """Test detecting critical severity from alarm name."""
        alarm = CloudWatchAlarmMessage(alarm_name="prod-critical-cpu-alarm")
        assert _determine_severity(alarm) == AlertSeverity.CRITICAL

    def test_critical_from_p1(self) -> None:
        """Test detecting critical from P1 in name."""
        alarm = CloudWatchAlarmMessage(alarm_name="alarm-p1-database")
        assert _determine_severity(alarm) == AlertSeverity.CRITICAL

    def test_high_from_error(self) -> None:
        """Test detecting high severity from error in name."""
        alarm = CloudWatchAlarmMessage(alarm_name="error-rate-alarm")
        assert _determine_severity(alarm) == AlertSeverity.HIGH

    def test_high_from_p2(self) -> None:
        """Test detecting high from P2 in name."""
        alarm = CloudWatchAlarmMessage(alarm_name="alarm-p2-api")
        assert _determine_severity(alarm) == AlertSeverity.HIGH

    def test_medium_from_warning(self) -> None:
        """Test detecting medium severity from warning in name."""
        alarm = CloudWatchAlarmMessage(alarm_name="warning-latency-alarm")
        assert _determine_severity(alarm) == AlertSeverity.MEDIUM

    def test_low_from_info(self) -> None:
        """Test detecting low severity from info in name."""
        alarm = CloudWatchAlarmMessage(alarm_name="info-request-count")
        assert _determine_severity(alarm) == AlertSeverity.LOW

    def test_default_medium(self) -> None:
        """Test default severity is medium."""
        alarm = CloudWatchAlarmMessage(alarm_name="some-alarm")
        assert _determine_severity(alarm) == AlertSeverity.MEDIUM


class TestSNSAlertHandler:
    """Tests for SNSAlertHandler class."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create mock alert client."""
        client = MagicMock()
        client.create_alert = AsyncMock(return_value=AlertResponse(
            success=True,
            alert_id="test-id",
            dedup_key="test-dedup",
        ))
        client.resolve_alert = AsyncMock(return_value=AlertResponse(
            success=True,
            status="resolved",
        ))
        return client

    @pytest.fixture
    def handler(self, mock_client: MagicMock) -> SNSAlertHandler:
        """Create handler with mock client."""
        return SNSAlertHandler(
            client=mock_client,
            environment="test",
            auto_resolve=True,
        )

    @pytest.mark.asyncio
    async def test_handle_alarm_state(self, handler: SNSAlertHandler) -> None:
        """Test handling ALARM state creates alert."""
        message = {
            "AlarmName": "test-alarm",
            "NewStateValue": "ALARM",
            "OldStateValue": "OK",
            "NewStateReason": "Threshold exceeded",
            "AWSAccountId": "123456789012",
            "Region": "us-east-1",
        }

        response = await handler.handle_message(message)

        assert response.success
        handler.client.create_alert.assert_called_once()
        call_args = handler.client.create_alert.call_args[0][0]
        assert isinstance(call_args, Alert)
        assert "test-alarm" in call_args.title

    @pytest.mark.asyncio
    async def test_handle_ok_state_auto_resolve(self, handler: SNSAlertHandler) -> None:
        """Test handling OK state resolves alert when auto_resolve enabled."""
        message = {
            "AlarmName": "test-alarm",
            "NewStateValue": "OK",
            "OldStateValue": "ALARM",
            "NewStateReason": "Threshold crossed",
            "AWSAccountId": "123456789012",
            "Region": "us-east-1",
        }

        response = await handler.handle_message(message)

        assert response.success
        handler.client.resolve_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_ok_state_no_auto_resolve(self, mock_client: MagicMock) -> None:
        """Test OK state does not resolve when auto_resolve disabled."""
        handler = SNSAlertHandler(
            client=mock_client,
            environment="test",
            auto_resolve=False,
        )
        message = {
            "AlarmName": "test-alarm",
            "NewStateValue": "OK",
            "OldStateValue": "ALARM",
            "NewStateReason": "Threshold crossed",
        }

        response = await handler.handle_message(message)

        mock_client.resolve_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_insufficient_data(self, handler: SNSAlertHandler) -> None:
        """Test handling INSUFFICIENT_DATA state."""
        message = {
            "AlarmName": "test-alarm",
            "NewStateValue": "INSUFFICIENT_DATA",
            "OldStateValue": "OK",
            "NewStateReason": "Missing data",
        }

        response = await handler.handle_message(message)

        assert response.success
        assert "Insufficient data" in response.message
        handler.client.create_alert.assert_not_called()
        handler.client.resolve_alert.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_sns_notification(self, handler: SNSAlertHandler) -> None:
        """Test handling full SNS notification envelope."""
        sns_message = {
            "Type": "Notification",
            "Message": json.dumps({
                "AlarmName": "test-alarm",
                "NewStateValue": "ALARM",
                "OldStateValue": "OK",
                "NewStateReason": "Test",
                "AWSAccountId": "123456789012",
                "Region": "us-east-1",
            }),
        }

        response = await handler.handle_sns_notification(sns_message)

        assert response.success
        handler.client.create_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_subscription_confirmation(self, handler: SNSAlertHandler) -> None:
        """Test handling SNS subscription confirmation."""
        sns_message = {
            "Type": "SubscriptionConfirmation",
            "TopicArn": "arn:aws:sns:us-east-1:123456789012:test",
            "SubscribeURL": "https://example.com/confirm",
        }

        response = await handler.handle_sns_notification(sns_message)

        assert response.success
        assert "Subscription confirmation" in response.message

    @pytest.mark.asyncio
    async def test_dedup_key_generation(self, handler: SNSAlertHandler) -> None:
        """Test deduplication key is generated correctly."""
        alarm = CloudWatchAlarmMessage(
            alarm_name="test-alarm",
            aws_account_id="123456789012",
            region="us-east-1",
        )

        dedup_key = handler._create_dedup_key(alarm)

        assert dedup_key == "123456789012:us-east-1:test-alarm"

    def test_alarm_to_alert_conversion(self, handler: SNSAlertHandler) -> None:
        """Test CloudWatch alarm to Alert conversion."""
        alarm = CloudWatchAlarmMessage(
            alarm_name="critical-cpu-alarm",
            alarm_description="CPU too high",
            aws_account_id="123456789012",
            region="us-east-1",
            new_state="ALARM",
            new_state_reason="Threshold exceeded",
            namespace="AWS/EC2",
            metric_name="CPUUtilization",
            threshold=80.0,
            comparison_operator="GreaterThanThreshold",
            dimensions={"InstanceId": "i-1234"},
        )

        alert = handler._alarm_to_alert(alarm)

        assert "critical-cpu-alarm" in alert.title
        assert "ALARM" in alert.title
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.source == "cloudwatch"
        assert "aws_account_id" in alert.custom_details
        # Tags have prefix format like "region:us-east-1"
        assert "region:us-east-1" in alert.tags
