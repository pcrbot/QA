import json
import os
import sys
import time
import traceback

import sqlitedict
import yaml
from peewee import *

if __name__ == '__main__':
	print("==========eqa数据库迁移脚本==========")
	print("开始之前,请将本脚本置于eqa目录下,与eqa的配置文件config.yaml同级")
	if input('准备好之后请输入\"ready\"继续:') != 'ready':
		sys.exit()
	try:
		print('正在读取eqa配置文件...')
		with open(os.path.join(os.path.dirname(__file__), "../eqa/config.yaml"), 'r', encoding="utf-8") as f:
			config = yaml.load(f.read(), Loader=yaml.FullLoader)
	except FileNotFoundError:
		print('无法读取eqa配置文件,请确认目录正确后重试')
		time.sleep(3)
		sys.exit()
	data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), config['cache_dir']))
	print("正在装载eqa数据库...")
	try:
		question_dict = dict(sqlitedict.SqliteDict(os.path.join(data_dir, 'db.sqlite'), encode=json.dumps,
		                                           decode=json.loads, autocommit=True))
	except:
		traceback.print_exc()
		print(f"装载eqa数据库失败,请确认数据库存在后重试(应位于{os.path.join(data_dir, 'db.sqlite')})")
		time.sleep(3)
		sys.exit()
	print("询问MySQL数据库信息...")
	MySQL_host = input('请输入MySQL主机名:')
	MySQL_port = input('请输入端口号:')
	while not MySQL_port.isdigit():
		MySQL_port = input('请输入端口号:')
	MySQL_port = int(MySQL_port)
	MySQL_username = input('请输入用户名:')
	MySQL_password = input('请输入密码:')
	MySQL_database = input('请输入数据库名:')
	
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
	
	
	class question_log(Model):
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
		print("初始化MySQL数据库中...")
		database.connect()
		if not Question.table_exists():
			database.create_tables([Question])
			database.execute_sql(r'ALTER TABLE `question` MODIFY COLUMN `id` int(11) NOT NULL AUTO_INCREMENT FIRST;')
		if not question_log.table_exists():
			database.create_tables([question_log])
		database.close()
	except Exception as e:
		traceback.print_exc()
		print(f"初始化MySQL数据库时出错{e}")
		time.sleep(5)
		sys.exit()
	print("正在执行迁移...")
	print("整理数据中...")
	new_question_list = []
	for question, data in question_dict.items():
		for answer in data:
			data_dict = {'question': answer['qus'], 'is_all': True if not answer['is_me'] else False,
			             'creator_id': answer["user_id"], 'group_id': answer["group_id"], 'answer': ''}
			for a in answer['message']:
				if a['type'] == 'text':
					data_dict['answer'] += a['data']['text']
				elif a['type'] == 'image':
					data_dict['answer'] += '[CQ:image,file=rfile:///' + a['data']['file'].split('\\')[-1] + ']'
				else:
					continue
			data_dict['answer'] = data_dict['answer'].strip()
			new_question_list.append(data_dict)
	print(f"数据整理完成,共{len(new_question_list)}条")
	print("正在更新数据库...")
	try:
		Question.replace_many(new_question_list).execute()
		print("正在清理数据库...")
		query = Question.delete().where(
			(Question.question == Question.answer) | (Question.question == '') | (Question.answer == '')).execute()
		print('数据库清理完毕,共清理' + str(query) + '条无效数据(答案或者问题为空/答案与问题相同)')
	except:
		traceback.print_exc()
		print("更新数据库时出错")
	print("数据库更新完成")
	print(f"最后一步:请将{os.path.join(data_dir, 'img')}文件夹中的文件手动复制到res/img/questions中")
	time.sleep(60)
