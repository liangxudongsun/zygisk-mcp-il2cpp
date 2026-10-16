"""No device access: native facade contract, uncertainty and shared switches."""
import json
import unittest
from unittest.mock import patch
from mcp import native_transport as n,mcp_server as s

class RootService:
    def __init__(self):self.features={};self.calls=[];self.fail=False
    def __call__(self,command,**kwargs):
        self.calls.append(command)
        if command=='MCP_FEATURE_STATE_V1':return json.dumps({'features':self.features})
        if command=='MCP_SERVICE_INFO_V1':
            return json.dumps({'protocol':1,'features':self.features,'tools':[s.TOOL_BY_NAME['frida_script']] if self.features.get('frida',True) else []})
        if command.startswith('MCP_FEATURE_CONTROL_V1 '):
            self.features.update(json.loads(bytes.fromhex(command.split()[1])).get('features',{}))
            return self('MCP_SERVICE_INFO_V1')
        if self.fail:raise OSError('completion unknown')
        value=json.loads(bytes.fromhex(command.split()[1]));data={'pending':False,'success':False,'error':'TEST_FAILURE','request_id':42}
        return json.dumps({'content':[{'type':'text','text':'TEST_FAILURE'}],'isError':True,'structuredContent':data})

class NativeTransportTests(unittest.TestCase):
    def test_exact_tool_results_and_no_mutation_replay(self):
        root=RootService();transport=n.NativeTransport(root);transport.info()
        result=transport.call('workspace_result',{'request_id':42})
        self.assertTrue(result['isError']);self.assertEqual(result['structuredContent']['request_id'],42)
        self.assertEqual(s.McpServer._tool_result(result),result)
        root.fail=True;before=len(root.calls)
        with self.assertRaises(OSError):transport.call('memory_write',{'address':'0x1000','hex_bytes':'00'})
        self.assertEqual(len(root.calls),before+1);self.assertFalse(transport._legacy)

    def test_only_explicit_unknown_discovery_enables_legacy(self):
        for text in ('UNKNOWN_COMMAND','UNKNOWN_IL2CPP_COMMAND'):
            transport=n.NativeTransport(lambda *a,**k:(_ for _ in ()).throw(s.BridgeError(text)))
            self.assertIsNone(transport.info());self.assertTrue(transport._legacy)
        transport=n.NativeTransport(lambda *a,**k:(_ for _ in ()).throw(OSError('lost')))
        with self.assertRaises(OSError):transport.info()
        self.assertFalse(transport._legacy)

    def test_registry_uses_same_phone_state_and_updates_admin(self):
        root=RootService();root.features={'frida':False}
        transport=n.NativeTransport(root);registry=s.FeatureRegistry();registry.bind_remote(transport)
        updates=[];registry.subscribe(lambda:updates.append(True));registry.refresh_remote()
        self.assertFalse(registry.enabled('frida'));self.assertTrue(updates)
        registry.set('frida',True);self.assertTrue(root.features['frida']);self.assertTrue(registry.enabled('frida'))
        registry.set_all(False);self.assertFalse(any(root.features.values()))

    def test_long_frida_request_is_not_rejected_by_legacy_socket_limit(self):
        from mcp import analysis_tools
        command=analysis_tools.encode('frida_script',{'op':'load','source':'x'*49152})
        client=s.HookSocketClient(s.ConnectionConfig(auto_adb_forward=False))
        with patch.object(s.socket,'create_connection',side_effect=OSError('offline')) as connect:
            with self.assertRaises(s.BridgeError):client.call(command)
            self.assertTrue(connect.called)

    def test_legacy_failed_task_keeps_diagnostics_and_is_error(self):
        value={'pending':False,'success':False,'error':'FAILED','request_id':42}
        result=s.McpServer._tool_result(value)
        self.assertTrue(result['isError']);self.assertEqual(result['structuredContent'],value)

    def test_cli_defaults_to_device_facade_and_has_explicit_old_mode(self):
        self.assertFalse(s.parse_args([]).legacy_tools)
        self.assertTrue(s.parse_args(['--legacy-tools']).legacy_tools)

    def test_unchanged_state_poll_does_not_download_catalog_again(self):
        root=RootService();transport=n.NativeTransport(root);transport.info()
        transport.info(force=True)
        self.assertEqual(root.calls.count('MCP_SERVICE_INFO_V1'),1)
        self.assertEqual(root.calls[-1],'MCP_FEATURE_STATE_V1')

    def test_identity_mismatch_is_not_accepted_or_replayed(self):
        def request(*a,**k):return json.dumps({'content':[],'isError':False,'structuredContent':{'target_process':{'session':'new'}}})
        transport=n.NativeTransport(request)
        with self.assertRaisesRegex(ValueError,'IDENTITY_CHANGED'):
            transport.call('memory_write',{'address':'0x1000','hex_bytes':'00'},'old')

if __name__=='__main__':unittest.main()
