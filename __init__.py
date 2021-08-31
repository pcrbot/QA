import asyncio

from nonebot import CommandSession
from nonebot.command.argfilter import controllers, extractors
from nonebot.command.argfilter.validators import ensure_true

from hoshino import Service
from hoshino.priv import ADMIN, check_priv
from hoshino.typing import CQEvent
from .database import Question, question_log
from .utils import *

sv = Service('你问我答')

during_interactive = False

try:
	session_timeout = hoshino.config.SESSION_EXPIRE_TIMEOUT.total_seconds()
except:
	session_timeout = 60


async def pagination_display(session: CommandSession, display_title: str, question: List[List[dict]],
                             display_type: str = 'display'):
	""":params display_type: display(展示) , confirm(操作确认)"""
	global during_interactive
	i = 0
	for page in question:
		i += 1
		msg = f'{display_title}\n' \
		      f'-----第{i}/{len(question)}页-----\n'
		for _question in page:
			if display_type == 'display':
				msg += f'id：{_question["id"]} 问题：{_question["question"]} 回答：{_question["answer"]} \n'
			elif display_type == 'confirm':
				msg += f'id：{_question["id"]} 作用范围：{"全体" if _question["is_all"] else "个人"} 回答：{_question["answer"]} \n'
		tip = f'使用"不要回答 id+数字id"删除问题下的指定id的答案(如：不要回答 id1)，使用"取消"退出流程({session_timeout}秒后会自动退出)'
		if i == len(question):
			msg += '-----完-----'
			tip = '※' + tip
		else:
			tip = '※使用"下一页"翻页，' + tip
		await session.send('\n' + msg, at_sender=True)
		await asyncio.sleep(0.15)
		during_interactive = True
		try:
			option = await session.aget(prompt=tip,
			                            arg_filters=[extractors.extract_text, str.strip,
			                                         controllers.handle_cancellation(session),
			                                         ensure_true(
				                                         lambda _option: True if
				                                         text_validator(_option, i, len(question)) else False,
				                                         message='指令错误，请重试')])
		except asyncio.exceptions.TimeoutError:
			return
		finally:
			during_interactive = False
		if validator_regex.search(option):
			await _delete_questions(session)
			return


@sv.on_message()
async def _handle_reply(bot: hoshino.HoshinoBot, ev: CQEvent):
	message = ev.raw_message.strip()
	if during_interactive:
		return
	try:
		query = Question.select().where(
			Question.question == message, Question.group_id == ev.group_id,
			(Question.is_all == True) | (Question.creator_id == ev.user_id)). \
			order_by(Question.create_time.desc())
	except Exception as e:
		traceback.print_exc()
		hoshino.logger.error(f"查询你问我答数据库时出错{e}")
		return
	if not query:
		return
	else:
		answer, is_all = await get_answer(query)
		if not answer:
			return
		else:
			await asyncio.sleep(answer_delay)
			await bot.send(ev, answer)
			if record_trigger_log:
				question_log.replace(
					{'operator_id': ev.user_id, 'group_id': ev.group_id,
					 'target_question': message, 'target_answer': answer,
					 'is_all': is_all, 'action': 'trigger'}).execute()


@sv.on_message()
async def _modify_question(bot: hoshino.HoshinoBot, ev: CQEvent):
	message = ev.raw_message.strip()
	if message.startswith(('有人问', '大家问', '我问')):  # 我问/大家问/有人问...你答...
		question_list = message.split('你答', maxsplit=1)
		if len(question_list) == 1:
			await bot.send(ev, "回答呢回答呢回答呢？", at_sender=True)
			return
		question, answer = question_list
		is_all = True if type_regex.search(question).group() in ('有人问', '大家问') else False
		if is_all and not check_priv(ev, ADMIN):
			await bot.send(ev, f'只有管理员才能设置{question[:3]}哦~', at_sender=True)
			return
		question = type_regex.sub('', question, count=1).strip()
		answer = await handle_image(answer, 'save')
		if not question or not answer:
			await bot.send(ev, "问题呢问题呢回答呢回答呢？", at_sender=True)
			return
		if question == answer:
			await bot.send(ev, "你搁这搁这呢？[CQ:face,id=97]", at_sender=True)
			return
		if Question.select().where(
				Question.question == answer, Question.answer == question, Question.group_id == ev.group_id,
				(Question.is_all == True) | (Question.creator_id == ev.user_id)):
			await bot.send(ev, "死循环是吧？差不多得了[CQ:face,id=97]", at_sender=True)
			return
		try:
			Question.replace(question=question,
			                 answer=answer,
			                 group_id=ev.group_id,
			                 creator_id=ev.user_id,
			                 is_all=is_all).execute()
		except Exception as e:
			traceback.print_exc()
			await bot.send(ev, f"设置问题时出错{type(e)}", at_sender=True)
			return
		await bot.send(ev, '好的我记住了', at_sender=True)
		question_log.replace(
			{'operator_id': ev.user_id, 'group_id': ev.group_id,
			 'target_question': question, 'target_answer': answer,
			 'is_all': is_all, 'action': 'add'}).execute()
	elif wrong_command_remind:
		if wrong_command_regex.search(message):
			await bot.send(ev, "请使用\"不要回答 问题或id+数字id\"来删除，中间有空格(如：不要回答 id1/不要回答 这是问题)", at_sender=True)
	else:
		return


