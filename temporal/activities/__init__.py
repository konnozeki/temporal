from .fe_generator import *
from .be_generator import *

fe_activities = [
    generate_column_setting,
    generate_service,
    generate_menu,
    generate_configuration,
    generate_i18n,
]
be_activities = [generate_model, generate_controller, generate_route, generate_view]

# Flatten everything
all_activities = [*fe_activities, *be_activities]
