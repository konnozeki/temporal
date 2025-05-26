from temporalio import activity
from scripts.unit_test.unit_test_generator import UnitTestGenerator


@activity.defn
async def collect_table_contexts(table_names):
    """
    Collect context for the specified tables from the database.
    """
    from scripts.unit_test.db_context.database_context import DatabaseContext

    db_context = DatabaseContext()
    await db_context.connect()
    try:
        return await db_context.get_table_id_contexts(table_names)
    finally:
        await db_context.close()


@activity.defn
async def generate_unit_tests(xml_context, db_context):
    """
    Generate unit tests based on XML context and database context.
    """
    generator = UnitTestGenerator(xml_context, db_context)
    return generator.generate()
