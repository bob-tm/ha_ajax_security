from homeassistant.components.mqtt import async_get_platforms
from .const import DOMAIN, LOGGER


class AjaxService:
    def getGroupsForCall(call):
        groups = call.data["groups"]
        result = []
        if isinstance(groups, int):
            result.append(groups)
        elif isinstance(groups, str):
            x = groups.strip().split(",")
            for g in x:
                result.append(int(g.strip()))
        else:
            for g in groups:
                result.append(int(g))

        return result

    def getClassForCall(hass, call):
        eid = call.data["entity_id"]
        entities = {}
        for platform in async_get_platforms(hass, DOMAIN):
            entities.update(platform.entities)

        if eid in entities:
            return entities[eid]

    def getCmdForCall(call):
        c = call.data["command"]
        if "ignore_problems" in call.data:
            ip = call.data["ignore_problems"] == "yes"
        else:
            ip = False

        if c == "ARM":
            return "FORCE ARM" if ip else "ARM"
        elif c == "DISARM":
            return c
        else:
            return None

    async def handle_arm_disarm(hass, call):
        groups = AjaxService.getGroupsForCall(call)
        e = AjaxService.getClassForCall(hass, call)
        cmd = AjaxService.getCmdForCall(call)

        LOGGER.debug(f"RUN {cmd} {groups} {e}")

        if e and cmd:
            hub = e.get_ajax_device().ha_Hub

            for id in groups:
                gid = f"{id:08d}"
                if gid in hub.devices:
                    g = hub.devices[gid]
                    # print(gid, cmd, g)
                    await g.exec_command(cmd)
