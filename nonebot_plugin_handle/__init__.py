import asyncio
from asyncio import TimerHandle
from datetime import datetime
from typing import Any, Dict
from nonebot import on_command, on_message, on_regex, on_shell_command, require
from nonebot.adapters.onebot.v11 import PrivateMessageEvent, GroupMessageEvent
from nonebot.utils import logger_wrapper, run_sync
from nonebot.matcher import Matcher
from nonebot.params import RegexDict, RegexGroup
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot.rule import is_type, to_me

from typing_extensions import Annotated

require("nonebot_plugin_alconna")
require("nonebot_plugin_session")

from nonebot_plugin_alconna import (
    Alconna,
    AlconnaQuery,
    Image,
    Option,
    Query,
    Text,
    UniMessage,
    on_alconna,
    store_true,
)
from nonebot_plugin_session import SessionId, SessionIdType

from .config import Config, handle_config
from .data_source import GuessResult, Handle
from .utils import game_mode
from .utils import random_idiom, init_answers

logger = logger_wrapper('Handle')

no_limit_groups = [
    '62195088',
]

current_games = {}
last_game = {}
temp_no_limit_groups = []
game_start = list(game_mode.keys())
all_category_list = ['主线关卡', '主线章节', '保全派驻关卡', '傀影与猩红孤钻中的事件', '傀影与猩红孤钻中的关卡', '傀影与猩红孤钻中的收藏品', '关卡', '其他', '其他天赋', '其他技能', '刻俄柏的灰蕈迷境中的事件', '刻俄柏的灰蕈迷境中的关卡', '刻俄柏的灰蕈迷境中的收藏品', '剿灭关卡', '卡池', '周常关卡', '周常章节', '干员代号', '干员基建技能', '干员天赋', '干员技能', '干员模组', '探索者的银凇止境中的事件', '探索者的银凇止境中的关卡', '探索者的银凇止境中的收藏品', '敌人', '水月与深蓝之树中的事件', '水月与深蓝之树中的关卡', '水月与深蓝之树中的排异反应', '水月与深蓝之树中的收藏品', '活动', '活动关卡', '活动章节', '物品', '生息演算-沙中之火中的关卡', '生息演算-沙中之火中的物品', '生息演算-沙洲遗闻中的关卡', '生息演算-沙洲遗闻中的物品', '生息演算关卡', '生息演算物品', '皮肤', '章节', '装置/可部署物品名', '阵营', '集成战略事件', '集成战略关卡', '集成战略分队', '集成战略层数', '集成战略收藏品', '集成战略结局', '集成战略节点', '集成战略难度选项']
ji_category_list = [
    '集成战略事件', '集成战略关卡', '集成战略分队', '集成战略层数', '集成战略收藏品', '集成战略结局', '集成战略节点', '集成战略难度选项',
    '刻俄柏的灰蕈迷境中的事件', '刻俄柏的灰蕈迷境中的关卡', '刻俄柏的灰蕈迷境中的收藏品',
    '傀影与猩红孤钻中的事件', '傀影与猩红孤钻中的关卡', '傀影与猩红孤钻中的收藏品',
    '探索者的银凇止境中的事件', '探索者的银凇止境中的关卡', '探索者的银凇止境中的收藏品',
    '水月与深蓝之树中的事件', '水月与深蓝之树中的关卡', '水月与深蓝之树中的排异反应', '水月与深蓝之树中的收藏品',
]

is_group_msg = is_type(GroupMessageEvent)

logger('INFO', init_answers())

## ======================

