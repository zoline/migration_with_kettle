import os, sys
import argparse,configparser 
import csv,re

import getpass
import oracledb

import jpype
import jpype.imports
from jpype import *

import jpype.types as jtypes

java_opts =['-Xms1024m', '-Xmx2048m','-DKETTLE_HOME=/home/icp/pentaho/data-integration', 
            '-DKETTLE_REPOSITORY=','-DKETTLE_USER=','-DKETTLE_PASSWORD=','-DKETTLE_PLUGIN_PACKAGES=','-DKETTLE_LOG_SIZE_LIMIT=','-DKETTLE_JNDI_ROOT=']

jpype.startJVM(jpype.getDefaultJVMPath(),convertStrings=True, *java_opts)

import java.io
import java.lang
from java.io import File 
from com.typesafe.config 		import Config,ConfigFactory
from org.pentaho.di.core      	   	import KettleEnvironment
from org.pentaho.di.core.exception 	import KettleException
from org.pentaho.di.core.util      	import EnvUtil
from org.pentaho.di.core 	   	import plugins, NotePadMeta
from org.pentaho.di.core.database  	import DatabaseMeta
from org.pentaho.di.trans 		import Trans,TransMeta,TransHopMeta
from org.pentaho.di.trans.step  	import StepMeta, StepMetaInterface
from org.pentaho.di.trans.steps.dummytrans import DummyTransMeta
from org.pentaho.di.trans.steps.tableinput  import TableInputMeta
from org.pentaho.di.trans.steps.tableoutput import TableOutputMeta

def get_database_config():
    from java.io import File
    f=File('./database.conf')
    database_config = ConfigFactory.parseFile(f).getConfig("databaseConfig")
    if database_config is not None:
       return database_config
    else:
       sys.exit(-1)

class Oracle_Source:
    def __init__(self,connect_string,username,password ):
        self.conn = None
        self.connect_string = connect_string
        self.username = username
        self.password = password

    def connect(self):
        """ Connect to oracle database swith username and password
            Oracle Connection info was saved in oracle.cfg """

        self.conn= oracledb.connect(user=self.username, password=self.password, dsn=self.connect_string)
        if self.conn is None:
            print("Cananot connect to Oracle") 
            sys.exit(-1)

    def get_cursor():
        return self.conn.cursor()

    def get_tables(self, filter=None):
       table_query="""
        SELECT OWNER, TABLE_NAME,STATUS
        FROM all_tables 
        WHERE %s
          -- AND tablespace_name is not NULL AND NUM_ROWS IS NOT NULL 
        ORDER BY  OWNER, TABLE_NAME
       """
       if filter is None:
           query = table_query % ( "1=1" )
       else:
           query = table_query % filter
       with self.conn.cursor() as cur:
           cur.execute(query)
           res = cur.fetchall()
           return res

    def get_columns(self,owner,table):
        column_query = """
         SELECT COLUMN_ID,COLUMN_NAME,DATA_TYPE	
          FROM ALL_TAB_COLS	 
         WHERE OWNER = '%s' AND TABLE_NAME = '%s'
           AND USER_GENERATED = 'YES' 
         ORDER BY COLUMN_ID
        """
        column_string = ""
        query = column_query % (owner.upper(), table.upper())
    
        with self.conn.cursor() as cur:
            cur.execute(query)
            res = cur.fetchall()
            source_columns= []
            for COLUMN_ID, COLUMN_NAME,	DATA_TYPE in res:  
                source_columns.append((COLUMN_NAME,DATA_TYPE))
            return source_columns

