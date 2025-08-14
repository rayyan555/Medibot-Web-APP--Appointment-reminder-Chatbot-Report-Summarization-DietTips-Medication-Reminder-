from transformers import pipeline

# Load the emotion classification pipeline once
emotion_classifier = pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base", top_k=1)
def detect_emotion(text):
    result = emotion_classifier(text)

    try:
        # Flatten if needed
        if isinstance(result[0], list):
            result = result[0]
        return result[0]['label'].lower()
    except Exception as e:
        print("Emotion detection error:", e)
        return "neutral"
