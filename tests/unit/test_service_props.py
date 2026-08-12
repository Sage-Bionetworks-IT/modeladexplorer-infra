from src.service_props import ServiceProps


def test_service_props_flags_path_location():
    props = ServiceProps(
        container_name="app",
        container_location="path://docker/app",
        container_port=8010,
    )

    assert props.container_location == "docker/app"
    assert props.container_location_is_path is True


def test_service_props_registry_location_is_not_a_path():
    props = ServiceProps(
        container_name="app",
        container_location="ghcr.io/sage-bionetworks/app:1.0",
        container_port=8010,
    )

    assert props.container_location == "ghcr.io/sage-bionetworks/app:1.0"
    assert props.container_location_is_path is False
