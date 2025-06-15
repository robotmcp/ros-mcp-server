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


# ==============================
# Конфигурация
# ==============================

WAKE_WORD = "nex"
MODEL_NAME = "mistralai/Mixtral-8x7B-Instruct-v0.1"


# ==============================
# TTS функция
# ==============================

def speak_with_gtts(text: str):
    """Озвучивает текст с помощью gTTS и pygame"""
    print(f"[TTS] Spech")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmpfile:
        tts = gTTS(text=text, lang="en", slow=False)
        tts.save(tmpfile.name)
        tmpfile_name = tmpfile.name

    try:
        pygame.mixer.init()
        pygame.mixer.music.load(tmpfile_name)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

    except Exception as e:
        print(f"[TTS] Play error: {e}")
    finally:
        try:
            pygame.mixer.quit()
            time.sleep(0.2)
            if os.path.exists(tmpfile_name):
                os.remove(tmpfile_name)
        except Exception as e:
            print(f"[TTS] File Error: {e}")


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
            print(f"[MCP] Res {tool_name}: {result}")
            speak_with_gtts(f"Start skill: {tool_name}")
    except Exception as e:
        print(f"[MCP] ОError call {tool_name}: {e}")
        speak_with_gtts("MCP probl...")


# ==============================
# LLM + обработка команд
# ==============================

client = Together()

SYSTEM_PROMPT = None  # Системный промпт будет загружен один раз

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

    system_prompt = (
        "You are a voice assistant controlling a robot through an MCP server.\n"
        "Available tools:\n"
    )
    for tool in tools:
        system_prompt += f"- {tool}\n"

    system_prompt += (
        "When the user gives a command like 'move forward', respond ONLY in this format:\n"
        "{\n"
        "  \"tool_call\": \"make_step\",\n"
        "  \"arguments\": {\"direction\": {\"x\": 0.0, \"z\": 1.0}}\n"
        "}\n"
        "Use only x and z axes:\n"
        "- x: -1.0 → turn left, 1.0 → turn right\n"
        "- z: -1.0 → move backward, 1.0 → move forward\n"
        "If it's not a command, just answer naturally."
    )

    SYSTEM_PROMPT = system_prompt
    return SYSTEM_PROMPT


async def handle_conversation(user_input: str):
    user_input = user_input.lower()
    print(f"User]: {user_input}")

    system_prompt = await init_system_prompt()

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            max_tokens=500,
            temperature=0.2,
            stop=["</s>"],
        )

        answer = response.choices[0].message.content.strip()
        print(f"[LLM] Ans:\n{answer}")

        # Пробуем найти JSON в ответе
        try:
            # Сначала пытаемся найти JSON внутри ```
            json_start = answer.find("```json")
            if json_start != -1:
                answer = answer[json_start + 6:]
            json_end = answer.find("```")
            if json_end != -1:
                answer = answer[:json_end]

            # Теперь пробуем просто извлечь JSON
            tool_data = json.loads(answer)
            if "tool_call" in tool_data:
                print("FindData")
                tool_name = tool_data["tool_call"]
                args = tool_data.get("arguments", {})
                await call_mcp_tool(tool_name, args)
                return
            else:
                # Проверяем, есть ли JSON внутри текста
                json_match = re.search(r'\{.*\}|\$.*\$', answer, re.DOTALL)
                if json_match:
                    tool_data = json.loads(json_match.group(0))
                    if "tool_call" in tool_data:
                        print("FindData")
                        tool_name = tool_data["tool_call"]
                        args = tool_data.get("arguments", {})
                        await call_mcp_tool(tool_name, args)
                        return
                else:
                    print("NoDATA")
        except json.JSONDecodeError as e:
            print(f"[LLM] Error JSON: {e}")
            print("NoDATA")

        # Если не нашли JSON — говорим обычный ответ
        speak_with_gtts(answer)

    except Exception as e:
        print(f"[LLM] Ошибка: {e}")
        speak_with_gtts("I couldn't understand your request.")


# ==============================
# Основной цикл
# ==============================

async def main():
    # Приветствие
    speak_with_gtts("Ainex Ready")

    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("I'm  ready. Say 'Ainex' for start...")

    while True:
        print("[Waitng...]")
        command = recognize_speech_from_mic(recognizer, mic)
        if command and WAKE_WORD in command:
            print("Detect!")
            speak_with_gtts("Yes?")

            user_query = recognize_speech_from_mic(recognizer, mic)
            if user_query:
                await handle_conversation(user_query)
            else:
                speak_with_gtts("I didn't understand you.")

        time.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(main())