import asyncio
import os
import sys
import json
import tempfile
import time
import re

import speech_recognition as sr
from gtts import gTTS
import pygame
from fastmcp import Client
from together import Together
import pyaudio
import struct
import threading
from hashlib import md5
# ==============================
# Проба замены метода активации
# ==============================
import pvporcupine

# Твой API ключ от Picovoice

# RASP ACCESS_KEY = '+cs716sY8uf8TNQLnIRV4oh58560fYNC1pOFgcf8rbP0FpVYGg4lEw==' 'Ai-Nex_en_raspberry-pi_v3_0_0.ppn'
# Windows
ACCESSW_KEY = os.getenv("WAKEUP_API_KEY")

# Пути к твоим .ppn файлам (ключи-слова)
KEYWORD_PATHS = [
    'Ai-Nex_en_windows_v3_0_0.ppn'
]
# ==============================
# Конфигурация
# ==============================

WAKE_WORD = "nex"
MODEL_NAME = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"

# ==============================
# TTS функция
# ==============================

# Кеш для аудиофайлов: {hash(text) -> путь_к_файлу}
tts_cache = {}
# Блокировка для безопасного доступа к кешу из разных потоков
cache_lock = threading.Lock()

# Флаг для завершения работы
tts_active = True

message_history = []
history_active = False
text_input = False

def speak_with_gtts(text: str):
    """Озвучивает текст с помощью gTTS и pygame. Поддерживает кеширование."""
    print(f"[TTS] Speech: {text}")

    # Хэшируем текст для ключа в кеше
    text_hash = md5(text.encode("utf-8")).hexdigest()
    
    with cache_lock:
        if text_hash in tts_cache:
            audio_file = tts_cache[text_hash]
            print(f"[TTS] Using cached audio for: {text}")
        else:
            # Создаем временный файл и сохраняем речь
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmpfile:
                tts = gTTS(text=text, lang="en", slow=False)
                tts.save(tmpfile.name)
                audio_file = tmpfile.name
                tts_cache[text_hash] = audio_file
                print(f"[TTS] Generated new audio for: {text}")

    # Проигрываем в отдельном потоке
    threading.Thread(target=play_audio, args=(audio_file,)).start()


def play_audio(file_path: str):
    """Проигрывает аудиофайл через pygame"""
    try:
        # Инициализируем mixer один раз
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy() and tts_active:
            time.sleep(0.1)

    except Exception as e:
        print(f"[TTS] Play error: {e}")


def stop_tts():
    """Останавливает воспроизведение и очищает ресурсы"""
    global tts_active
    tts_active = False
    pygame.mixer.quit()
    
    # Опционально: удаление временных файлов из кеша
    for path in tts_cache.values():
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            print(f"[TTS] File deletion error: {e}")

# ==============================
# Распознавание речи
# ==============================

def recognize_speech_from_mic(recognizer, microphone):
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        print("I'm listening...")
        audio = recognizer.listen(source)

    try:
        return recognizer.recognize_google(audio, language="en-US").lower()
    except sr.UnknownValueError:
        return None

# ==============================
# Клиент FastMCP
# ==============================

async def call_mcp_tool(tool_name: str, parameters: dict):
    """Вызывает инструмент MCP-сервера через FastMCP"""
    try:
        async with Client("server.py") as client:
            result = await client.call_tool(tool_name, parameters)
            print(f"[MCP] Result for {tool_name}: {result}")
            return True, result
    except Exception as e:
        print(f"[MCP] Error calling {tool_name}: {e}")
        return False, str(e)

# ==============================
# LLM + обработка команд
# ==============================

client = Together()
SYSTEM_PROMPT = None

async def init_system_prompt():
    """Формируем системный промпт один раз"""
    global SYSTEM_PROMPT
    if SYSTEM_PROMPT is not None:
        return SYSTEM_PROMPT

    tools = []
    try:
        async with Client("server.py") as mcp_client:
            tools = await mcp_client.list_tools()
    except Exception as e:
        print(f"[LLM] Не могу получить список инструментов: {e}")
        tools = []

    result = await call_mcp_tool("get_available_actions", {})

    # Упрощенный и более понятный системный промпт
    SYSTEM_PROMPT = (
        "You are a voice assistant controlling a robot through an MCP server.\n"
        "Available tools:\n" + 
        "\n".join([f"- {tool}" for tool in tools]) +
        "Available actions for tool 'run_action', for 'run_action': Use ONLY action names WITHOUT .d6a extension\n" +
        "\n".join([f"- {result}"]) + 
        "\n\nRespond ONLY in this JSON format:\n"
        "{\n"
        '  "answer": "Your response to the user",\n'
        '  "commands": [\n'
        '    {\n'
        '      "tool": "tool_name",\n'
        '      "params": {"param1": "value1"}\n'
        '    },\n'
        '    ...\n'
        '  ]\n'
        "}\n"
        "Rules:\n"
        "1. 'commands' must be a list (can be empty)\n"
        "2. Only include parameters if the tool requires them\n"
        "3. Keep your verbal response (answer) concise\n"
        "4. If user asks to perform actions, include them in commands\n"
        "5. For make_step use parametr x and z. x move robot left (1.0) and right (-1.0), z move robot forward(1.0) and back(-1.0) if you just move forward set z 1.0 and x 0 :\n"
        "Example for 'turn on the light':\n"
        "{\n"
        '  "answer": "Turning on the light",\n'
        '  "commands": [\n'
        '    {"tool": "light_on", "params": {}}\n'
        '  ]\n'
        "}\n"
    )
    
    return SYSTEM_PROMPT