__plugin_meta__ = PluginMetadata(
    name="猜成语",
    description="汉字Wordle 猜成语",
    usage=(
        "@我 + “猜成语”开始游戏；\n"
        "你有十次的机会猜一个四字词语；\n"
        "每次猜测后，汉字与拼音的颜色将会标识其与正确答案的区别；\n"
        "青色 表示其出现在答案中且在正确的位置；\n"
        "橙色 表示其出现在答案中但不在正确的位置；\n"
        "每个格子的 汉字、声母、韵母、声调 都会独立进行颜色的指示。\n"
        "当四个格子都为青色时，你便赢得了游戏！\n"
        "可发送“结束”结束游戏；可发送“提示”查看提示。"
        "使用 --strict 选项开启非默认的成语检查，即猜测的短语必须是成语，\n"
        "如：@我 猜成语 --strict"
    ),
    type="application",
    homepage="https://github.com/noneplugin/nonebot-plugin-handle",
    config=Config,
    supported_adapters=inherit_supported_adapters(
        "nonebot_plugin_alconna", "nonebot_plugin_session"
    ),
    extra={
        "unique_name": "handle",
        "example": "@小Q 猜成语",
        "author": "meetwq <meetwq@gmail.com>",
        "version": "0.3.4",
    },
)



games: Dict[str, Handle] = {}
timers: Dict[str, TimerHandle] = {}

UserId = Annotated[str, SessionId(SessionIdType.GROUP)]

def game_is_running(user_id: UserId) -> bool:
    return user_id in games


def game_not_running(user_id: UserId) -> bool:
    return user_id not in games

handle = on_alconna(
    Alconna(
        game_start,
        Option("--hard", default=False, action=store_true),
        Option("-s|--strict", default=False, action=store_true),
        Option("--nohint", default=False, action=store_true),
        Option("--confirm", default=False, action=store_true),
        Option("--ji", default=False, action=store_true),
    ),
    aliases=("猜舟语",),
    rule=game_not_running,
    use_cmd_start=handle_config.handle_use_cmd_start,
    block=True,
    priority=13,
)
handle_hint = on_alconna(
    "提示",
    rule=game_is_running,
    use_cmd_start=handle_config.handle_use_cmd_start,
    block=True,
    priority=13,
)
handle_stop = on_alconna(
    "结束",
    aliases=("结束游戏", "结束猜成语"),
    rule=game_is_running,
    use_cmd_start=handle_config.handle_use_cmd_start,
    block=True,
    priority=13,
)
handle_idiom = on_regex(
    r"^(?P<idiom>[\u4e00-\u9fa5]{4})$",
    rule=game_is_running,
    block=True,
    priority=14,
)
handle_query_word = on_regex(
    r'^查询?P<name>(.{2})?P<word>(.*)',
    rule=is_group_msg,
    block=True,
    priority=14,
)


def stop_game(user_id: str):
    if timer := timers.pop(user_id, None):
        timer.cancel()
    games.pop(user_id, None)


async def stop_game_timeout(matcher: Matcher, user_id: str):
    game = games.get(user_id, None)
    stop_game(user_id)
    if game:
        msg = "猜成语超时，游戏结束。"
        if len(game.guessed_idiom) >= 1:
            msg += f"\n{game.result}"
        await matcher.finish(msg)


def set_timeout(matcher: Matcher, user_id: str, timeout: float = 300):
    if timer := timers.get(user_id, None):
        timer.cancel()
    loop = asyncio.get_running_loop()
    timer = loop.call_later(
        timeout, lambda: asyncio.ensure_future(stop_game_timeout(matcher, user_id))
    )
    timers[user_id] = timer



@handle.handle()
async def _(
    matcher: Matcher,
    user_id: UserId,
    hard: Query[bool] = AlconnaQuery("hard.value", False),
    strict: Query[bool] = AlconnaQuery("strict.value", False),
    nohint: Query[bool] = AlconnaQuery("nohint.value", False),
    confirm: Query[bool] = AlconnaQuery("confirm.value", False),
    ji: Query[bool] = AlconnaQuery("ji.value", False),
):
    is_hard = hard.result
    is_strict = is_hard or handle_config.handle_strict_mode or strict.result
    is_nohint = is_hard or nohint.result
    is_confirm = confirm.result
    mode, idiom, explanation, category, selected_category = random_idiom('arkdle', custom_category=ji_category_list if ji.result else [])
    game = Handle(mode, idiom, explanation, category, selected_category)

    games[user_id] = game
    set_timeout(matcher, user_id)

    extra_info = ''
    if is_hard:
        game.times = 5
        extra_info += '\n本局已启用困难模式，可猜次数变为5，自动禁用提示，自动启用严格模式'
    if is_nohint:
        game.hint_enabled = False
        extra_info += '\n本局已禁用提示'
    if is_strict:
        game.strict = True  # 是否判断输入词语为成语
        extra_info += '\n本局已启用严格模式，仅接受{}回答'.format(game.name)
        if is_confirm:
            game.confirm = True  # 是否判断输入词语为成语
            extra_info += '\n本局已启用确认模式，输入回答不为{}时将提示'.format(game.name)
    # current_games[cid] = game
    # last_game[cid] = game
    msg = Text('你有{}次机会猜一个四字{}{}\n本局出题范围为：{}'.format(
        game.times,
        game.name,
        extra_info,
        '、'.join(game.selected_category) or '全部'
    )) + Image(raw=await run_sync(game.draw)())
    await msg.send()

