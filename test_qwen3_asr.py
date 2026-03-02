#!/usr/bin/env python3
"""
Test script for Qwen3-ASR STT engine integration
"""
import sys
import os

def test_imports():
    """Test that all imports work correctly"""
    try:
        # Test importing the main module
        import main
        print("✅ main.py imports successfully")
        
        # Test importing the Qwen3ASRSTT class directly
        from stt.qwen3_asr import Qwen3ASRSTT
        print("✅ Qwen3ASRSTT imports successfully")
        
        # Test that it inherits from BaseSTT
        from stt.base import BaseSTT
        assert issubclass(Qwen3ASRSTT, BaseSTT), "Qwen3ASRSTT must inherit from BaseSTT"
        print("✅ Qwen3ASRSTT inherits from BaseSTT")
        
        return True
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_build_stt():
    """Test that build_stt() function can create Qwen3ASRSTT instance"""
    try:
        import main
        
        # Test config with qwen3_asr engine
        config = {"stt_engine": "qwen3_asr"}
        
        # This should create a Qwen3ASRSTT instance
        stt_instance = main.build_stt(config)
        
        # Check that we got the right type
        from stt.qwen3_asr import Qwen3ASRSTT
        assert isinstance(stt_instance, Qwen3ASRSTT), f"Expected Qwen3ASRSTT, got {type(stt_instance)}"
        print("✅ build_stt() creates Qwen3ASRSTT instance")
        
        return True
    except Exception as e:
        print(f"❌ build_stt test failed: {e}")
        return False

def test_method_signature():
    """Test that Qwen3ASRSTT has the correct method signature"""
    try:
        from stt.qwen3_asr import Qwen3ASRSTT
        import inspect
        
        # Check that transcribe method exists and has correct signature
        transcribe_method = getattr(Qwen3ASRSTT, 'transcribe', None)
        assert transcribe_method is not None, "transcribe method not found"
        
        sig = inspect.signature(transcribe_method)
        params = list(sig.parameters.keys())
        
        # Should have self, audio_bytes, and language parameters
        expected_params = ['self', 'audio_bytes', 'language']
        for param in expected_params:
            assert param in params, f"Missing parameter: {param}"
        
        print("✅ Qwen3ASRSTT.transcribe() has correct signature")
        return True
    except Exception as e:
        print(f"❌ Method signature test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Running Qwen3-ASR integration tests...\n")
    
    tests = [
        test_imports,
        test_build_stt,
        test_method_signature
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())