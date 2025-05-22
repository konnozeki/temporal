import psycopg2


class ViewGenerator:
    def __init__(self, xml_dict):
        self.xml_dict = xml_dict
        self.db_name = "nagaco"
        self.db_user = "odoo"
        self.db_password = "odoo17@2023"
        self.db_host = "192.168.1.8"
        self.db_port = 5433
        self.model_name = self.xml_dict["root"]["model"]
        self.class_name = self.model_name.replace("_", " ").title().replace(" ", "_")
        self.object_name = self.model_name.replace("nagaco_", "")
        self.number_type = ["int", "smallint", "float", "double", "bool"]

    def create_view(self, records):
        fk_name = [(r[0].replace("nagaco_", ""), r[0], r[1]) for r in records]
        fields = "\n".join([f"""\t{fk}_{i}_count = fields.Integer(string='Count of {cl}', readonly=True)""" for (i, (fk, cl, fi)) in enumerate(fk_name)])
        coalesces = ",\n".join([f"""\t\t\t\t(select count(*) from {cl} where {cl}.{fi} = source.id) AS {fk}_{i}_count""" for (i, (fk, cl, fi)) in enumerate(fk_name)])
        str = f"""
class {self.class_name}_View(models.Model):
	_name = '{self.model_name}_view'
	_auto = False  # Không tạo bảng mới trong CSDL
	_description = 'Table {self.model_name} View'
	{self.object_name}_id = fields.Many2one('{self.model_name}', string='{self.object_name}', readonly=True)
{fields}

	def init(self):
		self.env.cr.execute(\"\"\"
			CREATE OR REPLACE VIEW {self.model_name}_view AS
			SELECT
				source.id AS {self.object_name}_id,
{coalesces}
			FROM
				{self.model_name} source
	\"\"\")
"""
        return str

    def create_view_empty(self, records):
        str = f"""
class {self.class_name}_View(models.Model):
	_name = '{self.model_name}_view'
	_auto = False  # Không tạo bảng mới trong CSDL
	_description = 'Table {self.model_name} View'
	{self.object_name}_id = fields.Many2one('{self.model_name}', string='{self.object_name}', readonly=True)

	def init(self):
		self.env.cr.execute(\"\"\"
			CREATE OR REPLACE VIEW {self.model_name}_view AS
			SELECT
				source.id AS {self.object_name}_id
			FROM
				{self.model_name} source
	\"\"\")
"""

        return str

    def generate_view(self):
        connection = psycopg2.connect(database=self.db_name, user=self.db_user, password=self.db_password, host=self.db_host, port=self.db_port)
        cursor = connection.cursor()
        sql_context = f"""
SELECT
    DISTINCT r.table_name as table_name, r.column_name as column_name
FROM information_schema.constraint_column_usage       u
INNER JOIN information_schema.referential_constraints fk
           ON u.constraint_catalog = fk.unique_constraint_catalog
               AND u.constraint_schema = fk.unique_constraint_schema
               AND u.constraint_name = fk.unique_constraint_name
INNER JOIN information_schema.key_column_usage        r
           ON r.constraint_catalog = fk.constraint_catalog
               AND r.constraint_schema = fk.constraint_schema
               AND r.constraint_name = fk.constraint_name
WHERE
    u.column_name = 'id' AND
    u.table_catalog = 'nagaco' AND
    u.table_schema = 'public' AND
    u.table_name = '{self.model_name}';
        """

        cursor.execute(sql_context)
        records = cursor.fetchall()
        return_str = ""
        if len(records) > 0:
            return_str = f"""
from enum import Enum
from odoo import models, fields

{self.create_view(records)}
"""
        else:
            return_str = f"""
from enum import Enum
from odoo import models, fields

{self.create_view_empty(records)}
"""
        return return_str
