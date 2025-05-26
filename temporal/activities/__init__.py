from .fe_generator import *
from .be_generator import *
from .xml_generator import *
from .db_writer import *
from .unit_test_generator import *

fe_activities = [
    generate_column_setting,
    generate_service,
    generate_menu,
    generate_configuration,
    generate_i18n,
]
be_activities = [
    generate_model,
    generate_controller,
    generate_route,
    generate_view,
]
xml_activities = [
    generate_xml,
]

db_writer_activities = [
    save_generated_xml,
]

unit_test_activities = [generate_unit_tests, collect_table_contexts]

# Flatten everything
all_activities = [*fe_activities, *be_activities, *xml_activities, *db_writer_activities, *unit_test_activities]
