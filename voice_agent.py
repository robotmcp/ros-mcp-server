import asyncio
import os
import sys
import json
import tempfile
import time
import speech_recognition as sr
from gtts import gTTS
import pygame
from fastmcp import Client
from together import Together


# ==============================
# Конфигурация
# ==============================

WAKE_WORD = "robot"
MODEL_NAME = "mistralai/Mixtral-8x7B-Instruct-v0.1"


# ==============================
# TTS функция
# ==============================

def speak_with_gtts(text: str):
    """Озвучивает текст с помощью gTTS и pygame"""
    print(f"[TTS] Говорю: {text}")

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
        print(f"[TTS] Ошибка воспроизведения: {e}")
    finally:
        try:
            pygame.mixer.quit()
            time.sleep(0.2)
            if os.path.exists(tmpfile_name):
                os.remove(tmpfile_name)
        except Exception as e:
            print(f"[TTS] Не могу удалить файл: {e}")


# ==============================
# Распознавание речи
# ==============================

def recognize_speech_from_mic(recognizer, microphone):
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        print("Слушаю...")
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
            print(f"[MCP] Результат вызова {tool_name}: {result.text}")
            speak_with_gtts(f"Выполняю команду: {tool_name}")
    except Exception as e:
        print(f"[MCP] Ошибка вызова {tool_name}: {e}")
        speak_with_gtts("Не могу выполнить команду. Сервер MCP недоступен.")


# ==============================
# LLM + обработка команд
# ==============================

client = Together()

async def handle_conversation(user_input: str):
    user_input = user_input.lower()
    print(f"[Пользователь]: {user_input}")

    # Получаем список доступных инструментов
    tools = []
    try:
        async with Client("server.py") as client_mcp:
            tools = await client_mcp.list_tools()
    except Exception as e:
        speak_with_gtts("Не могу получить список действий.")
        return

    print(f"[LLM] Доступные инструменты: {tools}")

    system_prompt = (
        "You are a voice assistant controlling a robot through an MCP server.\n"
        "Available tools:\n"
    )
    for tool in tools:
        tool_info = f"- {tool}"
        try:
            tool_info += f": {getattr(client_mcp, tool).description or ''}"
        except:
            pass
        system_prompt += tool_info + "\n"

    system_prompt += (
        "When the user gives a command like 'move forward', respond ONLY in this format:\n"
        "{\n"
        "  \"tool_call\": \"tool_name\",\n"
        "  \"arguments\": {\"param1\": value1, \"param2\": value2}\n"
        "}\n"
        "If it's not a command, just answer naturally."
    )

    print("[LLM] Системный промпт:")
    print(system_prompt)

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
        print(f"[LLM] Ответ от модели:\n{answer}")

        # Пробуем распарсить как JSON
        try:
            tool_data = json.loads(answer)
            if "tool_call" in tool_data:
                tool_name = tool_data["tool_call"]
                args = tool_data.get("arguments", {})
                await call_mcp_tool(tool_name, args)
                return
        except json.JSONDecodeError:
            pass  # Это не JSON → просто текст

        # Иначе просто говорим
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

    print("Голосовой агент запущен. Скажите 'robot' чтобы начать...")

    while True:
        print("[Ожидание ключевой фразы...]")
        command = recognize_speech_from_mic(recognizer, mic)

        if command and WAKE_WORD in command:
            print("Ключевая фраза распознана!")
            speak_with_gtts("Yes?")

            user_query = recognize_speech_from_mic(recognizer, mic)
            if user_query:
                await handle_conversation(user_query)
            else:
                speak_with_gtts("I didn't understand you.")

        time.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(main())