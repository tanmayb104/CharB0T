# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2022 Bluesy1 <68259537+Bluesy1@users.noreply.github.com>
#
# SPDX-License-Identifier: MIT
"""Collection of functions for buying, retrieving, and using user items."""
from __future__ import annotations

from typing import TYPE_CHECKING, cast

import asyncpg
from discord.app_commands import Choice
from typing_extensions import assert_never

from ..types import Item, ItemUseInfo
from ..utils import ItemsView
from ..enums import Benefits
from . import item_utils as utils

if TYPE_CHECKING:  # pragma: no cover
    from ... import CBot, GuildInteraction


async def view_available_items_autocomplete(interaction: GuildInteraction[CBot], current: str) -> list[Choice[str]]:
    """Autocomplete for buying an item.

    Parameters
    ----------
    interaction : GuildInteraction[CBot]
        The interaction.
    current : str
        The current string.

    Returns
    -------
    choices : list[Choice[str]]
        The choices.
    """
    async with interaction.client.pool.acquire() as conn:
        if not await conn.fetchrow("SELECT TRUE FROM gang_members WHERE user_id = $1", interaction.user.id):
            return []
        items = await conn.fetch("SELECT name, cost FROM user_items ORDER BY value")
        return [
            Choice(name=f"{i['name']} - Cost: {i['cost']}", value=i["name"])
            for i in items
            if i["name"].startswith(current)
        ][:25]


async def view_item_autocomplete(interaction: GuildInteraction[CBot], current: str) -> list[Choice[str]]:
    """Autocomplete for viewing an item.

    Parameters
    ----------
    interaction : GuildInteraction[CBot]
        The interaction.
    current : str
        The current string.

    Returns
    -------
    choices : list[Choice[str]]
        The choices.
    """
    async with interaction.client.pool.acquire() as conn:
        if not await conn.fetchrow("SELECT TRUE FROM gang_members WHERE user_id = $1", interaction.user.id):
            return []
        items = await conn.fetch(
            "SELECT name FROM user_inventory JOIN user_items ui on ui.id = user_inventory.item WHERE user_id = $1",
            interaction.user.id,
        )
        return [Choice(name=i["name"], value=i["name"]) for i in items if i["name"].startswith(current)][:25]


async def try_buy_item(pool: asyncpg.Pool, user_id: int, item_name: str) -> str | int:
    """Try to buy a user item

    Parameters
    ----------
    pool : asyncpg.Pool
        The pool.
    user_id : int
        The user's ID.
    item_name : str
        The item's name.

    Returns
    -------
    remaining : str | int
        The remaining points, or a string error.
    """
    async with pool.acquire() as conn, conn.transaction():
        if not await conn.fetchval("SELECT TRUE FROM gang_members WHERE user_id = $1", user_id):
            return "You must be in a gang to buy items."
        item = await conn.fetchrow("SELECT * FROM user_items WHERE name = $1", item_name)
        if item is None:
            return f"The item `{item_name}` you requested doesn't exist."
        points: int = await conn.fetchval("SELECT points FROM users WHERE id = $1", user_id)
        if points < item["value"]:
            return f"You don't have enough rep to buy that. (Have: {points}, Need: {item['value']})"
        await conn.execute(
            "INSERT INTO user_inventory (user_id, item, quantity) VALUES ($1, $2, 1) ON CONFLICT(user_id, item) "
            "DO UPDATE SET quantity = (SELECT quantity + 1 FROM user_inventory WHERE user_id = $1 AND item = $2)",
            user_id,
            item["id"],
        )
        return await conn.fetchval(
            "UPDATE users SET points = points - $1 WHERE id = $2 RETURNING points", item["value"], user_id
        )


async def try_display_inventory(pool: asyncpg.Pool, user_id: int) -> str | ItemsView:
    """Try to display the user's inventory.

    Parameters
    ----------
    pool : asyncpg.Pool
        The database pool.
    user_id : int
        The user's ID.

    Returns
    -------
    items : str | ItemsView
        The view for the items, or a string error.
    """
    async with pool.acquire() as conn:
        items = await conn.fetch(
            "SELECT name, description, cost, quantity "
            "FROM user_items INNER JOIN user_inventory ui on user_items.id = ui.item WHERE ui.user_id = $1",
            user_id,
        )
        if not items:
            return "You don't have any items."
        return ItemsView([Item(**item) for item in items], user_id)


async def try_display_available_items(pool: asyncpg.Pool, user_id: int) -> str | ItemsView:
    """Try to display the available items.

    Parameters
    ----------
    pool : asyncpg.Pool
        The database pool.
    user_id : int
        The user's ID.

    Returns
    -------
    items : str | ItemsView
        The view for the items, or a string error.
    """
    async with pool.acquire() as conn:
        if not await conn.fetchval("SELECT TRUE FROM gang_members WHERE user_id = $1", user_id):
            return "You must be in a gang to have items."
        items = await conn.fetch("SELECT name, description, cost, NULL as quantity FROM user_items")
        if not items:
            return "There are no items available."
        return ItemsView([Item(**item) for item in items], user_id)


