import aws_cdk as cdk
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_logs as logs
from constructs import Construct

ECS_EVENT_DETAIL_TYPES = ["ECS Task State Change", "ECS Deployment State Change"]


def add_cache_clear_query(
    scope: Construct, name_prefix: str, log_group: logs.ILogGroup
) -> logs.QueryDefinition:
    """
    Saves a Logs Insights query for an API service's data release cache clears.

    Add it to the API service's own stack, so the query is removed along with the service
    and no other stack depends on the service's log group.
    """
    return logs.QueryDefinition(
        scope,
        "DataReleaseCacheClearsQuery",
        query_definition_name=f"{name_prefix}/Data release cache clears",
        log_groups=[log_group],
        query_string=logs.QueryString(
            fields=["@timestamp", "@logStream as task", "@message"],
            # matches the api-cache-invalidation library's startup line ("Initial data
            # version observed" / "Initial data release observed") and its cache clears
            # ("...; clearing caches", and "clearing caches again" from MG-1028)
            filter_statements=["@message like /Initial data|clearing caches/"],
            sort="@timestamp asc",
        ),
    )


class MonitoringStack(cdk.Stack):
    """
    Keeps the history of deploys:
      - sends the cluster's ECS task and deployment events to a CloudWatch Logs group
      - saves Logs Insights queries for deploy timelines, deployments and rollbacks
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        name_prefix: str,
        cluster: ecs.ICluster,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.ecs_events_log_group = logs.LogGroup(
            self,
            "EcsEventsLogGroup",
            log_group_name=f"/aws/events/{name_prefix}/ecs",
            retention=logs.RetentionDays.FOUR_MONTHS,
        )

        # Task events name the task ARN and deployment events name the service ARN
        # in `resources`; both ARNs contain the cluster name.
        arn_prefix = f"arn:{self.partition}:ecs:{self.region}:{self.account}"
        self.ecs_events_rule = events.Rule(
            self,
            "EcsEventsRule",
            description=f"Send {name_prefix} ECS task and deployment events to CloudWatch Logs",
            event_pattern=events.EventPattern(
                source=["aws.ecs"],
                detail_type=ECS_EVENT_DETAIL_TYPES,
                resources=events.Match.any_of(
                    events.Match.prefix(f"{arn_prefix}:task/{cluster.cluster_name}/"),
                    events.Match.prefix(
                        f"{arn_prefix}:service/{cluster.cluster_name}/"
                    ),
                ),
            ),
            targets=[targets.CloudWatchLogGroup(self.ecs_events_log_group)],
        )

        # Saved queries, grouped in a folder per environment in the Logs Insights console
        #
        # Task events don't include the task's health status. A Service Connect task (app,
        # api, api-next: no container health checks) starts taking traffic when it reaches
        # RUNNING, and stops once ECS sets its desired status to STOPPED and drains it.
        logs.QueryDefinition(
            self,
            "DeployTimelineQuery",
            query_definition_name=f"{name_prefix}/Deploy timeline",
            log_groups=[self.ecs_events_log_group],
            query_string=logs.QueryString(
                fields=[
                    "@timestamp",
                    "detail.group as service",
                    "detail.taskDefinitionArn as taskDefinition",
                    "detail.lastStatus as lastStatus",
                    "detail.desiredStatus as desiredStatus",
                    "detail.stoppedReason as stoppedReason",
                    "detail.taskArn as task",
                ],
                filter_statements=['`detail-type` = "ECS Task State Change"'],
                sort="@timestamp asc",
            ),
        )
        logs.QueryDefinition(
            self,
            "DeploymentsQuery",
            query_definition_name=f"{name_prefix}/Deployments and rollbacks",
            log_groups=[self.ecs_events_log_group],
            query_string=logs.QueryString(
                fields=[
                    "@timestamp",
                    "resources.0 as service",
                    "detail.eventName as event",
                    "detail.deploymentId as deployment",
                    "detail.reason as reason",
                ],
                filter_statements=['`detail-type` = "ECS Deployment State Change"'],
                sort="@timestamp asc",
            ),
        )
