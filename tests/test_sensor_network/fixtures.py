import os
import signal
import subprocess
from datetime import datetime
from random import randint, random

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, ProgrammingError

from plenario.database import psql
from plenario.settings import DB_USER, DB_PASSWORD, DB_HOST, DB_NAME, DB_PORT


class Fixtures:

    def _run_with_connection(self, query):
        conn = self.engine.connect()
        try:
            print(query)
            conn.execute("commit")
            conn.execute(query)
        except ProgrammingError as err:
            print(str(err))
        finally:
            conn.close()

    def _create_foi_table(self, table_schema):
        """A postgres friendly version of the redshift method that shares
        the same name.

        :param table_schema: (dict) {"name": "<name>", "properties": [ ... ]}
        :returns: None"""

        print("create table {}".format(table_schema["name"]))

        create_table = ("CREATE TABLE {} ("
                        "\"node_id\" VARCHAR NOT NULL,"
                        "datetime TIMESTAMP WITHOUT TIME ZONE NOT NULL,"
                        "\"meta_id\" DOUBLE PRECISION NOT NULL,"
                        "\"sensor\" VARCHAR NOT NULL,"
                        "").format(table_schema["name"])

        for i, prop in enumerate(table_schema["properties"]):
            create_table += '"{}" {} '.format(prop['name'], prop['type'])
            create_table += "," if i != len(table_schema["properties"]) - 1 else ""
        create_table += ')'
        self.rs_engine.execute(create_table)

    def __init__(self):
        os.environ["DB_NAME"] = "plenario_test"
        os.environ["RS_NAME"] = "plenario_test"

        self.user = DB_USER
        self.host = DB_HOST
        self.port = DB_PORT
        self.password = DB_PASSWORD

        self.base_db_url = "postgresql://{}:{}@{}:{}".format(
            self.user, self.password, self.host, self.port
        )
        self.engine = create_engine(self.base_db_url)
        self.pg_engine = None
        self.rs_engine = None
        self.worker_process = None

    def setup_databases(self):
        self._run_with_connection("create database plenario_test")
        self.rs_engine = create_engine(self.base_db_url + "/plenario_test")
        self.pg_engine = create_engine(self.base_db_url + "/plenario_test")
        self.pg_engine.execute("create extension postgis")
        self.pg_engine.execute("create extension plv8")
        psql('plenario/dbscripts/sensor_tree.sql')

    def generate_sensor_network_meta_tables(self):
        print("create sensor network tables for {} ..." .format(self.pg_engine))
        postgres_base.metadata.create_all(bind=self.pg_engine)

    def drop_databases(self):
        self._run_with_connection("drop database plenario_test")

    def generate_mock_metadata(self):
        postgres_session.configure(bind=self.pg_engine)

        sensor_01 = SensorMeta(
            name="sensor_01",
            observed_properties={"howhot": "temperature.temperature"}
        )

        sensor_02 = SensorMeta(
            name="sensor_02",
            observed_properties={"vec_x": "vector.x", "vex_y": "vector.y"}
        )

        sensor_03 = SensorMeta(
            name="sensor_03",
            observed_properties={"temperature": "temperature.temperature"}
        )

        node = NodeMeta(
            id="test_node",
            address='Nichols Bridgeway, Chicago, IL 60601, USA',
            sensor_network="test_network",
            sensors=[sensor_01, sensor_02, sensor_03],
            location="0101000020E6100000A4A7C821E2E755C07C48F8DEDFF04440",
        )

        node_2 = NodeMeta(
            id="node_2",
            sensor_network="test_network",
            sensors=[sensor_01, sensor_02],
            location="0101000020E6100000A4A7C821E2E755C07C48F8DEDFF04440",
        )

        network = NetworkMeta(
            name="test_network",
            nodes=[node],
        )

        network_02 = NetworkMeta(
            name="test_network_other",
        )

        feature_01 = FeatureMeta(
            name="temperature",
            observed_properties=[{"type": "float", "name": "temperature"}],
            networks=[network]
        )

        feature_02 = FeatureMeta(
            name="vector",
            observed_properties=[{"type": "float", "name": "x"}, {"type": "float", "name": "y"}],
            networks=[network]
        )

        for obj in [feature_01, feature_02, network, network_02, node, node_2]:
            try:
                print("INSERT {} with {}".format(obj, postgres_session.get_bind()))
                postgres_session.add(obj)
                postgres_session.commit()
            except IntegrityError as err:
                print(str(err) + "\n")
                postgres_session.rollback()

    def generate_mock_observations(self):
        self._create_foi_table({"name": "test_network__vector", "properties": [{"name": "x", "type": "float"}, {"name": "y", "type": "float"}]})
        self._create_foi_table({"name": "test_network__temperature", "properties": [{"name": "temperature", "type": "float"}]})
        print("Populating records ", end=' ')

        date_string = "2016-10-{} {}:{}:{}"
        date_format = "%Y-%m-%d %H:%M:%S"
        day = 0

        for i in range(0, 300):
            if i % 100 == 0:
                day += 1
                print(".", end=' ')

            record_date = datetime.strptime(
                date_string.format(day, randint(0, 23), randint(0, 59), randint(0, 59)),
                date_format
            )

            self.rs_engine.execute("""
                insert into test_network__vector (node_id, datetime, meta_id, sensor, x, y)
                values ('test_node', '{}', '{}', 'sensor_02', {}, {})
                """.format(record_date, randint(0, 100), random(), random())
            )

            self.rs_engine.execute("""
                insert into test_network__temperature (node_id, datetime, meta_id, sensor, temperature)
                values ('test_node', '{}', '{}', 'sensor_03', {})
                """.format(record_date, randint(0, 100), random())
            )

            self.rs_engine.execute("""
                insert into test_network__temperature (node_id, datetime, meta_id, sensor, temperature)
                values ('test_node', '{}', '{}', 'sensor_01', {})
                """.format(record_date, randint(0, 100), random())
            )

            self.rs_engine.execute("""
                insert into test_network__temperature (node_id, datetime, meta_id, sensor, temperature)
                values ('node_2', '{}', '{}', 'sensor_01', {})
                """.format(record_date, randint(0, 100), random(), random())
            )

        print("\n")


from plenario.models.SensorNetwork import *
