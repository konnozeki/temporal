from temporalio import activity
from scripts.frontend.fields_generator import FieldsGenerator
from scripts.frontend.i18n_generator import I18nGenerator
from scripts.frontend.service_generator import ServiceGenerator
from scripts.frontend.navigation_generator import NavigationGenerator
from scripts.frontend.configuration_generator import ConfigurationGenerator


# Các hoạt động cho FE
@activity.defn
async def generate_service(model_name, xml_dict, prefix):
    # Sinh các services
    return ServiceGenerator(prefix).generate(model_name, xml_dict)


@activity.defn
async def generate_i18n(xml_dict):
    # Sinh đa ngôn ngữ
    return I18nGenerator(xml_dict).generate()


@activity.defn
async def generate_column_setting(xml_dict):
    # Sinh cấu hình của các cột
    return FieldsGenerator(xml_dict).generate()


@activity.defn
async def generate_menu(xml_dict, module_name="categories"):
    # Sinh menu
    return NavigationGenerator(xml_dict, module_name).generate()


@activity.defn
async def generate_configuration(xml_dict, module_name="categories"):
    # Sinh config
    return ConfigurationGenerator(xml_dict).generate()
