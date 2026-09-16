# SPDX-License-Identifier: GPL-2.0-or-later
"""Deterministic attract/controller profile; no guessed demo or map names."""
import re

CONTROLS = '''// Generated Original Xbox/Nexuiz attract profile. Do not hand-edit generated packs.
cl_startdemos 0
joy_enable 1
joy_x360_axisforward 1
joy_x360_axisside 0
joy_x360_axisup -1
joy_x360_axispitch 3
joy_x360_axisyaw 2
joy_x360_sensitivityforward 1
joy_x360_sensitivityside 1
joy_x360_sensitivitypitch -1
joy_x360_sensitivityyaw -1
joy_x360_deadzoneforward 0.266
joy_x360_deadzoneside 0.266
joy_x360_deadzonepitch 0.266
joy_x360_deadzoneyaw 0.266
xbox_demo_loadtimeout 60
bind X360_A "+jump"
bind X360_B "+crouch"
bind X360_X "dropweapon"
bind X360_Y "weaplast"
bind X360_LEFT_TRIGGER "+attack2"
bind X360_RIGHT_TRIGGER "+attack"
bind X360_LEFT_SHOULDER "weapprev"
bind X360_RIGHT_SHOULDER "weapnext"
bind X360_LEFT_THUMB "+hook"
bind X360_RIGHT_THUMB "+zoom"
bind X360_DPAD_UP "+showscores"
bind X360_DPAD_DOWN "+show_info"
bind X360_DPAD_LEFT "weapprev"
bind X360_DPAD_RIGHT "weapnext"
bind X360_START "togglemenu"
bind X360_BACK "togglemenu"
'''

def build_config(selected_paths: list[str], demos: list[str] | None = None,
                 require: bool = False) -> tuple[list[str], bytes | None]:
    """Use explicit order when supplied, otherwise sorted selected .dem paths."""
    available = set(selected_paths)
    names = list(demos) if demos is not None else sorted(p for p in selected_paths if p.endswith('.dem'))
    if not names:
        if require:
            raise ValueError('autoplay requires at least one selected demo (.dem) file')
        return [], None
    if len(names) > 8 or len(names) != len(set(names)):
        raise ValueError('autoplay requires 1 to 8 unique demos; choose an explicit --demo list')
    for name in names:
        if (name not in available or len(name) >= 128 or not re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9_./-]*\.dem', name)
                or '..' in name or '//' in name or '/./' in name):
            raise ValueError(f'invalid or unselected autoplay demo: {name!r}')
    command = 'xbox_demo_playlist ' + ' '.join('"' + name + '"' for name in names) + '\n'
    if len(command) >= 1024:  # DP_SMALLMEMORY MAX_INPUTLINE, including terminator.
        raise ValueError('autoplay playlist exceeds the 1024-byte small-memory command limit')
    config = CONTROLS + command
    return names, config.encode('ascii')