async def handle_conversation(user_input: str):
    global message_history

    user_input = user_input.lower()
    print(f"[User]: {user_input}")

    system_prompt = await init_system_prompt()
    message_history = [
        {"role": "system", "content": system_prompt},
    ]

    message_history.append({"role": "user", "content": user_input})

    print(f"Waiting LLM...")
    try:
        response = None
        if history_active: 
            response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=message_history,
                    max_tokens=800,
                    temperature=0.2,
                    stop=["</s>"],
            )
        else:
            response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_input}
                    ],
                    max_tokens=800,
                    temperature=0.2,
                    stop=["</s>"],
            )

        answer = response.choices[0].message.content.strip()
        print(f"[LLM] Raw response:\n{answer}")

        # Улучшенная обработка JSON
        json_str = answer
        if "```json" in answer:
            json_str = answer.split("```json")[1].split("```")[0].strip()
        elif "```" in answer:
            json_str = answer.split("```")[1].strip()
        
        try:
            response_data = json.loads(json_str)
             
            # Обрабатываем команды
            commands = response_data.get("commands", [])
            if not isinstance(commands, list):
                commands = [commands]
                
            for command in commands:
                if not isinstance(command, dict):
                    continue
                    
                tool_name = command.get("tool")
                params = command.get("params", {})
                
                if tool_name:
                    success, result = await call_mcp_tool(tool_name, params)
                    if not success:
                        speak_with_gtts(f"Failed to execute {tool_name}")
                else:
                    print("[LLM] Missing tool name in command")
                    

            # Добавляем ответ ассистента в историю
            message_history.append({"role": "assistant", "content": answer})

            # Озвучиваем ответ
            verbal_response = response_data.get("answer", "I'll execute your request")
            speak_with_gtts(verbal_response)


        except json.JSONDecodeError as e:
            print(f"[LLM] JSON decode error: {e}")
            speak_with_gtts("I had trouble processing your request")
        except Exception as e:
            print(f"[LLM] Response handling error: {e}")
            speak_with_gtts("Something went wrong with my response")

    except Exception as e:
        print(f"[LLM] Request error: {e}")
        speak_with_gtts("I couldn't process your request")

# ==============================
# Основной цикл
# ==============================

async def main():

    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    speak_with_gtts("AiNex ready")
    
    # Создаем экземпляр Porcupine
    porcupine = pvporcupine.create(
        access_key=ACCESSW_KEY,
        keyword_paths=KEYWORD_PATHS
    )

    # Настройка аудио потока
    pa = pyaudio.PyAudio()
    audio_stream = pa.open(
        rate=porcupine.sample_rate,
        format=pyaudio.paInt16,
        channels=1,
        input=True,
        frames_per_buffer=porcupine.frame_length
    )

    print(f"Say AiNex to start...")
    try:
        while True:

            if text_input:
                user_query = input(str(""))
                if user_query:
                    await handle_conversation(user_query)
            
            pcm = audio_stream.read(porcupine.frame_length)
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)

            keyword_index = porcupine.process(pcm)

            if keyword_index >= 0:
                print("Wake word detected!")
                speak_with_gtts("Yes?")
                print("Listening for command...")
                user_query = recognize_speech_from_mic(recognizer, mic)
                if user_query:
                    await handle_conversation(user_query)
                else:
                    speak_with_gtts("I didn't catch that")
    except KeyboardInterrupt:
        print("\n User stop")

    finally:
        # Очистка ресурсов
        stop_tts()
        if 'porcupine' in locals():
            porcupine.delete()
        if 'audio_stream' in locals():
            audio_stream.close()
        if 'pa' in locals():
            pa.terminate()


if __name__ == "__main__":
    asyncio.run(main())