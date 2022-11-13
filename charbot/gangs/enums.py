# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2022 Bluesy1 <68259537+Bluesy1@users.noreply.github.com>
#
# SPDX-License-Identifier: MIT

import enum


class Benefits(enum.Enum):
    control = "control"
    control_consumable = "control_consumable"
    defense = "defense"
    defense_consumable = "defense_consumable"
    offense = "offense"
    offense_consumable = "offense_consumable"
    other = "other"
    other_consumable = "other"
