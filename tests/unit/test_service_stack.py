import aws_cdk as cdk
import aws_cdk.assertions as assertions

from src.network_stack import NetworkStack
from src.ecs_stack import EcsStack
from src.service_props import ServiceProps, ServiceSecret, ContainerVolume
from src.service_stack import ServiceStack


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
