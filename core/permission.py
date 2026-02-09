# -*- coding: utf-8 -*-
"""Check API permission against CallContext (groups only)."""

from __future__ import annotations

from .types import CallContext


def check_permission(
    api: dict,
    ctx: CallContext,
    groups: dict | None = None,
) -> tuple[bool, str]:
    """
    Only require_admin, allowed_user_groups, allowed_group_groups are used.
    allowed_users / allowed_groups in api are ignored.
    groups: {"user_groups": {name: [uid,...]}, "group_groups": {name: [gid,...]}}.
    """
    groups = groups or {}
    user_groups = groups.get("user_groups") or {}
    group_groups = groups.get("group_groups") or {}

    if api.get("require_admin") is True and not ctx.is_admin:
        return False, "需要管理员权限。"

    allowed_user_groups = api.get("allowed_user_groups") or []
    if allowed_user_groups and ctx.user_id is not None:
        user_in_any = False
        for gname in allowed_user_groups:
            members = user_groups.get(gname)
            if isinstance(members, list) and ctx.user_id in [str(m) for m in members]:
                user_in_any = True
                break
        if not user_in_any:
            return False, "你不在该 API 的允许用户组中。"

    allowed_group_groups = api.get("allowed_group_groups") or []
    if allowed_group_groups:
        if ctx.group_id is None:
            return False, "该接口仅限群聊使用。"
        group_in_any = False
        for gname in allowed_group_groups:
            members = group_groups.get(gname)
            if isinstance(members, list) and ctx.group_id in [str(m) for m in members]:
                group_in_any = True
                break
        if not group_in_any:
            return False, "当前群不在该 API 的允许群组中。"

    return True, ""
