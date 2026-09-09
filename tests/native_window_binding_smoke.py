from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cws_viewer.backends.native_window import bind_neutral_window, capsule_pointer

class IntegerWindow:
    def SetNativeHandle(self, handle):
        if not isinstance(handle,int): raise TypeError('integer ABI')
        self.handle=handle
    def NativeHandle(self): return self.handle
class CapsuleWindow:
    def SetNativeHandle(self,handle):
        if isinstance(handle,int): raise TypeError('capsule ABI')
        self.handle=handle
    def NativeHandle(self): return self.handle
class NativeWindowBindingTests(unittest.TestCase):
    def test_integer_abi(self):
        window=IntegerWindow()
        self.assertEqual(bind_neutral_window(window,0x123456),0x123456)
        self.assertEqual(window.NativeHandle(),0x123456)
    def test_capsule_abi(self):
        window=CapsuleWindow()
        capsule=bind_neutral_window(window,0x123456)
        self.assertEqual(capsule_pointer(capsule),0x123456)
        self.assertIs(window.NativeHandle(),capsule)
    def test_invalid_handles_fail_before_call(self):
        for value in (0,-1,True,2**256,1.5,'12'):
            with self.subTest(value=value),self.assertRaises((ValueError,TypeError)):
                bind_neutral_window(IntegerWindow(),value)
    def test_native_failure_is_not_swallowed(self):
        class Broken(IntegerWindow):
            def SetNativeHandle(self,handle): raise RuntimeError('driver failure')
        with self.assertRaisesRegex(RuntimeError,'driver failure'):
            bind_neutral_window(Broken(),42)
    def test_wrong_readback_is_not_success(self):
        class Wrong(IntegerWindow):
            def NativeHandle(self): return self.handle+1
        with self.assertRaisesRegex(RuntimeError,'verified'):
            bind_neutral_window(Wrong(),42)
    def test_installed_native_ocp_integer_or_capsule_binding(self):
        from OCP.Aspect import Aspect_NeutralWindow
        window=Aspect_NeutralWindow()
        bind_neutral_window(window,0x123456)
        value=window.NativeHandle()
        self.assertEqual(value if isinstance(value,int) else capsule_pointer(value),0x123456)

if __name__=='__main__': unittest.main(verbosity=2)
