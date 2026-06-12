from ai.core.speech.tts import PiperTTS


def main():
    tts = PiperTTS()

    output_path = tts.synthesize(
        text="object search mode activated.",
        output_path="defaultAudio/objectSearch_mode.wav"
    )

    print("TTS output:")
    print(output_path)


if __name__ == "__main__":
    main()