@handle_hint.handle()
async def _(matcher: Matcher, user_id: UserId):
    game = games[user_id]
    set_timeout(matcher, user_id)

    if game.hint_enabled == False:
        await matcher.finish('本局已禁用提示')
    elif len(game.guessed_idiom) - game.last_hint < 3:
        await matcher.finish('提示冷却中，距离下一次使用提示还需猜{}次'.format(3 - len(game.guessed_idiom) + game.last_hint))
    else:
        game.last_hint = len(game.guessed_idiom)
        msg = UniMessage(raw=await run_sync(game.draw_hint)())
        await msg.send()

@handle_stop.handle()
async def _(matcher: Matcher, user_id: UserId):
    game = games[user_id]
    stop_game(user_id)

    msg = "游戏已结束"
    if len(game.guessed_idiom) >= 1:
        msg += f"\n{game.result}"
    await matcher.finish(msg)


    # if options.nohint:
    #     if game.last_hint > 0:
    #         reply = '本局已使用过提示，不能再禁用提示'
    #     else:
    #         game.hint_enabled = False
    #         reply = '本局已禁用提示'
    #     await send(group_id, reply)

@handle_idiom.handle()
async def _(matcher: Matcher, user_id: UserId, matched: Dict[str, Any] = RegexDict()):
    game = games[user_id]
    set_timeout(matcher, user_id)

    idiom = str(matched["idiom"])

    result = game.guess(idiom)
    if result in [GuessResult.WIN, GuessResult.LOSS]:
        stop_game(user_id)
        msg = Text(
            (
                f"恭喜你猜出了{game.name}！({len(game.guessed_idiom)}/{game.times})"
                if result == GuessResult.WIN
                else "很遗憾，没有人猜出来呢"
            )
            + f"\n{game.result}"
        ) + Image(raw=await run_sync(game.draw)())
        await msg.send()

    elif result == GuessResult.DUPLICATE:
        await matcher.finish(f"你已经猜过这个{game.name}了呢", reply_message=True)

    elif result == GuessResult.ILLEGAL:
        if game.confirm:
            await matcher.finish(f"你确定这是个{game.name}吗？", reply_message=True)
    else:
        msg = Text('正在猜{}({}/{})\n范围：{}'.format(
            game.name,
            len(game.guessed_idiom),
            game.times,
            '、'.join(game.selected_category) or '全部'
        )) + Image(raw=await run_sync(game.draw)())
        await msg.send()

@handle_query_word.handle()
async def handle_query_word(matcher: Matcher, user_id: UserId, matched: Dict[str, Any] = RegexDict()):
    name = str(matched["name"]).strip()
    word = str(matched["word"]).strip()
    for mode in game_mode:
        if name == game_mode[mode]['name']:
            word_found = False
            for ans in game_mode[mode]['answers']:
                if word == ans['word']:
                    reply = '【{}】\n拼音：{}\n所属范围：{}\n释义：{}'.format(word, ' '.join(ans['pinyin']), '、'.join(ans['category']), ans['explanation'].replace('；', '\n'))
                    # logger('INFO', reply)
                    await query_word.finish(reply)
            else:
                reply = '你确定这是个四字{}吗？'.format(game_mode[mode]['name'])
                await query_word.finish(reply, reply_message=True)
