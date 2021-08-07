# 你问我答

基于主流的MySQL而非二进制存储的sqlitedict的可靠、易用、易维护的新版你问我答插件。

## 特点
- 基于主流MySQL数据库，以文本方式存储，便于维护
- 支持配置我问的问题与有人问的问题的优先度
- 支持配置一个问题多个回答时的行为
- 支持回答限频以免刷屏
- 不允许回答与问题相同或回答与数据库中其他的问题相同的回答，以免机器人进入死循环
- 回答列表过多时智能分页，交互式操作
- 支持问答日志，以便溯源危险问答的添加者
- 支持多种存储问答图片的方式
- 支持单独删除一个问题下某一个回答，或清空某一问题下所有回答

## 安装方法

1. clone本仓库
2. `__bot__.py`中加入`QA`
3. <b>（如果需要从eqa迁移数据）</b>将`migration.py`放在eqa目录下，并运行
4. 将`qa.py`打开配置后复制到`config/`下
5. 安装必须依赖

### 注意事项

1. 为了使MySQL支持emoji的存储,请参考以下文章进行配置:  
   [mysql下emoji的存储](https://www.jianshu.com/p/770c029ce5af)

2. 解决`create table: Specified key was too long; max key length is 767 bytes`错误:  
   [解决字段太长的问题](https://blog.51cto.com/u_13476134/2377030)

3. 需要nonebot 1.8.0+（通常随hoshino一同安装的都是1.6.0，所以需要升级）

4. 长度限制及元素长度参考(InnoDB引擎限制)  
   问题限制:100字符,超出者会被截断  
   回答限制:665字符,超出者会被截断    
   其中,  
   换行符:占1或2个字符  
   图片:
   - 处于问题中的图片一律只存储md5,即每张占54字符
   - link方式存储的每张固定占97字符
   - rel_path方式存储的每张固定占57字符
   - abs_path方式存储的每张占 56+路径长度 字符

## 指令表

全部指令如下:   
你问/有人问/大家问...你答...    
全体问答/看看有人问/看看大家问/全部问答/所有问答    
我的问答/看看我问   
不要回答/删除回答 id+回答id/问题  
