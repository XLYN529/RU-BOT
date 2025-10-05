from importlib.machinery import SourceFileLoader
path = r"c:\Users\aravi\OneDrive\Documents\Computer Science\Projects\RU_AI_Assistant\elevenlabs\11labs.py"
mod = SourceFileLoader('elevenlabs_11labs', path).load_module()
print('ELEVEN_API_KEY=', getattr(mod, 'ELEVEN_API_KEY', None))
print('GOOGLE_API_KEY=', getattr(mod, 'API_KEY', None))
print('eleven_client_initialized=', mod.eleven_client is not None)
print('\n--- CALL GEMINI (safe) ---')
try:
    res = mod.call_gemini_api('Test prompt for sanity check')
    print('gemini result:', res)
except Exception as e:
    print('gemini exception:', repr(e))

print('\n--- TTS (safe) ---')
try:
    mod.text_to_speech('This is a short test utterance.')
    print('TTS call completed')
except Exception as e:
    print('TTS exception:', repr(e))

print('\n--- STT missing file test ---')
print('speech_to_text ->', repr(mod.speech_to_text('no_such_file.wav')))
