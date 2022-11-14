# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2022 Bluesy1 <68259537+Bluesy1@users.noreply.github.com>
#
# SPDX-License-Identifier: MIT
"""Collection of functions for buying, retrieving, and using gang items."""
from __future__ import annotations

from typing import TYPE_CHECKING

import asyncpg
from discord.app_commands import Choice

from ..types import Item
from ..utils import ItemsView

if TYPE_CHECKING:  # pragma: no cover
    from ... import CBot, GuildInteraction


async def view_available_items_autocomplete(interaction: GuildInteraction[CBot], current: str) -> list[Choice[str]]:
    """Autocomplete for viewing available items.

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
        if not await conn.fetchval(
            "SELECT (leader OR leadership) AS is_leader FROM gang_members WHERE user_id = $1", interaction.user.id
        ):
            return []
        items = await conn.fetch("SELECT name, cost FROM gang_items ORDER BY value")
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
        if not await conn.fetchval(
            "SELECT (leader OR leadership) AS is_leader FROM gang_members WHERE user_id = $1", interaction.user.id
        ):
            return []
        items = await interaction.client.pool.fetch(
            "SELECT name FROM gang_inventory JOIN gang_items gi on gang_inventory.item = gi.id "
            "WHERE gang = (SELECT gang FROM gang_members WHERE user_id = $1)",
            interaction.user.id,
        )
        return [Choice(name=i["name"], value=i["name"]) for i in items if i["name"].startswith(current)][:25]


async def try_buy_item(pool: asyncpg.Pool, user_id: int, item_name: str) -> str | int:
    """Try to buy a gang item

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
        if not await conn.fetchval(
            "SELECT (leader OR leadership) AS is_leader FROM gang_members WHERE user_id = $1", user_id
        ):
            return "You are not in the leadership of a gang, you cannot buy gang items."
        item = await conn.fetchrow("SELECT * FROM gang_items WHERE name = $1", item_name)
        if item is None:
            return f"The item `{item_name}` you requested doesn't exist."
        control: int = await conn.fetchval(
            "SELECT control FROM gangs WHERE name = (SELECT gang FROM gang_members WHERE user_id = $1)", user_id
        )
        if control < item["cost"]:
            return f"Your gang doesn't have enough control to buy that. (Have: {control}, Need: {item['cost']})"
        await conn.execute(
            "INSERT INTO gang_inventory (gang, item, quantity) VALUES "
            "((SELECT gang FROM gang_members WHERE user_id = $1), $2, 1) ON CONFLICT(gang, item) "
            "DO UPDATE SET quantity = (SELECT quantity + 1 FROM gang_inventory WHERE"
            " gang = excluded.gang AND item = excluded.item)",
            user_id,
            item["id"],
        )
        return await conn.fetchval(
            "UPDATE gangs SET control = control - $1 WHERE name = (SELECT gang FROM gang_members WHERE user_id = $2)"
            " RETURNING control",
            item["cost"],
            user_id,
        )


async def try_display_inventory(pool: asyncpg.Pool, user_id: int) -> str | ItemsView:
    """Try to display the user's gang inventory.

    Parameters
    ----------
    pool : asyncpg.Pool
        The pool.
    user_id : int
        The user's ID.

    Returns
    -------
    items : str | ItemsView
        The items, or a string error.
    """
    async with pool.acquire() as conn:
        if not await conn.fetchval(
            "SELECT (leader OR leadership) AS is_leader FROM gang_members WHERE user_id = $1", user_id
        ):
            return "You are not in the leadership of a gang, you cannot view your gang's inventory."
        items = await conn.fetch(
            "SELECT name, description, cost, quantity FROM gang_items INNER JOIN gang_inventory gi ON id = gi.item "
            "WHERE gang = (SELECT gang FROM gang_members WHERE user_id = $1)",
            user_id,
        )
        if not items:
            return "Your gang doesn't have any items."
        return ItemsView([Item(**item) for item in items], user_id)


async def try_display_available_items(pool: asyncpg.Pool, user_id: int) -> str | ItemsView:
    """Try to display the available items.

    Parameters
    ----------
    pool : asyncpg.Pool
        The pool.
    user_id : int
        The user's ID.

    Returns
    -------
    items : str | ItemsView
        The items, or a string error.
    """
    async with pool.acquire() as conn:
        if not await conn.fetchval(
            "SELECT (leader OR leadership) AS is_leader FROM gang_members WHERE user_id = $1", user_id
        ):
            return "You are not in the leadership of a gang, you cannot view the available items."
        items = await conn.fetch("SELECT name, description, cost, NULL as quantity FROM gang_items")
        if not items:
            return "There are no items available."
        return ItemsView([Item(**item) for item in items], user_id)


async def try_display_item(pool: asyncpg.Pool, user_id: int, item_name: str) -> str:
    """Try to display an item.

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
    item : str
        A string denoting the item, or an error.
    """
    async with pool.acquire() as conn:
        if not await conn.fetchval(
            "SELECT (leader OR leadership) AS is_leader FROM gang_members WHERE user_id = $1", user_id
        ):
            return "You are not in the leadership of a gang, you cannot view gang items."
        item = await conn.fetchrow(
            "SELECT name, description, cost, quantity FROM gang_items"
            " LEFT OUTER JOIN gang_inventory gi ON id = gi.item "
            "WHERE gang = (SELECT gang FROM gang_members WHERE user_id = $1) AND name = $2",
            user_id,
            item_name,
        ) or await conn.fetchrow(
            "SELECT name, description, cost, 0 as quantity FROM gang_items WHERE name = $1", item_name
        )
        if item is None:
            return f"The item `{item_name}` does not exist."
        return f"**{item['name']}**\n{item['description']}\nCost: {item['cost']}\nOwned: {item['quantity']}"


async def try_sell_item(pool: asyncpg.Pool, user_id: int, item_name: str) -> str | int:
    """Try to sell a gang item.

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
        The new amount of control, or a string error.
    """
    async with pool.acquire() as conn, conn.transaction():
        if not await conn.fetchval(
            "SELECT (leader OR leadership) AS is_leader FROM gang_members WHERE user_id = $1", user_id
        ):
            return "You are not in the leadership of a gang, you cannot sell gang items."
        gang: str = await conn.fetchval("SELECT gang FROM gang_members WHERE user_id = $1", user_id)
        item = await conn.fetchrow(
            "SELECT id, quantity, cost FROM gang_items INNER JOIN gang_inventory gi ON id = gi.item "
            "WHERE name = $1 AND gang = $2",
            item_name,
            gang,
        )
        if item is None:
            return f"Your gang doesn't have any `{item_name}` to sell, or it doesn't exist."
        if item["quantity"] == 1:
            await conn.execute("DELETE FROM gang_inventory WHERE gang = $1 AND item = $2", gang, item["id"])
        else:
            await conn.execute(
                "UPDATE gang_inventory SET quantity = quantity - 1 WHERE gang = $1 AND item = $2", gang, item["id"]
            )
        return await conn.fetchval(
            "UPDATE gangs SET control = control + $1 WHERE name = $2 RETURNING control", item["cost"] // 10, gang
        )
