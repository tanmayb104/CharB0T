# -*- coding: utf-8 -*-
#  ----------------------------------------------------------------------------
#  MIT License
#
# Copyright (c) 2022 Bluesy
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#  ----------------------------------------------------------------------------
"""Admin commands for the reputation system."""
from functools import partial
from io import BytesIO
from typing import Callable, Literal

import asyncpg
import discord
from card import generate_card
from discord import Interaction, app_commands
from discord.ext import commands
from discord.utils import MISSING

from main import CBot


_ALLOWED_MENTIONS = discord.AllowedMentions(roles=False, users=False, everyone=False)


# noinspection PyAbstractClass
class TextChannelOnly(app_commands.Transformer):
    """Transformer that only allows text channels."""

    @classmethod
    def channel_types(cls) -> list[discord.ChannelType]:
        """Return the channel types that are allowed.

        Returns
        -------
        list[discord.ChannelType]
            The channel types that are allowed.
        """
        return [
            discord.ChannelType.text,
            discord.ChannelType.news,
            discord.ChannelType.news_thread,
            discord.ChannelType.public_thread,
            discord.ChannelType.private_thread,
        ]

    @classmethod
    def type(cls) -> discord.AppCommandOptionType:
        """Return the type of the transformer.

        Returns
        -------
        discord.AppCommandOptionType
            The type of the transformer.
        """
        return discord.AppCommandOptionType.channel

    @classmethod
    async def transform(
        cls, interaction: discord.Interaction, value: app_commands.AppCommandChannel  # skipcq: PYL-W0613
    ) -> app_commands.AppCommandChannel:
        """Transform the value.

        It actually doesn't, but we've got to pretend it does.

        Parameters
        ----------
        interaction: discord.Interaction
            The interaction object for the message.
        value: app_commands.AppCommandChannel
            The value to "transform".

        Returns
        -------
        app_commands.AppCommandChannel
            The "transformed" value.
        """
        return value


