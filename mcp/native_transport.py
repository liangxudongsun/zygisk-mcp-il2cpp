"""Stdio facade for the device's native named-tool service; no target actions on import."""
from __future__ import annotations
import json
import threading
import time

class NativeToolResult(dict):
    """Already formatted MCP result; preserve isError and structured diagnostics."""

class NativeTransport:
    def __init__(self, request):
        self.request=request
        self._lock=threading.RLock()
        self._info=None
        self._at=0.0
        self._legacy=False

    def info(self, force=False):
        with self._lock:
            if self._legacy:return None
            if not force and self._info is not None and time.monotonic()-self._at<1:return self._info
            if self._info is not None:
                state=json.loads(self.request("MCP_FEATURE_STATE_V1",timeout=10.0))
                if state.get("features")==self._info["features"] and state.get("catalog_revision")==self._info.get("catalog_revision"):
                    self._at=time.monotonic();return self._info
            try:raw=self.request("MCP_SERVICE_INFO_V1",timeout=10.0)
            except Exception as exc:
                # Only a rejected read-only discovery verb enables old-module
                # fallback. Never replay a tool after transport uncertainty.
                if str(exc) in {"UNKNOWN_COMMAND","UNKNOWN_IL2CPP_COMMAND"}:
                    self._legacy=True;return None
                raise
            value=json.loads(raw)
            if not isinstance(value,dict) or value.get("protocol")!=1 or not isinstance(value.get("tools"),list) or not isinstance(value.get("features"),dict):
                raise ValueError("INVALID_NATIVE_MCP_SERVICE_INFO")
            names=[t.get("name") for t in value["tools"]]
            if any(not isinstance(n,str) or not n for n in names) or len(names)!=len(set(names)):
                raise ValueError("INVALID_NATIVE_MCP_TOOL_CATALOG")
            self._info=value;self._at=time.monotonic();return value

    def reset(self):
        with self._lock:self._info=None;self._at=0.0;self._legacy=False

    def call(self,name,arguments,target_session=None):
        request={"name":name,"arguments":arguments}
        if target_session:request["target_session"]=target_session
        raw=json.dumps(request,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode("utf-8")
        if len(raw)>4*1024*1024+8192:raise ValueError("NATIVE_TOOL_REQUEST_TOO_LARGE")
        result=json.loads(self.request("MCP_NAMED_CALL_V1 "+raw.hex(),timeout=315.0))
        if not isinstance(result,dict) or not isinstance(result.get("isError"),bool) or not isinstance(result.get("content"),list):
            raise ValueError("INVALID_NATIVE_MCP_TOOL_RESULT")
        target=result.get("structuredContent",{}).get("target_process")
        if target_session and isinstance(target,dict) and target.get("session")!=target_session:
            raise ValueError("TARGET_PROCESS_IDENTITY_CHANGED_COMMAND_NOT_REPLAYED")
        return NativeToolResult(result)

    def features(self, changes=None):
        options={"op":"get"} if changes is None else {"op":"set","features":changes}
        raw=json.dumps(options,separators=(",",":")).encode().hex()
        value=json.loads(self.request("MCP_FEATURE_CONTROL_V1 "+raw,timeout=10.0))
        if value.get("isError"):raise ValueError(value.get("content",[{}])[0].get("text","FEATURE_CONFIG_FAILED"))
        if value.get("protocol")==1 and isinstance(value.get("tools"),list) and isinstance(value.get("features"),dict):
            with self._lock:self._info=value;self._at=time.monotonic()
            return value
        with self._lock:self._info=None
        return self.info(force=True)
