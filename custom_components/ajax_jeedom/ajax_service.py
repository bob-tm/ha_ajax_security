from homeassistant.components.mqtt import async_get_platforms
from homeassistant.core import HomeAssistant
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
        #sometimes it's array, sometimes it's string
        eid = call.data["entity_id"]
        if not isinstance(eid, str):
            eid = eid[0]

        entities = {}
        for platform in async_get_platforms(hass, DOMAIN):
            entities.update(platform.entities)

        if eid in entities:
            return entities[eid]

        return None

    def getCmdForCall(call):
        c = call.data["command"]
        if "ignore_problems" in call.data:
            ip = call.data["ignore_problems"] == "yes"
        else:
            ip = False

        if c == "ARM":
            return "FORCE ARM" if ip else "ARM"

        if c == "DISARM":
            return c

        return None

    async def handle_arm_disarm(hass: HomeAssistant, call):
        groups = AjaxService.getGroupsForCall(call)
        e = AjaxService.getClassForCall(hass, call)
        cmd = AjaxService.getCmdForCall(call)

        LOGGER.debug(f"RUN {cmd} {groups} {e}")

        if e and cmd:
            ajaxDevice = e.get_ajax_device()
            haHub      = ajaxDevice.ha_Hub
            devices    = haHub.hubs[ajaxDevice.parentHubId]['devices']

            for id in groups:
                gid = f"{id:08d}"
                if gid in devices:
                    g = devices[gid]
                    # print(gid, cmd, g)
                    await g.exec_command(cmd, call.context)
