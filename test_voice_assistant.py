#!/usr/bin/env python3
"""
Test script for the ElevenLabs voice assistant.
This validates the API integrations without requiring microphone input.
"""
import os
import sys
from dotenv import load_dotenv

# Add elevenlabs directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'elevenlabs'))

def test_env_setup():
    """Check if required environment variables are set"""
    load_dotenv()
    
    print("="*60)
    print("ENVIRONMENT SETUP CHECK")
    print("="*60)
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    eleven_key = os.getenv("ELEVENLABS_API_KEY")
    
    if gemini_key:
        print("✅ GEMINI_API_KEY is set")
    else:
        print("❌ GEMINI_API_KEY is missing - add it to .env file")
    
    if eleven_key:
        print("✅ ELEVENLABS_API_KEY is set")
    else:
        print("⚠️  ELEVENLABS_API_KEY is missing - voice features will be disabled")
    
    return gemini_key is not None


def test_imports():
    """Test if all required modules can be imported"""
    print("\n" + "="*60)
    print("IMPORT TEST")
    print("="*60)
    
    try:
        from google import genai
        from google.genai import types
        print("✅ google-genai library imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import google-genai: {e}")
        return False
    
    try:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import stream
        print("✅ elevenlabs library imported successfully")
    except ImportError as e:
        print(f"⚠️  elevenlabs library not found: {e}")
        print("   Run: pip install elevenlabs")
    
    try:
        import sounddevice as sd
        print("✅ sounddevice library imported successfully")
    except ImportError as e:
        print(f"⚠️  sounddevice library not found: {e}")
        print("   Run: pip install sounddevice")
    
    try:
        import numpy
        print("✅ numpy library imported successfully")
    except ImportError as e:
        print(f"❌ numpy library not found: {e}")
        print("   Run: pip install numpy")
        print("   (Required by sounddevice for audio recording)")
        return False
    
    return True


def test_gemini_integration():
    """Test if Gemini API works correctly"""
    print("\n" + "="*60)
    print("GEMINI API TEST")
    print("="*60)
    
    try:
        # Import the function we fixed
        import sys
        sys.path.insert(0, 'elevenlabs')
        from elevenlabs.labs import call_gemini_api
        
        # Test with a simple prompt
        test_prompt = "Say 'Hello from Rutgers!' in one sentence."
        print(f"Sending test prompt: {test_prompt}")
        
        response = call_gemini_api(test_prompt)
        
        if response and "Rutgers" in response:
            print("✅ Gemini API is working!")
            print(f"Response: {response[:200]}")
            return True
        else:
            print(f"⚠️  Got response but it seems unexpected: {response[:200]}")
            return False
            
    except ImportError as e:
        print(f"❌ Could not import the module: {e}")
        # Try importing directly from the file
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "labs", 
                "/Users/fawwaazsheik/codingggg/rupersonalassistant/RU_AI_Assistant/elevenlabs/11labs.py"
            )
            labs = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(labs)
            
            test_prompt = "Say 'Hello from Rutgers!' in one sentence."
            print(f"Sending test prompt: {test_prompt}")
            response = labs.call_gemini_api(test_prompt)
            
            if response and len(response) > 0:
                print("✅ Gemini API is working!")
                print(f"Response: {response[:200]}")
                return True
            else:
                print(f"⚠️  Got empty or error response")
                return False
        except Exception as e2:
            print(f"❌ Failed to test Gemini: {e2}")
            return False
    except Exception as e:
        print(f"❌ Error testing Gemini API: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n🧪 Testing Voice Assistant Components\n")
    
    # Test 1: Environment setup
    env_ok = test_env_setup()
    
    # Test 2: Imports
    imports_ok = test_imports()
    
    # Test 3: Gemini API (only if env is set up)
    gemini_ok = False
    if env_ok and imports_ok:
        gemini_ok = test_gemini_integration()
    else:
        print("\n⚠️  Skipping Gemini test - environment or imports not ready")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Environment Setup: {'✅ PASS' if env_ok else '❌ FAIL'}")
    print(f"Library Imports:   {'✅ PASS' if imports_ok else '❌ FAIL'}")
    print(f"Gemini API:        {'✅ PASS' if gemini_ok else '⚠️  SKIP/FAIL'}")
    
    if env_ok and imports_ok and gemini_ok:
        print("\n🎉 All tests passed! The voice assistant should work.")
        print("\n📝 Next steps:")
        print("   1. Make sure you have an audio input device (microphone)")
        print("   2. Run: python elevenlabs/11labs.py")
        print("   3. Press Enter and speak for 5 seconds")
    else:
        print("\n⚠️  Some issues detected. Please fix them before running the voice assistant.")
        if not env_ok:
            print("   - Add GEMINI_API_KEY to your .env file")
        if not imports_ok:
            print("   - Install missing dependencies: pip install -r requirements.txt")


if __name__ == "__main__":
    main()
