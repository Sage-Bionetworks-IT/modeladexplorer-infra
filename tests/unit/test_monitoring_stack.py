import aws_cdk as cdk
import aws_cdk.assertions as assertions

from src.ecs_stack import EcsStack
from src.monitoring_stack import MonitoringStack, add_cache_clear_query
from src.network_stack import NetworkStack
from src.service_props import ServiceProps
from src.service_stack import ServiceStack


def _make_stacks():
    app = cdk.App()
    network_stack = NetworkStack(app, "NetworkStack", vpc_cidr="10.254.192.0/24")
    ecs_stack = EcsStack(app, "EcsStack", vpc=network_stack.vpc, namespace="dev.app.io")
    api_next_stack = ServiceStack(
        scope=app,
        construct_id="ApiNextStack",
        vpc=network_stack.vpc,
        cluster=ecs_stack.cluster,
        props=ServiceProps(
            container_name="api-next",
            container_location="ghcr.io/sage-bionetworks/api-next:1.0",
            container_port=3334,
        ),
    )
    add_cache_clear_query(api_next_stack, "app-dev", api_next_stack.log_group)
    monitoring_stack = MonitoringStack(
        scope=app,
        construct_id="MonitoringStack",
        name_prefix="app-dev",
        cluster=ecs_stack.cluster,
    )
    return monitoring_stack, api_next_stack


def _make_template():
    monitoring_stack, _ = _make_stacks()
    return assertions.Template.from_stack(monitoring_stack)


def test_ecs_events_log_group_created():
    template = _make_template()
    template.has_resource_properties(
        "AWS::Logs::LogGroup",
        {"LogGroupName": "/aws/events/app-dev/ecs", "RetentionInDays": 120},
    )


def test_ecs_events_rule_targets_log_group():
    template = _make_template()
    template.has_resource_properties(
        "AWS::Events::Rule",
        {
            "EventPattern": {
                "source": ["aws.ecs"],
                "detail-type": [
                    "ECS Task State Change",
                    "ECS Deployment State Change",
                ],
                "resources": assertions.Match.array_with(
                    [
                        {"prefix": assertions.Match.any_value()},
                        {"prefix": assertions.Match.any_value()},
                    ]
                ),
            },
            "State": "ENABLED",
            "Targets": [
                assertions.Match.object_like(
                    {"Arn": assertions.Match.any_value(), "Id": "Target0"}
                )
            ],
        },
    )


def test_saved_queries_created():
    template = _make_template()
    template.resource_count_is("AWS::Logs::QueryDefinition", 2)
    for name in [
        "app-dev/Deploy timeline",
        "app-dev/Deployments and rollbacks",
    ]:
        template.has_resource_properties("AWS::Logs::QueryDefinition", {"Name": name})
    template.has_resource_properties(
        "AWS::Logs::QueryDefinition",
        {
            "Name": "app-dev/Deploy timeline",
            "QueryString": assertions.Match.string_like_regexp(
                'filter `detail-type` = "ECS Task State Change"'
            ),
        },
    )


def test_cache_clear_query_in_api_stack():
    monitoring_stack, api_next_stack = _make_stacks()
    template = assertions.Template.from_stack(api_next_stack)
    template.has_resource_properties(
        "AWS::Logs::QueryDefinition",
        {
            "Name": "app-dev/Data release cache clears",
            "LogGroupNames": [{"Ref": assertions.Match.string_like_regexp("LogGroup")}],
            "QueryString": assertions.Match.string_like_regexp(
                "filter @message like /Initial data\\|clearing caches/"
            ),
        },
    )
    # the query lives with api-next, so no stack imports api-next's log group
    assert "Outputs" not in template.to_json()
    assert "ApiNextStack" not in str(
        assertions.Template.from_stack(monitoring_stack).to_json()
    )