@sv.on_command('删除问答', aliases=('删除回答', '不要回答'))
async def _delete_questions(session: CommandSession):
	global during_interactive
	args = validator_regex.sub("", session.current_arg).strip()
	if args.startswith('id') and args.replace("id", "").isdigit():
		args = int(args.replace("id", ""))
		param_list = [Question.id == args]
		if not check_priv(session.event, ADMIN):
			param_list.append(Question.is_all == False)
		try:
			question = Question.get_or_none(id=args)
			query = Question.delete().where(*param_list).execute()
		except Exception as e:
			session.finish(f"删除回答时出现错误{type(e)}", at_sender=True)
		if query == 0:
			session.finish(f"没有找到这个问题哦"
			               f"{'，有可能您试图删除的问题是全体问答(只有管理员才能删除)' if not check_priv(session.event, ADMIN) else ''}",
			               at_sender=True)
		else:
			await session.send(f"我不再作出这个回答啦~", at_sender=True)
			question_log.replace(
				{'operator_id': session.event.user_id, 'group_id': session.event.group_id,
				 'target_question': question.question, 'target_answer': question.answer,
				 'is_all': question.is_all, 'action': 'delete'}).execute()
			return
	else:
		try:
			if not check_priv(session.event, ADMIN):
				question = await separate_questions(Question.select().where(
					Question.question == args, Question.group_id == session.event.group_id,
					Question.creator_id == session.event.user_id))
			else:
				question = await separate_questions(Question.select().where(
					Question.question == args, Question.group_id == session.event.group_id,
					(Question.is_all == True) | (Question.creator_id == session.event.user_id)))
		except Exception as e:
			traceback.print_exc()
			session.finish(f"查询问答时出现错误{type(e)}", at_sender=True)
		if not question:
			session.finish("没有找到这个问题哦"
			               f"{'，有可能您试图删除的问题是全体问答(只有管理员才能删除)' if not check_priv(session.event, ADMIN) else ''}",
			               at_sender=True)
		elif len(question) == 1 and len(question[0]) == 1:
			try:
				Question.delete().where(Question.id == question[0][0]['id']).execute()
			except Exception as e:
				traceback.print_exc()
				session.finish(f"删除回答时出现错误{type(e)}", at_sender=True)
			await session.send(f"我不再作出这个回答啦~", at_sender=True)
			question_log.replace_many(
				[{'operator_id': session.event.user_id, 'group_id': session.event.group_id,
				  'target_question': x['question'], 'target_answer': x['answer'],
				  'is_all': x['is_all'], 'action': 'delete'} for x in sum(question, [])]
			).execute()
			return
		else:
			during_interactive = True
			option = await session.aget(prompt='\n您想删除的问题有多个回答，请选择：\n1.展开回答列表，删除个别回答\n2.全部删除',
			                            arg_filters=[extractors.extract_text, str.strip,
			                                         controllers.handle_cancellation(session),
			                                         ensure_true(
				                                         lambda _option: True if
				                                         int(_option) in [1, 2] else False,
				                                         message='选项错误，请重试')], at_sender=True)
			during_interactive = False
			if int(option) == 1:
				await pagination_display(session, "请从其中选择要删除的回答", question, 'confirm')
			elif int(option) == 2:
				try:
					if not check_priv(session.event, ADMIN):
						Question.delete().where(Question.question == args, Question.is_all == False).execute()
					else:
						Question.delete().where(Question.question == args).execute()
				except Exception as e:
					traceback.print_exc()
					session.finish(f"删除回答时出现错误{type(e)}", at_sender=True)
				await session.send(f"我不再作出这个回答啦~", at_sender=True)
				question_log.replace_many(
					[{'operator_id': session.event.user_id, 'group_id': session.event.group_id,
					  'target_question': x['question'], 'target_answer': x['answer'],
					  'is_all': x['is_all'], 'action': 'delete'} for x in sum(question, [])]
				).execute()
				return
			else:
				return


@sv.on_command('全体问答', aliases=('看看有人问', '看看大家问', '我的问答', '看看我问', '全部问答', '所有问答'))
async def _view_questions(session: CommandSession):
	try:
		if session.event.raw_message.strip() in ('我的问答', '看看我问'):
			question = await separate_questions(Question.select().where(
				Question.group_id == session.event.group_id,
				Question.creator_id == session.event.user_id,
				Question.is_all == False), separate=question_per_page)
			title = '你的个人问答：'
		else:
			if not check_priv(session.event, ADMIN):
				await session.send("只有管理员及以上才能查看全体的问答哦~", at_sender=True)
				return
			question = await separate_questions(Question.select().where(
				Question.group_id == session.event.group_id,
				Question.is_all == True), separate=question_per_page)
			title = '本群的全体问答：'
	except Exception as e:
		session.finish(f"查询问答时出错{e}", at_sender=True)
	if not question:
		session.finish(f"{title}\n空")
	await pagination_display(session, title, question)
