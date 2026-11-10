import json
import urllib.parse

import aiohttp

quoteurl = urllib.parse.quote


# import locale


class JeedomAjaxApi:
    last_exec_error = ""

    def __init__(self, session, adrss, url, apiKey):
        self.session = session
        self.adrss = adrss + url
        self.apiKey = apiKey
        self.userId = False

    async def isOk(self):
        params = {"ha_direct_call": "get_userId"}
        r = await self.CallJeedomAjaxApi(params)
        if r and "test" in r:
            return r["test"] == "ok"
        else:
            return False

    async def get_userId(self):
        params = {"ha_direct_call": "get_userId"}
        r = await self.CallJeedomAjaxApi(params)
        if r and "userId" in r:
            self.userId = r["userId"]
            return self.userId
        else:
            return False

    async def get_config_json(self, path):
        if self.userId:
            return await self.exec_cmd(f"/user/{self.userId}/{path}", {}, "GET")
        else:
            return False

    async def exec_cmd(self, path, data, call_method):
        self.last_exec_error = ""
        params = {
            "ha_direct_call": "AjaxApi",
            "a_path": path,
            "a_data": data,
            "a_type": call_method,
        }

        r = await self.CallJeedomAjaxApi(params)
        if r:
            if "result" in r:
                return r["result"]

            if "exception" in r:
                self.last_exec_error = r["exception"]

        return False

    async def CallJeedomAjaxApi(self, params):
        params["apikey"] = self.apiKey
        data = json.dumps(params)

        try:
            async with self.session.post(
                self.adrss,
                data=data,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    return await response.json()

                self.last_exec_error = f"Jeedom returned HTTP {response.status}"
        except TimeoutError:
            self.last_exec_error = "Timed out waiting for Jeedom API response"
        except aiohttp.ClientError as err:
            self.last_exec_error = f"aiohttp: {err}"

        return None