async def try_display_item(pool: asyncpg.Pool, user_id: int, item_name: str) -> str:
    """Try to display an item.

    Parameters
    ----------
    pool : asyncpg.Pool
        The database pool.
    user_id : int
        The user's ID.
    item_name : str
        The item's name.

    Returns
    -------
    item : str
        A string denoting the item, or an error.
    """
    async with pool.acquire() as conn:
        if not await conn.fetchval("SELECT TRUE FROM gang_members WHERE user_id = $1", user_id):
            return "You must be in a gang to have items."
        item = await conn.fetchrow(
            "SELECT name, description, cost, quantity FROM user_items "
            "LEFT OUTER JOIN user_inventory ui on user_items.id = ui.item WHERE ui.user_id = $1 AND name = $2",
            user_id,
            item_name,
        ) or await conn.fetchrow(
            "SELECT name, description, cost, 0 as quantity FROM user_items WHERE name = $1", item_name
        )
        if item is None:
            return f"The item `{item_name}` does not exist."
        return f"**{item['name']}**\n{item['description']}\nCost: {item['cost']}\nOwned: {item['quantity']}"


async def try_sell_item(pool: asyncpg.Pool, user_id: int, item_name: str) -> str | int:
    """Try to sell a user item

    Parameters
    ----------
    pool : asyncpg.Pool
        The pool.
    user_id : int
        The user's ID.
    item_name : str
        The item's name.

    Returns
    -------
    remaining : str | int
        The new rep, or a string error.
    """
    async with pool.acquire() as conn, conn.transaction():
        item = await conn.fetchrow(
            "SELECT id, quantity, cost FROM user_items INNER JOIN user_inventory ui on user_items.id = ui.item"
            " WHERE user_id = $1 AND name = $2",
            user_id,
            item_name,
        )
        if item is None:
            return f"You don't have any `{item_name}` to sell, or it doesn't exist."
        if item["quantity"] == 1:
            await conn.execute("DELETE FROM user_inventory WHERE user_id = $1 AND item = $2", user_id, item["id"])
        else:
            await conn.execute(
                "UPDATE user_inventory SET quantity = quantity - 1 WHERE user_id = $1 AND item = $2",
                user_id,
                item["id"],
            )
        return await conn.fetchval(
            "UPDATE users SET points = points + $1 WHERE id = $2 RETURNING points", item["cost"] // 10, user_id
        )


async def try_gift_item(pool: asyncpg.Pool, user_id: int, item_name: str, target: int) -> str:
    """Try to gift a user item

    Parameters
    ----------
    pool : asyncpg.Pool
        The pool.
    user_id : int
        The user's ID.
    item_name : str
        The item's name.
    target : int
        The target's ID.

    Returns
    -------
    remaining : str
        A string message denoting success or an error.
    """
    async with pool.acquire() as conn, conn.transaction():
        if not await conn.fetchval(
            "SELECT (leader OR leadership) AS is_leader FROM gang_members WHERE user_id = $1", user_id
        ):
            return "You are not in the leadership of a gang, you cannot gift items."
        item = await conn.fetchrow(
            "SELECT id, quantity FROM user_items INNER JOIN user_inventory ui on user_items.id = ui.item"
            " WHERE user_id = $1 AND name = $2",
            user_id,
            item_name,
        )
        if item is None:
            return f"You don't have any `{item_name}` to gift, or it doesn't exist."
        if item["quantity"] == 1:
            await conn.execute("DELETE FROM user_inventory WHERE user_id = $1 AND item = $2", user_id, item["id"])
        else:
            await conn.execute(
                "UPDATE user_inventory SET quantity = quantity - 1 WHERE user_id = $1 AND item = $2",
                user_id,
                item["id"],
            )
        await conn.execute(
            "INSERT INTO user_inventory (user_id, item, quantity) VALUES ($1, $2, 1) ON CONFLICT(user_id, item) "
            "DO UPDATE SET quantity = (SELECT quantity + 1 FROM user_inventory WHERE user_id = $1 AND item = $2)",
            target,
            item["id"],
        )
        return f"You gifted `{item_name}` to <@{target}>."


async def use_currency_item(conn: asyncpg.Connection, item: ItemUseInfo, user: int) -> str:
    """Use a currency item

    Parameters
    ----------
    conn : asyncpg.Connection
        The connection.
    item : ItemUseInfo
        The item to use.
    user : int
        The user's ID.

    Returns
    -------
    str
        A string message denoting success or an error.
    """
    ret = await conn.fetchval(
        "UPDATE users SET points = points + $1 WHERE id = $2 RETURNING points", item["value"], user
    )
    await utils.consume_item(conn, item["id"], item["quantity"], user=user)
    return f"You used `{item['name']}` and gained {item['value']} rep. You now have {ret} rep."


