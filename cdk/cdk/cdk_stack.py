
"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0
Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
from typing_extensions import runtime
from async_timeout import timeout
from aws_cdk.aws_events import Rule, Schedule
from aws_cdk.aws_iam import Role
from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as _lambda,
    aws_iam as iam,
    triggers as triggers,
    aws_events_targets as targets,
    aws_logs as logs
)
import aws_cdk
import aws_cdk.aws_sso as sso
from constructs import Construct


class DailyConfigReporter(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        aggregator = aws_cdk.CfnParameter(
            self,
            "aggregator",
            type="String",
            default='aggregator',
            description="Name of AWS Config Aggregator"
        )

        BUCKETNAME = aws_cdk.CfnParameter(
            self,
            "BUCKETNAME",
            type="String",
            default='BUCKETNAME',
            description="Bucket name for storage"
        )
        HOUR = aws_cdk.CfnParameter(
            self,
            "HOUR",
            type="String",
            default='23',
            description="The time (hour) the Lambda will run. For example: for 23:50 UTC, type 23"
        )
        MINUTE = aws_cdk.CfnParameter(
            self,
            "MINUTE",
            type="String",
            default='50',
            description="The time (minute) the Lambda will run. For example: for 23:50 UTC, type 50"
        )
        config_reporter_lambda = _lambda.Function(self, "config_reporter",
                                                        log_retention=logs.RetentionDays.ONE_MONTH,
                                                        code=_lambda.Code.from_asset(
                                                            "../src/"),
                                                        runtime=_lambda.Runtime.PYTHON_3_8,
                                                        handler="config_reporter.config_reporter",
                                                        timeout=Duration.seconds(
                                                            60),
                                                        environment={
                                                            "AGGREGATOR_NAME": aggregator.value_as_string,
                                                            "BUCKET_NAME": BUCKETNAME.value_as_string})
        config_reporter_lambda.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:*"
            ],
            resources=[f'arn:aws:s3:::{BUCKETNAME.value_as_string}',
                       f'arn:aws:s3:::{BUCKETNAME.value_as_string}/*']))
        
        config_reporter_lambda.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "config:DescribeAggregationAuthorizations",
				"config:DescribeConfigRules",
				"config:DescribeConfigurationAggregators",
				"config:DescribeConfigurationRecorders",
				"config:DescribeConformancePacks",
				"config:DescribeDeliveryChannels",
				"config:DescribeOrganizationConfigRules",
				"config:DescribeOrganizationConformancePacks",
				"config:DescribePendingAggregationRequests",
				"config:DescribeRemediationConfigurations",
				"config:DescribeRemediationExceptions",
				"config:DescribeRetentionConfigurations",
				"config:ListAggregateDiscoveredResources",
				"config:ListConformancePackComplianceScores",
				"config:ListDiscoveredResources",
				"config:ListResourceEvaluations",
				"config:ListStoredQueries",
				"config:BatchGetAggregateResourceConfig",
				"config:BatchGetResourceConfig",
				"config:DeliverConfigSnapshot",
				"config:DescribeAggregateComplianceByConfigRules",
				"config:DescribeAggregateComplianceByConformancePacks",
				"config:DescribeComplianceByResource",
				"config:DescribeComplianceByConfigRule",
				"config:DescribeConfigRuleEvaluationStatus",
				"config:DescribeConfigurationAggregatorSourcesStatus",
				"config:DescribeConfigurationRecorderStatus",
				"config:DescribeConformancePackCompliance",
				"config:DescribeConformancePackStatus",
				"config:DescribeDeliveryChannelStatus",
				"config:DescribeOrganizationConfigRuleStatuses",
				"config:DescribeOrganizationConformancePackStatuses",
				"config:DescribeRemediationExecutionStatus",
				"config:GetAggregateComplianceDetailsByConfigRule",
				"config:GetAggregateConfigRuleComplianceSummary",
				"config:GetAggregateConformancePackComplianceSummary",
				"config:GetAggregateDiscoveredResourceCounts",
				"config:GetAggregateResourceConfig",
				"config:GetComplianceDetailsByConfigRule",
				"config:GetComplianceDetailsByResource",
				"config:GetComplianceSummaryByConfigRule",
				"config:GetComplianceSummaryByResourceType",
				"config:GetConformancePackComplianceDetails",
				"config:GetConformancePackComplianceSummary",
				"config:GetCustomRulePolicy",
				"config:GetDiscoveredResourceCounts",
				"config:GetOrganizationConfigRuleDetailedStatus",
				"config:GetOrganizationConformancePackDetailedStatus",
				"config:GetOrganizationCustomRulePolicy",
				"config:GetResourceConfigHistory",
				"config:GetResourceEvaluationSummary",
				"config:GetStoredQuery",
				"config:ListTagsForResource",
				"config:SelectAggregateResourceConfig",
				"config:SelectResourceConfig"
            ],
            resources=[
                '*'
            ],
            conditions={
                "StringEquals": {
                    "aws:ResourceAccount": [aws_cdk.Aws.ACCOUNT_ID
                                            ]
                }
            }
        ))
        
        rule = Rule(self, "ConfigDailyReporterCW",
                    schedule=Schedule.cron(
                        minute=MINUTE.value_as_string, hour=HOUR.value_as_string)
                    )
        rule.add_target(targets.LambdaFunction(config_reporter_lambda))
        trigger = triggers.Trigger(
            self, "TriggerLambda", handler=config_reporter_lambda)
