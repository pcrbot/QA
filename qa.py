# 数据库设置

MySQL_host = ""
MySQL_port = 3306
MySQL_username = ''
MySQL_password = ''
MySQL_database = 'datatest'
enable_index = True
# 启用索引(查询更快速,但插入&删除&更新时更慢,详见README)
# 请注意:仅在初次配置(数据库未初始化)时有效.一经初始化数据库,不能修改

# 基本功能设置

to_all_question_override = True  # 全体问答是否覆盖个人问答
multiple_answer_return_random = True  # 多个答案是否返回随机回答(否则返回最新的回答)
question_per_page = 10  # 每页显示的问题数
answer_delay = 0.1  # 触发回答时发送的延迟,用于限频(秒)
wrong_command_remind = True  # 触发旧指令(eqa的指令)时给予提示(设置旧指令请修改__init__.py:23)
record_trigger_log = True  # 记录触发日志(创建&删除日志会始终记录)
image_save_method = 'link'
# 图片存储方式
# abs_path:直接存储绝对路径(/home/user/...)
# rel_path:存储相对路径(res/img/...)
# link:存储服务器上的图片链接(对于eqa的不在服务器上的本地图片,会以rel_path做兼容)
image_send_method = 'base64'  # 本地图片发送方式 base64 / file

# 文本/图片鉴定功能设置
# 目前还是个饼,计划接入阿里云,然后鉴定必须上传到阿里云的服务器,因此肯定会拖延添加的进程

assert image_save_method in ('abs_path', 'rel_path', 'link'), \
	"image_save_method must be one of 'abs_path', 'rel_path', 'link'"
assert image_send_method in ('file', 'base64'), \
	"image_send_method must be one of 'file', 'base64'"
