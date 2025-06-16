import os
import pvporcupine
import pyaudio
import struct

# Твой API ключ от Picovoice

# RASP ACCESS_KEY = '+cs716sY8uf8TNQLnIRV4oh58560fYNC1pOFgcf8rbP0FpVYGg4lEw==' 'Ai-Nex_en_raspberry-pi_v3_0_0.ppn'
# Windows
ACCESSW_KEY = 'I1IKvHNkLoisoo2Pb2CLMMkG7JEV5T9CZxS2uYvG1wVj7LqmoetQwA=='

# Пути к твоим .ppn файлам (ключи-слова)
KEYWORD_PATHS = [
    'Ai-Nex_en_windows_v3_0_0.ppn'
]


try:
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

    print("🎧 Слушаю микрофон...")

    while True:
        pcm = audio_stream.read(porcupine.frame_length)
        pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)

        keyword_index = porcupine.process(pcm)

        if keyword_index >= 0:
            print(f"\n✅ Обнаружено ключевое слово: Ai Nex")
            # Здесь вызови нужное действие
            # Например: start_assistant(), send_notification() и т.д.

except KeyboardInterrupt:
    print("\n Остановлено пользователем.")

finally:
    # Очистка ресурсов
    if 'porcupine' in locals():
        porcupine.delete()
    if 'audio_stream' in locals():
        audio_stream.close()
    if 'pa' in locals():
        pa.terminate()