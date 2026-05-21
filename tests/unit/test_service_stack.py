import pytest
import aws_cdk as cdk
import aws_cdk.assertions as assertions

from src.network_stack import NetworkStack
from src.ecs_stack import EcsStack
from src.load_balancer_stack import LoadBalancerStack
from src.service_props import ServiceProps, ServiceSecret, ContainerVolume
from src.service_stack import LoadBalancedServiceStack, ServiceStack

FAKE_CERT_ID = "00000000-0000-0000-0000-000000000000"


def _make_load_balanced_stack(redirect_from=None, redirect_to=None):
    app = cdk.App()
    network_stack = NetworkStack(app, "NetworkStack", vpc_cidr="10.254.192.0/24")
    ecs_stack = EcsStack(app, "EcsStack", vpc=network_stack.vpc, namespace="dev.app.io")
    lb_stack = LoadBalancerStack(app, "LbStack", vpc=network_stack.vpc)
    props = ServiceProps(
        container_name="apex",
        container_location="ghcr.io/sage-bionetworks/apex:1.0",
        container_port=80,
        container_memory_reservation=200,
    )
    return LoadBalancedServiceStack(
        scope=app,
        construct_id="ApexStack",
        vpc=network_stack.vpc,
        cluster=ecs_stack.cluster,
        props=props,
        load_balancer=lb_stack.alb,
        certificate_id=FAKE_CERT_ID,
        redirect_from_hostname=redirect_from,
        redirect_to_hostname=redirect_to,
    )


def test_service_stack_created():
    cdk_app = cdk.App()
    vpc_cidr = "10.254.192.0/24"
    network_stack = NetworkStack(cdk_app, "NetworkStack", vpc_cidr=vpc_cidr)
    ecs_stack = EcsStack(
        cdk_app, "EcsStack", vpc=network_stack.vpc, namespace="dev.app.io"
    )

    app_props = ServiceProps(
        container_name="app",
        container_location="ghcr.io/sage-bionetworks/app:1.0",
        container_port=8010,
        container_memory_reservation=200,
        container_secrets=[
            ServiceSecret(
                secret_name="/app/secret",
                environment_key="APP_SECRET",
            )
        ],
        container_volumes=[ContainerVolume(path="/work")],
        container_command=["test"],
        container_healthcheck=cdk.aws_ecs.HealthCheck(command=["CMD", "/healthcheck"]),
    )
    app_stack = ServiceStack(
        scope=cdk_app,
        construct_id="app",
        vpc=network_stack.vpc,
        cluster=ecs_stack.cluster,
        props=app_props,
    )

    template = assertions.Template.from_stack(app_stack)
    template.has_resource_properties(
        "AWS::ECS::TaskDefinition",
        {
            "ContainerDefinitions": [
                {
                    "Image": "ghcr.io/sage-bionetworks/app:1.0",
                    "MemoryReservation": 200,
                    "MountPoints": [{"ContainerPath": "/work"}],
                    "Secrets": [{"Name": "APP_SECRET"}],
                    "Command": ["test"],
                    "HealthCheck": {"Command": ["CMD", "/healthcheck"]},
                }
            ]
        },
    )


def test_load_balanced_service_stack_raises_when_only_redirect_from_set():
    with pytest.raises(ValueError):
        _make_load_balanced_stack(redirect_from="prod.modeladexplorer.org")


def test_load_balanced_service_stack_raises_when_only_redirect_to_set():
    with pytest.raises(ValueError):
        _make_load_balanced_stack(redirect_to="modeladexplorer.org")


def test_load_balanced_service_stack_no_redirect_rule_by_default():
    stack = _make_load_balanced_stack()
    template = assertions.Template.from_stack(stack)
    template.resource_count_is("AWS::ElasticLoadBalancingV2::ListenerRule", 0)


def test_load_balanced_service_stack_redirect_rule_created():
    stack = _make_load_balanced_stack(
        redirect_from="prod.modeladexplorer.org",
        redirect_to="modeladexplorer.org",
    )
    template = assertions.Template.from_stack(stack)
    template.has_resource_properties(
        "AWS::ElasticLoadBalancingV2::ListenerRule",
        {
            "Priority": 1,
            "Conditions": [
                {
                    "Field": "host-header",
                    "HostHeaderConfig": {"Values": ["prod.modeladexplorer.org"]},
                }
            ],
            "Actions": [
                {
                    "Type": "redirect",
                    "RedirectConfig": {
                        "Host": "modeladexplorer.org",
                        "Port": "443",
                        "Protocol": "HTTPS",
                        "StatusCode": "HTTP_301",
                    },
                }
            ],
        },
    )