def build_copy_table(databases,owner,table_name,source_columns):
    trans_name = table_name +"_transformation" 
    source_db_info = None
    target_db_info = None

    trans_meta = TransMeta()
    trans_meta.setName(trans_name)

    (source_db_name, conn_source) = databases[0] 
    (target_db_name, conn_target) = databases[1] 

    source_database_meta = DatabaseMeta(conn_source)
    trans_meta.addDatabase(source_database_meta)
    target_database_meta = DatabaseMeta(conn_target)
    trans_meta.addDatabase(target_database_meta)

    source_db_info = trans_meta.findDatabase(source_db_name)
    target_db_info = trans_meta.findDatabase(target_db_name)

    note = "Reads information from table [%s] on  database [%s] After that, it writes information to table [%s] on database [%s]" %(table_name,source_db_info,table_name,target_db_info)
    note_info = NotePadMeta(note,150,10,-1,-1)
    trans_meta.addNote(note_info)

    from_step_name = "read from [%s]" % table_name
    column_string = ""

    field_array = []
    target_columns =[]

    for (col_name,col_type) in source_columns:
       column_string += "," if column_string != "" else " "
       field_array.append(col_name)
       target_columns.append(col_name)
       match col_type: 
            case 'CHAR':
                column_string += "decode(%s,'', NULL, %s) AS %s \n" %(col_name,col_name,col_name)  
            case 'VARCHAR'|'VARCHAR2'|'NVARCHAR2':
                column_string += "decode(%s,'', NULL, trim(%s)) AS %s \n" %(col_name,col_name,col_name)  
            case _:
                column_string += "%s \n" % (col_name) 
    select_statement = " SELECT \n %s FROM  %s.%s " % (column_string,owner,table_name) 

    table_inputmeta = TableInputMeta()
    table_inputmeta.setDatabaseMeta(source_db_info)
    table_inputmeta.setSQL(select_statement)

    from_step =StepMeta("TableInput",from_step_name,table_inputmeta)
    from_step.setLocation(150,100)
    from_step.setDraw(True)
    from_step.setDescription("Reads information from table [%s] on database [%s]" % (table_name, source_db_info))
    trans_meta.addStep(from_step);

    to_step_name = "write to [ %s ]" % (table_name)
    table_outputmeta =TableOutputMeta()
    
    table_outputmeta.setDatabaseMeta(target_db_info)
    table_outputmeta.setTablename(table_name)
    ##table_outputmeta.setSchemaName(target_schema_name)
    table_outputmeta.setSpecifyFields(True)
    table_outputmeta.setTruncateTable(True)

    table_outputmeta.setFieldStream(field_array)
    table_outputmeta.setFieldDatabase(target_columns)

    table_outputmeta.setCommitSize(1000)
    table_outputmeta.setTruncateTable(False)

    to_step =StepMeta("TableOutput",to_step_name,table_outputmeta)
    to_step.setLocation(500, 100)
    to_step.setDescription("Write information to table [ %s ] on database [ %s ]" % (table_name, target_db_info))
    to_step.setDraw(True)
    trans_meta.addStep(to_step);

    trans_hop = TransHopMeta(from_step, to_step)
    trans_hop.setEnabled(True)
    trans_meta.addTransHop(trans_hop)
    return trans_meta

def main(argv, args):
    """main"""
    database_config=get_database_config()
    root_directory   = database_config.getString("outputDir")
    connect_string   = database_config.getString("connection.CONNECT_STRING")
    connect_user     = database_config.getString("connection.ORACLE_USER")
    connect_password = database_config.getString("connection.ORACLE_PASSWORD")

    oracle = Oracle_Source(connect_string,connect_user,connect_password)
    oracle.connect()
    owner=args['u']

    #EnvUtil.environmentInit()
    KettleEnvironment.init();

    filter = "OWNER = '%s' " % owner.upper()
    databases=[(database_config.getString("Database.sourceDbName"),database_config.getString("Database.source")),
               (database_config.getString("Database.targetDbName"),database_config.getString("Database.target")) ]
    defSchemaName = database_config.getString("Database.sourceSchemaName")

    tables = oracle.get_tables(filter)
    for owner,table_name,status in tables:
        source_columns = oracle.get_columns(owner,table_name)
        table_trans_meta = build_copy_table(databases,defSchemaName,table_name,source_columns) 

        trans_xml = table_trans_meta.getXML()
        file_name ="%s/%s.ktr" %(root_directory,table_name)
        with open(file_name,'w') as dos:
            dos.write(trans_xml)   

if '--version' in sys.argv:
	print(__version__)
elif __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', help=' : Please set the user name')
    args = vars(parser.parse_args())
    argv = sys.argv
    main(argv,args)
