import time
import traceback

from peewee import *

import hoshino

try:
	from hoshino.config.__bot__ import (MySQL_host, MySQL_password, MySQL_port,
	                                    MySQL_username)
	from hoshino.config.qa import MySQL_database, enable_index
except ImportError:
	from hoshino.config.qa import (MySQL_host, MySQL_password, MySQL_port,
	                               MySQL_username, MySQL_database, enable_index)

database = MySQLDatabase(
	host=MySQL_host,
	port=MySQL_port,
	user=MySQL_username,
	password=MySQL_password,
	database=MySQL_database,
	charset='utf8mb4',
	autocommit=True
)


class Question(Model):
	"""
	contains:
	answer
	create_time
	creator_id
	group_id
	id
	is_all
	question
	"""
	id = IntegerField(unique=True)
	question = CharField(max_length=100)
	answer = CharField(max_length=665)
	is_all = BooleanField(default=False)
	creator_id = BigIntegerField()
	group_id = BigIntegerField()
	create_time = TimestampField(default=time.time())
	
	class Meta:
		table_name = 'question'
		primary_key = CompositeKey('answer', 'group_id', 'is_all', 'question')
		database = database
		table_settings = ['ENGINE=InnoDB', 'DEFAULT CHARSET=utf8mb4']


if enable_index:
	Question.add_index(Question.index(Question.question, Question.group_id, Question.creator_id, Question.is_all,
	                                  Question.create_time))
else:
	pass


class question_log(Model):
	"""
	action: trigger/delete/add
	"""
	operator_id = BigIntegerField()
	group_id = BigIntegerField()
	target_question = CharField(max_length=100)
	target_answer = CharField(max_length=665)
	is_all = BooleanField(default=False)
	action = CharField()
	time_created = TimestampField(default=time.time())
	
	class Meta:
		database = database
		table_settings = ['ENGINE=InnoDB', 'DEFAULT CHARSET=utf8mb4']


try:
	database.connect()
	if not Question.table_exists():
		database.create_tables([Question])
		database.execute_sql(r'ALTER TABLE `question` MODIFY COLUMN `id` int(11) NOT NULL AUTO_INCREMENT FIRST;')
	if not question_log.table_exists():
		database.create_tables([question_log])
	database.close()
except Exception as e:
	traceback.print_exc()
	hoshino.logger.error(f"初始化时出错{e}")
