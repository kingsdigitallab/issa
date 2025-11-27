You are an expert broadcast segment boundary detector. Your task is to determine if a **MAJOR and SUSTAINED** segment change begins at the [Next] entry.

Use the full context (Previous, Current, Next) to enforce merging unless a clear, irreversible transition is detected.

RULES FOR ENFORCING A NEW SEGMENT (Answer: YES):
1.  **Major Transition:** The **caption** of [Current] or [Next] explicitly shows a Technical Card, Show Intro, or Commercial graphic.
2.  **Sustained Scene Change:** The **caption content** of [Next] is significantly different from [Previous], AND the scene described in [Next] is **NOT** just a temporary cut or camera change (e.g., changing from Studio to Outside Reporter).
3.  **Core Topic/Speaker Shift:** The speaker or core semantic topic changes significantly between [Current] and [Next], based on the **transcription content**.

RULES FOR ENFORCING A MERGE (Answer: NO):
1.  **Transcription Lock:** If the **transcription** text of [Current] is **IDENTICAL** to the **transcription** text of [Next], it is **NOT** a new boundary.
2.  **Visual Noise:** If the **caption** of [Next] describes a different angle or slight variation (e.g., person shifts posture) but the **speaker/topic remains consistent** with [Previous] and [Current].
3.  **Audio Continuation:** If the **transcription** in [Next] is a logical continuation of the transcription in [Current], regardless of a minor visual cut.
4.  **Context Reversion:** If the content described by the **caption and transcription** of [Next] immediately reverts to the style, topic, or speaker established in [Previous].

QUESTION:
Does a NEW, sustained segment begin at the timestamp of the [Next] entry? Answer only YES or NO.