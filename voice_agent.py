import asyncio
from mcp.client.stdio import stdio_client
from together import Together
from gtts import gTTS
import pygame
import speech_recognition as sr
import tempfile
import os
import time


# ==============================
# Конфигурация
# ==============================

WAKE_WORD = "robot"
MODEL_NAME = "mistralai/Mixtral-8x7B-Instruct-v0.1"


# ==============================
# TTS функция
# ==============================

def speak_with_gtts(text: str):
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

        pygame.mixer.quit()
    finally:
        if os.path.exists(tmpfile_name):
            os.unlink(tmpfile_name)


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
    """Вызывает инструмент MCP-сервера"""
    try:
         async with stdio_client("server.py") as mcpclient:
            result = await mcpclient.call_tool(tool_name, parameters)
            print(f"[MCP] Результат вызова {tool_name}: {result}")
            speak_with_gtts(f"Выполняю: {tool_name}")
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
    await call_mcp_tool("make_step", {"direction": {"x": 0.0, "z": 1.0}})
    # Анализируем команды
    if "move forward" in user_input:
        await call_mcp_tool("make_step", {"direction": {"x": 0.0, "z": 1.0}})
    elif "move backward" in user_input:
        await call_mcp_tool("make_step", {"direction": {"x": 0.0, "z": -1.0}})
    elif "turn left" in user_input:
        await call_mcp_tool("make_step", {"direction": {"x": 1.0, "z": 0.0}})
    elif "turn right" in user_input:
        await call_mcp_tool("make_step", {"direction": {"x": -1.0, "z": 0.0}})
    elif "run action" in user_input:
        action_name = user_input.replace("run action", "").strip()
        if action_name:
            await call_mcp_tool("run_action", {"action_name": action_name})
        else:
            speak_with_gtts("Please specify an action name.")
    elif "take picture" in user_input or "get image" in user_input:
        await call_mcp_tool("get_image", {})
    else:
        # Отправляем запрос в LLM
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "user", "content": user_input},
                ],
                max_tokens=300,
                temperature=0.2,
                stop=["</s>"],
            )
            answer = response.choices[0].message.content.strip()
            print(f"[LLM] Ответ: {answer}")
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

    print("Голосовой агент запущен. Скажите 'Robot' чтобы начать...")

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

        time.sleep(0.1)


if __name__ == "__main__":
    asyncio.run(main())