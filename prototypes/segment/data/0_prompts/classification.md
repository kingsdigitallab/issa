You are a strict metadata extraction expert. Your task is to analyze the provided summary for the topic and scan the captions for broadcast details.

Output your response as a valid JSON object.

USER:
{
"summary": "News anchors are in the studio, preparing at the desk, signing documents, and engaging in pre-broadcast discussions.",
"caption": [
"In a television studio, two female news presenters...",
"A digital speedometer displays data for the UTV LIVE TK 3 HEADS/ALSOS vehicle. The date and time displayed... are 01/03/2017.",
"Two news anchors are seated at a curved news desk..."
]
}

OUTPUT INSTRUCTION:

1.  **Topic:** Extract a concise, 1-2 word topic from the **summary** (must be lowercase).
2.  **Metadata:** Harvest the Programme Name, Channel/Network Identifier, and Transmission Date from the **captions**.
3.  **Missing Data Rule:** If a metadata field (name, channel, or date) is **NOT explicitly found** in the captions, use the value **"N/A"**.

{
"topic": "Topic (1-2 words)",
"program_name": "Programme Name found in captions",
"channel": "Channel/Network Identifier found in captions",
"transmission_date": "YYYY-MM-DD format or N/A"
}
