from temporalio import activity
from scripts.backend.controller_generator import ControllerGenerator
from scripts.backend.model_generator import ModelGenerator
from scripts.backend.route_generator import RouteGenerator
from scripts.backend.view_generator import ViewGenerator


# Các hoạt động cho BE
@activity.defn
async def generate_controller(xml_dict):
    # Sinh các controller
    return ControllerGenerator(xml_dict).generate_controller()


@activity.defn
async def generate_route(xml_dict):
    # Sinh các route
    return RouteGenerator(xml_dict).generate_route()


@activity.defn
async def generate_model(xml_dict):
    # Sinh các model
    return ModelGenerator(xml_dict).generate_model()


@activity.defn
async def generate_view(xml_dict):
    # Sinh các view
    return ViewGenerator(xml_dict).generate_view()