async def use_defensive_item(conn: asyncpg.Connection, item: ItemUseInfo, user, reusable) -> str:
    """Use a defensive item

    Parameters
    ----------
    conn : asyncpg.Connection
        The connection.
    item : ItemUseInfo
        The item to use.
    user : int
        The user's ID.
    reusable : bool
        Whether the item is reusable or not.

    Returns
    -------
    message : str
        A string message denoting success or an error.
    """
    ret = await utils.check_defensive_item(conn, user)
    if isinstance(ret, str):
        return ret
    if reusable:
        pts = await conn.fetchval("SELECT points FROM users WHERE id = $1", user)
        if pts < item["cost"]:
            return f"You do not have enough rep to use `{item['name']}`. You need {item['cost']} rep, and have {pts}."
        remaining = await conn.fetchval(
            "UPDATE users SET points = points - $1 WHERE id = $2 RETURNING points", item["value"], user
        )
        res = (
            f"You used `{item['name']}` and gained {item['value']} defense. Your gang now has "
            f"{ret['defense'] + item['value']} defense. You now have {remaining} rep."
        )
    else:
        await utils.consume_item(conn, item["id"], item["quantity"], user=user)
        res = (
            f"You used `{item['name']}` and gained {item['value']} defense. Your gang now has "
            f"{ret['defense'] + item['value']} defense."
        )
    await conn.execute("UPDATE territories SET defense = defense + $1 WHERE id = $2", item["value"], ret["id"])
    return res


async def use_offensive_item(conn: asyncpg.Connection, item: ItemUseInfo, user, reusable) -> str:
    """Use an offensive item

    Parameters
    ----------
    conn : asyncpg.Connection
        The connection.
    item : ItemUseInfo
        The item to use.
    user : int
        The user's ID.
    reusable : bool
        Whether the item is reusable or not.

    Returns
    -------
    message : str
        A string message denoting success or an error.
    """
    ret = await utils.check_offensive_item(cast(asyncpg.Connection, conn), user)
    if isinstance(ret, str):
        return ret
    if reusable:
        pts = await conn.fetchval("SELECT points FROM users WHERE id = $1", user)
        if pts < item["cost"]:
            return f"You do not have enough rep to use `{item['name']}`. You need {item['cost']} rep, and have {pts}."
        remaining = await conn.fetchval(
            "UPDATE users SET points = points - $1 WHERE id = $2 RETURNING points", item["value"], user
        )
        res = (
            f"You used `{item['name']}` and gained {item['value']} attack. Your gang now has "
            f"{ret['attack'] + item['value']} attack. You now have {remaining} rep."
        )
    else:
        await utils.consume_item(conn, item["id"], item["quantity"], user=user)
        res = (
            f"You used `{item['name']}` and gained {item['value']} attack. Your gang now has "
            f"{ret['attack'] + item['value']} attack."
        )
    await conn.execute("UPDATE territories SET attack = attack + $1 WHERE id = $2", item["value"], ret["id"])
    return res


async def try_use_item(pool: asyncpg.Pool, user_id: int, item_name: str) -> str:
    """Try to use a user item

    Parameters
    ----------
    pool : asyncpg.Pool
        The pool.
    user_id : int
        The user's ID.
    item_name : str
        The item's name.

    Returns
    -------
    remaining : str
        A string message denoting success or an error.
    """
    async with pool.acquire() as conn, conn.transaction():
        item = cast(
            ItemUseInfo,
            await conn.fetchrow(
                "SELECT id, name, quantity, value, benefit, cost FROM user_items "
                "INNER JOIN user_inventory ui on user_items.id = ui.item WHERE user_id = $1 AND name = $2",
                user_id,
                item_name,
            ),
        )
        if item is None:  # pragma: no cover
            return f"You don't have any `{item_name}` to use, or it doesn't exist."
        match item["benefit"]:
            case Benefits.currency | Benefits.currency_consumable:
                return await use_currency_item(cast(asyncpg.Connection, conn), item, user_id)
            case Benefits.defense:
                return await use_defensive_item(cast(asyncpg.Connection, conn), item, user_id, True)
            case Benefits.defense_consumable:
                return await use_defensive_item(cast(asyncpg.Connection, conn), item, user_id, False)
            case Benefits.offense:
                return await use_offensive_item(cast(asyncpg.Connection, conn), item, user_id, True)
            case Benefits.offense_consumable:
                return await use_offensive_item(cast(asyncpg.Connection, conn), item, user_id, False)
            case Benefits.other:
                return f"You cannot use `{item['name']}`. It is not a usable item."
            case _:  # pragma: no cover
                assert_never(item["benefit"])