@app_commands.default_permissions(manage_messages=True)
@app_commands.guilds(225345178955808768)
@app_commands.checks.has_any_role(225413350874546176, 253752685357039617, 725377514414932030, 338173415527677954)
class ReputationAdmin(
    commands.GroupCog, name="administration", description="Administration commands for the reputation system."
):
    """Reputation Admin Commands.

    These commands are used to manage the reputation system.

    Parameters
    ----------
    bot : CBot
        The bot object.
    """

    def __init__(self, bot: CBot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name="Check User's Reputation",
            callback=self.check_reputation_context,
        )
        self.bot.tree.add_command(self.ctx_menu)

        # noinspection PyUnusedLocal
        @self.edit_pool.autocomplete("pool")
        @self.pool_role.autocomplete("pool")
        @self.check_pool.autocomplete("pool")
        @self.delete_pool.autocomplete("pool")
        async def pool_autocomplete(
            interaction: Interaction, current: str  # skipcq: PYL-W0613
        ) -> list[app_commands.Choice[str]]:
            """Autocomplete a pool name.

            Parameters
            ----------
            interaction : Interaction
                The interaction object.
            current : str
                The current string.

            Returns
            -------
            list[app_commands.Choice[str]]
                The list of choices.
            """
            return [
                app_commands.Choice(name=pool["pool"], value=pool["pool"])
                for pool in await self.bot.pool.fetch("SELECT pool FROM pools")
                if current.lower() in pool["pool"].lower()
            ]

    async def cog_unload(self) -> None:
        """Unload the cog."""
        self.bot.tree.remove_command(
            self.ctx_menu.name, type=self.ctx_menu.type, guild=discord.Object(id=225345178955808768)
        )

    pools = app_commands.Group(name="pools", description="Administration commands for the reputation pools.")
    reputation = app_commands.Group(name="reputation", description="Administration commands for the reputation system.")

    @pools.command(name="create", description="Create a new reputation pool.")
    async def create_pool(
        self,
        interaction: Interaction,
        name: str,
        capacity: int,
        reward: str,
        role: discord.Role,
        level: app_commands.Range[int, 1] = 1,
        current: app_commands.Range[int, 0] = 0,
        start: app_commands.Range[int, 0] = 0,
        role1: discord.Role = MISSING,
        role2: discord.Role = MISSING,
        role3: discord.Role = MISSING,
        role4: discord.Role = MISSING,
        role5: discord.Role = MISSING,
        role6: discord.Role = MISSING,
        role7: discord.Role = MISSING,
        role8: discord.Role = MISSING,
        role9: discord.Role = MISSING,
        role10: discord.Role = MISSING,
        role11: discord.Role = MISSING,
        role12: discord.Role = MISSING,
        role13: discord.Role = MISSING,
        role14: discord.Role = MISSING,
        role15: discord.Role = MISSING,
        role16: discord.Role = MISSING,
        role17: discord.Role = MISSING,
        role18: discord.Role = MISSING,
        role19: discord.Role = MISSING,
    ):
        """Create a new reputation pool.

        Parameters
        ----------
        interaction : Interaction
            The interaction to use.
        name : str
            The name of the pool. Must be unique.
        capacity : int
            How many reputation points the pool can hold.
        reward : str
            The reward for completing the pool. Max 100 characters.
        role : discord.Role
            A role to whitelist to participate in the pool. role1 to 19 allow additional roles to participate.
        level : app_commands.Range[int, 1]
            Level of the pool. Default is 1. If set to a number other than 1, current and start are required.
        current : app_commands.Range[int, 0]
            The current reputation points in the pool. Default is 0. Must be above 0 if level is not 1
        start : app_commands.Range[int, 0]
            The base reputation for the pool level. Default is 0. Must be above 0 if level is not 1
        role1 : discord.Role
            [OPTIONAL] Additional slot for a role to whitelist to participate in the pool.
        role2 : discord.Role
            [OPTIONAL] Additional slot for a role to whitelist to participate in the pool.
        role3 : discord.Role
            [OPTIONAL] Additional slot for a role to whitelist to participate in the pool.
        role4 : discord.Role
            [OPTIONAL] Additional slot for a role to whitelist to participate in the pool.
        role5 : discord.Role
            [OPTIONAL] Additional slot for a role to whitelist to participate in the pool.
        role6 : discord.Role
            [OPTIONAL] Additional slot for a role to whitelist to participate in the pool.
        role7 : discord.Role
            [OPTIONAL] Additional slot for a role to whitelist to participate in the pool.
        role8 : discord.Role
            [OPTIONAL] Additional slot for a role to whitelist to participate in the pool.
        role9 : discord.Role
            [OPTIONAL] Additional slot for a role to whitelist to participate in the pool.
        role10 : discord.Role
            [OPTIONAL] Additional slot for a role to whitelist to participate in the pool.
        role11 : discord.Role
            [OPTIONAL] Additional slot for a role to whitelist to participate in the pool.
        role12 : discord.Role
            [OPTIONAL] Additional slot for a role to whitelist to participate in the pool.
        role13 : discord.Role
            [OPTIONAL] Additional slot for a role to whitelist to participate in the pool.
        role14 : discord.Role
            [OPTIONAL] Additional slot for a role to whitelist to participate in the pool.
        role15 : discord.Role
            [OPTIONAL] Additional slot for a role to whitelist to participate in the pool.
        role16 : discord.Role
            [OPTIONAL] Additional slot for a role to whitelist to participate in the pool.
        role17 : discord.Role
            [OPTIONAL] Additional slot for a role to whitelist to participate in the pool.
        role18 : discord.Role
            [OPTIONAL] Additional slot for a role to whitelist to participate in the pool.
        role19 : discord.Role
            [OPTIONAL] Additional slot for a role to whitelist to participate in the pool.
        """
        if level != 1 and (current == 0 or start == 0):
            await interaction.response.send_message(
                "Error: Level is not 1, but current and start are not set.", ephemeral=True
            )
            return
        if len(name) > 32:
            await interaction.response.send_message("Error: Name must be 32 characters or less.", ephemeral=True)
            return
        if len(reward) > 100:
            await interaction.response.send_message("Error: Reward must be 100 characters or less.", ephemeral=True)
            return
        async with self.bot.pool.acquire() as conn, conn.transaction():
            _pool = await conn.fetchrow("SELECT * FROM pools WHERE pool = $1", name)
            if _pool is not None:
                await interaction.response.send_message("Error: Pool already exists.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            roles = [role.id]
            # noinspection DuplicatedCode
            if role1 is not MISSING and role1.id not in roles:
                roles.append(role1.id)
            if role2 is not MISSING and role2.id not in roles:
                roles.append(role2.id)
            if role3 is not MISSING and role3.id not in roles:
                roles.append(role3.id)
            if role4 is not MISSING and role4.id not in roles:
                roles.append(role4.id)
            if role5 is not MISSING and role5.id not in roles:
                roles.append(role5.id)
            if role6 is not MISSING and role6.id not in roles:
                roles.append(role6.id)
            if role7 is not MISSING and role7.id not in roles:
                roles.append(role7.id)
            if role8 is not MISSING and role8.id not in roles:
                roles.append(role8.id)
            if role9 is not MISSING and role9.id not in roles:
                roles.append(role9.id)
            # noinspection DuplicatedCode
            if role10 is not MISSING and role10.id not in roles:
                roles.append(role10.id)
            if role11 is not MISSING and role11.id not in roles:
                roles.append(role11.id)
            if role12 is not MISSING and role12.id not in roles:
                roles.append(role12.id)
            if role13 is not MISSING and role13.id not in roles:
                roles.append(role13.id)
            if role14 is not MISSING and role14.id not in roles:
                roles.append(role14.id)
            if role15 is not MISSING and role15.id not in roles:
                roles.append(role15.id)
            if role16 is not MISSING and role16.id not in roles:
                roles.append(role16.id)
            if role17 is not MISSING and role17.id not in roles:
                roles.append(role17.id)
            if role18 is not MISSING and role18.id not in roles:
                roles.append(role18.id)
            if role19 is not MISSING and role19.id not in roles:
                roles.append(role19.id)
            await conn.execute(
                "INSERT INTO pools (pool, cap, reward, required_roles, level, current, start)"
                " VALUES ($1, $2, $3, $4, $5, $6, $7)",
                name,
                capacity,
                reward,
                roles,
                level,
                current,
                start,
            )
            _partial_image: Callable[[], BytesIO] = partial(
                generate_card, level=level, base_rep=start, current_rep=current, completed_rep=capacity, pool_name=name
            )
            image_bytes = await self.bot.loop.run_in_executor(None, _partial_image)
            image = discord.File(image_bytes, f"{name}.png")
            await interaction.followup.send(f"Pool {name} created with reward {reward}!", file=image)
            clientuser = self.bot.user
            assert isinstance(clientuser, discord.ClientUser)  # skipcq: BAN-B101
            await self.bot.program_logs.send(
                f"Pool {name} created with reward {reward} by {interaction.user.mention}.",
                allowed_mentions=_ALLOWED_MENTIONS,
                username=clientuser.name,
                avatar_url=clientuser.display_avatar.url,
            )

    @pools.command(name="edit", description="Edits a pool.")
    async def edit_pool(
        self,
        interaction: Interaction,
        pool: str,
        name: str = MISSING,
        capacity: app_commands.Range[int, 0] = 0,
        reward: str = MISSING,
        level: app_commands.Range[int, 1] = 1,
        current: app_commands.Range[int, 0] = 0,
        start: app_commands.Range[int, 0] = 0,
    ):
        """Edit a pool. Options left out will not be changed.

        Parameters
        ----------
        interaction : Interaction
            The interaction object.
        pool : str
            The name of the pool to edit. Use the autocomplete feature to find the pool.
        name : str
            The new name of the pool. Must be 32 characters or fewer.
        capacity : int
            The new capacity of the pool.
        reward : str
            The new reward of the pool. mMst be 100 characters or fewer.
        level : int
            The new level of the pool. Must be at least 1.
        current : int
            The new current rep of the pool. Must be at least 0 and set above 0 if level is 1.
        start : int
            The new base rep for the pool level. Must be at least 0 and set above 0 if level is 1.
        """
        if level != 1 and 0 in (current, start):
            await interaction.response.send_message(
                "Error: Current and start must be greater than 0 if level is 1.", ephemeral=True
            )
            return
        if name is not MISSING and len(name) > 32:
            await interaction.response.send_message("Error: Name must be 32 characters or less.", ephemeral=True)
            return
        if reward is not MISSING and len(reward) > 100:
            await interaction.response.send_message("Error: Reward must be 100 characters or less.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        async with self.bot.pool.acquire() as conn, conn.transaction():
            _pool = await conn.fetchrow("SELECT * FROM pools WHERE pool = $1", pool)
            if _pool is None:
                await interaction.followup.send(
                    f"Error: Pool `{pool}` not found. Use the autocomplete feature to find the pool."
                )
            else:
                if name is not MISSING:
                    await conn.execute("UPDATE pools SET pool = $1 WHERE pool = $2", name, pool)
                if capacity != 0:
                    await conn.execute("UPDATE pools SET cap = $1 WHERE pool = $2", capacity, pool)
                if reward is not MISSING:
                    await conn.execute("UPDATE pools SET reward = $1 WHERE pool = $2", reward, pool)
                if level != 1:
                    await conn.execute("UPDATE pools SET level = $1 WHERE pool = $2", level, pool)
                if current != 0:
                    await conn.execute("UPDATE pools SET current = $1 WHERE pool = $2", current, pool)
                if start != 0:
                    await conn.execute("UPDATE pools SET start = $1 WHERE pool = $2", start, pool)

                _pool = await conn.fetchrow("SELECT * FROM pools WHERE pool = $1", name)
                assert isinstance(_pool, asyncpg.Record)  # skipcq: BAN-B101
                _partial_image: Callable[[], BytesIO] = partial(
                    generate_card,
                    level=_pool["level"],
                    base_rep=_pool["start"],
                    current_rep=_pool["current"],
                    completed_rep=_pool["cap"],
                    pool_name=_pool["pool"],
                )
                image_bytes = await self.bot.loop.run_in_executor(None, _partial_image)
                image = discord.File(image_bytes, f"{_pool['pool']}.png")
                await interaction.followup.send(
                    f"Pool {_pool['pool']}{f' (formerly {pool})' if name is not MISSING else ''} edited!", file=image
                )
                clientuser = self.bot.user
                assert isinstance(clientuser, discord.ClientUser)  # skipcq: BAN-B101
                await self.bot.program_logs.send(
                    f"Pool {_pool['pool']}{f' (formerly {pool})' if name is not MISSING else ''}"
                    f" edited by {interaction.user.mention}.",
                    allowed_mentions=_ALLOWED_MENTIONS,
                    username=clientuser.name,
                    avatar_url=clientuser.display_avatar.url,
                )

    @pools.command(name="list", description="Lists all pools.")
    async def list_pools(self, interaction: Interaction):
        """List all pools.

        Parameters
        ----------
        interaction : Interaction
            The interaction object.
        """
        await interaction.response.defer(ephemeral=True)
        async with self.bot.pool.acquire() as conn:
            pools = [pool["pool"] for pool in await conn.fetch("SELECT pool FROM pools")]
            await interaction.followup.send(f"Pools: {', '.join(pools)}")

    @pools.command(name="role", description="Toggles a roles ability to participate in a pool.")
    async def pool_role(self, interaction: Interaction, pool: str, role: discord.Role):
        """Toggle a role's ability to participate in a pool.

        Parameters
        ----------
        interaction : Interaction
            The interaction object.
        pool : str
            The name of the pool. Use the autocomplete feature to find the pool.
        role : discord.Role
            The role to toggle.
        """
        await interaction.response.defer(ephemeral=True)
        clientuser = self.bot.user
        assert isinstance(clientuser, discord.ClientUser)  # skipcq: BAN-B101
        async with self.bot.pool.acquire() as conn, conn.transaction():
            _pool = await conn.fetchrow("SELECT * FROM pools WHERE pool = $1", pool)
            if _pool is None:
                await interaction.followup.send(f"Error: Pool `{pool}` not found.")
            else:
                if role.id in _pool["required_roles"]:
                    await conn.execute(
                        "UPDATE pools SET required_roles = array_remove(required_roles, $1) WHERE pool = $2",
                        role.id,
                        pool,
                    )
                    await interaction.followup.send(f"Role `{role.name}` removed from pool `{pool}`.")
                    await self.bot.program_logs.send(
                        f"Role `{role.name}` removed from pool `{pool}` by {interaction.user.mention}.",
                        allowed_mentions=_ALLOWED_MENTIONS,
                        username=clientuser.name,
                        avatar_url=clientuser.display_avatar.url,
                    )
                else:
                    await conn.execute(
                        "UPDATE pools SET required_roles = array_append(required_roles, $1) WHERE pool = $2",
                        role.id,
                        pool,
                    )
                    await interaction.followup.send(f"Role `{role.name}` added to pool `{pool}`.")
                    await self.bot.program_logs.send(
                        f"Role `{role.name}` added to pool `{pool}` by {interaction.user.mention}.",
                        allowed_mentions=_ALLOWED_MENTIONS,
                        username=clientuser.name,
                        avatar_url=clientuser.display_avatar.url,
                    )

    @pools.command(name="delete", description="Deletes a pool.")
    async def delete_pool(self, interaction: Interaction, pool: str):
        """Delete a pool.

        Parameters
        ----------
        interaction : Interaction
            The interaction object.
        pool : str
            The name of the pool. Use the autocomplete feature to find the pool.
        """
        await interaction.response.defer(ephemeral=True)
        async with self.bot.pool.acquire() as conn, conn.transaction():
            _pool = await conn.fetchrow("SELECT * FROM pools WHERE pool = $1", pool)
            if _pool is None:
                await interaction.followup.send(f"Error: Pool `{pool}` not found.")
            else:
                await conn.execute("DELETE FROM pools WHERE pool = $1", pool)
                await interaction.followup.send(f"Pool `{pool}` deleted.")
                clientuser = self.bot.user
                assert isinstance(clientuser, discord.ClientUser)  # skipcq: BAN-B101
                await self.bot.program_logs.send(
                    f"Pool `{pool}` deleted by {interaction.user.mention}.",
                    allowed_mentions=_ALLOWED_MENTIONS,
                    username=clientuser.name,
                    avatar_url=clientuser.display_avatar.url,
                )

    @pools.command(name="check", description="Checks a pool.")
    async def check_pool(self, interaction: Interaction, pool: str):
        """Check a pool.

        Parameters
        ----------
        interaction : Interaction
            The interaction object.
        pool : str
            The name of the pool. Use the autocomplete feature to find the pool.
        """
        await interaction.response.defer(ephemeral=True)
        async with self.bot.pool.acquire() as conn:
            _pool = await conn.fetchrow("SELECT * FROM pools WHERE pool = $1", pool)
            if _pool is None:
                await interaction.followup.send(f"Error: Pool `{pool}` not found.")
            else:
                completed = round(_pool["current"] / _pool["cap"], 2)
                status: Literal["online", "offline", "idle", "streaming", "dnd"] = "offline"
                if completed < 0.34:
                    status = "dnd"
                elif 0.34 <= completed < 0.67:
                    status = "idle"
                elif 0.67 <= completed < 1:
                    status = "streaming"
                elif completed == 1:
                    status = "online"
                _partial_image: Callable[[], BytesIO] = partial(
                    generate_card,
                    level=_pool["level"],
                    base_rep=_pool["start"],
                    current_rep=_pool["current"],
                    completed_rep=_pool["cap"],
                    pool_name=pool,
                    pool_status=status,
                )
                image_bytes = await self.bot.loop.run_in_executor(None, _partial_image)
                image = discord.File(image_bytes, f"{_pool['pool']}.png")
                await interaction.followup.send(
                    f"Pool `{pool}`: {_pool['level']} level pool with {_pool['start']} base rep, {_pool['current']}"
                    f" current rep, {_pool['cap']} completed rep, and {_pool['reward']} reward. "
                    f"and allowed for roles: <@{'>, <@&'.join(_pool['required_roles'])}>",
                    file=image,
                )

    @reputation.command(name="add", description="Adds reputation to a user.")
    async def add_reputation(self, interaction: Interaction, user: discord.User, amount: int):
        """Add reputation to a user.

        Parameters
        ----------
        interaction : Interaction
            The interaction object.
        user : discord.User
            The user to add reputation to.
        amount : int
            The amount of reputation to add.
        """
        await interaction.response.defer(ephemeral=True)
        async with self.bot.pool.acquire() as conn, conn.transaction():
            _user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user.id)
            if _user is None:
                await interaction.followup.send(f"Error: User `{user.name}` not found as active.")
            else:
                new_points: int = await conn.fetchval(
                    "UPDATE users SET points = points + $1 WHERE id = $2 RETURNING points", amount, user.id
                )
                await interaction.followup.send(f"User `{user.name}` now has {new_points} reputation.")
                clientuser = self.bot.user
                assert isinstance(clientuser, discord.ClientUser)  # skipcq: BAN-B101
                await self.bot.program_logs.send(
                    f"{user.mention} now has {new_points} reputation by {interaction.user.mention} ({amount} added).",
                    allowed_mentions=_ALLOWED_MENTIONS,
                    username=clientuser.name,
                    avatar_url=clientuser.display_avatar.url,
                )

    @reputation.command(name="remove", description="Removes reputation from a user.")
    async def remove_reputation(self, interaction: Interaction, user: discord.User, amount: int):
        """Remove reputation from a user.

        Parameters
        ----------
        interaction : Interaction
            The interaction object.
        user : discord.User
            The user to remove reputation from.
        amount : int
            The amount of reputation to remove.
        """
        await interaction.response.defer(ephemeral=True)
        async with self.bot.pool.acquire() as conn, conn.transaction():
            _user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user.id)
            if _user is None:
                await interaction.followup.send(f"Error: User `{user.name}` not found as active.")
            else:
                if amount > _user["points"]:
                    overflow = amount - _user["points"]
                    amount = _user["points"]
                else:
                    overflow = 0
                new_points: int = await conn.fetchval(
                    "UPDATE users SET points = points - $1 WHERE id = $2 RETURNING points", amount, user.id
                )
                await interaction.followup.send(
                    f"User `{user.name}` now has {new_points} reputation. {overflow} reputation overflow."
                )
                clientuser = self.bot.user
                assert isinstance(clientuser, discord.ClientUser)  # skipcq: BAN-B101
                await self.bot.program_logs.send(
                    f"{user.mention} now has {new_points} reputation by {interaction.user.mention} ({amount} removed).",
                    allowed_mentions=_ALLOWED_MENTIONS,
                    username=clientuser.name,
                    avatar_url=clientuser.display_avatar.url,
                )

    @reputation.command(name="check", description="Checks a user's reputation.")
    async def check_reputation(self, interaction: Interaction, user: discord.User):
        """Check a user's reputation.

        Parameters
        ----------
        interaction : Interaction
            The interaction object.
        user : discord.User
            The user to check.
        """
        await interaction.response.defer(ephemeral=True)
        async with self.bot.pool.acquire() as conn:
            _user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user.id)
            if _user is None:
                await interaction.followup.send(f"Error: User `{user.name}` not found as active.")
            else:
                await interaction.followup.send(f"User `{user.name}` has {_user['points']} reputation.")

    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guilds(225345178955808768)
    @app_commands.checks.has_any_role(225413350874546176, 253752685357039617, 725377514414932030, 338173415527677954)
    async def check_reputation_context(self, interaction: Interaction, user: discord.User):
        """Check a user's reputation.

        Parameters
        ----------
        interaction : Interaction
            The interaction object.
        user : discord.User
            The user to check.
        """
        await interaction.response.defer(ephemeral=True)
        async with self.bot.pool.acquire() as conn:
            _user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user.id)
            if _user is None:
                await interaction.followup.send(f"Error: User `{user.name}` not found as active.")
            else:
                await interaction.followup.send(f"User `{user.name}` has {_user['points']} reputation.")


async def setup(bot: CBot):
    """Initialize the cog."""
    await bot.add_cog(ReputationAdmin(bot))
