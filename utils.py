import base64
import imghdr
import os
import random
import re
import traceback
from io import BytesIO
from typing import List, Optional, Tuple

import httpx
import peewee
from PIL import Image

import hoshino
from hoshino import R
from hoshino.config.qa import *

image_regex = re.compile(r'\[CQ:image,file=([a-z0-9]+)\.image]')
handle_image_regex = re.compile(r'\[CQ:image,file=([^,]*)]')
type_regex = re.compile(r'^(有人问|大家问|我问)')
wrong_command_regex = re.compile(r'^不要回答[^\s]')
validator_regex = re.compile(r'^(删除问答|删除回答|不要回答)')
resource_dir = R.get('img/questions').path

if not os.path.exists(resource_dir):
	os.makedirs(resource_dir)


async def _get_answer(answer_list: list) -> Optional[str]:
	if not answer_list:
		return None
	if not multiple_answer_return_random:
		return await handle_image(answer_list[0], 'show')
	return await handle_image(random.choice(answer_list), 'show')


async def get_answer(query: peewee.Query) -> Tuple[Optional[str], bool]:
	"""
	:param query:peewee query
	:return
	2-element tuple(answer,is_all)
	"""
	to_all_satisfied_answer = [x.answer for x in query if x.is_all]
	to_me_satisfied_answer = [x.answer for x in query if not x.is_all]
	if to_all_question_override:
		if answer := await _get_answer(to_all_satisfied_answer):
			return answer, True
		else:
			return await _get_answer(to_me_satisfied_answer), False
	else:
		if answer := await _get_answer(to_me_satisfied_answer):
			return answer, False
		else:
			return await _get_answer(to_all_satisfied_answer), True


async def separate_questions(query: peewee.Query, separate: int = 10) -> List[List[dict]]:
	"""
	:param query: peewee query
	:param separate:每隔separate条分割为一个list,默认10条
	...
	:return:
	[[{...},{...}],[{...},...],...]
	"""
	query = list(query.dicts())
	for x in query:
		x['question'] = await handle_image(x['question'], 'show')
		x['answer'] = await handle_image(x['answer'], 'show')
	return [query[i:i + separate] for i in range(0, len(query), separate)]


def text_validator(option: str, current_pages: int, max_pages: int) -> bool:
	if validator_regex.search(option):
		return True
	elif option == '下一页':
		return current_pages + 1 <= max_pages
	else:
		return False


async def handle_image(message: str, _type: str) -> str:
	"""
	image may like:
	[CQ:image,file=https://xxxx.com/xxxx](link)
	[CQ:image,file=file:///C:/home/user/res/img/xxx.jpg](abs_path)
	[CQ:image,file=rfile:///res/img/xxx.jpg](rel_path)
	:param message
	:param _type: save/show
	:return:
	processed message(based on config)
	"""
	if _type == 'show':
		return handle_image_regex.sub(lambda match: '[CQ:image,file=' + get_image(match.group(1)) + ']', message)
	elif _type == 'save':
		if image_save_method in ['abs_path', 'rel_path']:
			for image in image_regex.finditer(message):
				filename = image.group(1)
				if os.path.isfile(filename):
					hoshino.logger.info(f"{filename} exists, skip downloading...")
					continue
				try:
					async with httpx.AsyncClient() as client:
						resp = await client.get(
							'http://gchat.qpic.cn/gchatpic_new/0/0-0-' + filename.upper() + '/0?term=2', timeout=10)
						if resp.status_code != 200:
							hoshino.logger.error(
								f'error occurred when downloading image {filename}:http {resp.status_code}')
							continue
						img = Image.open(BytesIO(resp.content))
						if img.mode != "RGB":
							img = img.convert('RGB')
					file_extension_name = imghdr.what(None, resp.content)
					img.save(os.path.join(resource_dir, f'{filename}'), file_extension_name)
					hoshino.logger.info(f"image saved to {resource_dir}(type:{file_extension_name})")
				except Exception as e:
					traceback.print_exc()
					hoshino.logger.error(f'error occurred when downloading image {filename}:{e}')
					continue
			if image_save_method == 'abs_path':
				return image_regex.sub(lambda match:
				                       r'[CQ:image,file=file:///{}]'.format(
					                       os.path.join(resource_dir, f'{filename}')), message).strip()
			else:
				return image_regex.sub(lambda match:
				                       r'[CQ:image,file=rfile:///{}]'.format(f'{filename}'), message).strip()
		elif image_save_method == 'link':
			return image_regex.sub(lambda match:
			                       '[CQ:image,file=http://gchat.qpic.cn/gchatpic_new/0/0-0-' + match.group(
				                       1).upper() + '/0?term=2]', message).strip()
		else:
			return message.strip()
	else:
		return message.strip()


def get_image(image_uri: str) -> str:
	"""
	:param image_uri:uri of image(with protocol prefix)
	:return:
	path to image(with prefix 'file:///')
	or
	base64 string of image(with prefix 'base64://')
	(based on config)
	"""
	if image_uri.startswith('rfile:///'):
		image_path = os.path.join(resource_dir, image_uri.replace('rfile:///', ''))
		return _get_image(image_path)
	elif image_uri.startswith('file:///'):
		return _get_image(image_uri.replace('file:///', ''))
	elif image_uri.endswith('.image'):
		return f'http://gchat.qpic.cn/gchatpic_new/0/0-0-{image_uri.replace(".image", "").upper()}/0?term=2'
	else:
		return image_uri


def _get_image(image_uri: str) -> str:
	if image_send_method == 'base64':
		try:
			with open(image_uri, 'rb') as f:
				return 'base64://' + base64.b64encode(f.read()).decode('utf-8')
		except FileNotFoundError:
			hoshino.logger.error(f"image not found:{image_uri}")
			with open(os.path.join(os.path.dirname(__file__), 'image_not_found.jpg'), 'rb') as f:
				return 'base64://' + base64.b64encode(f.read()).decode('utf-8')
	elif image_send_method == 'file':
		return 'file:///' + image_uri
