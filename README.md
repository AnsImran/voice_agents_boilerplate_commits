# Parachute Technologies — Queue Intro Assistant

A LiveKit voice agent for the support line: it asks the caller for their 6-digit
ticket number, looks it up in ConnectWise, and routes the call to a live agent.

## To Test

### Semantic turn detection
Scenarios to verify the multilingual semantic turn detector behaves better than plain VAD:

- **Short sentences vs long sentences** — rapid-fire short sentences vs a single long sentence with
  pauses. The detector should tell a natural pause *inside* a long utterance apart from a completed
  thought, so it does **not** cut the caller off mid-sentence during the long one.
- **Background noise** — background voices (TV, nearby chatter) vs the primary speaker. The detector
  should track the **primary speaker's** turn completion and not trigger on secondary audio (plain VAD
  may activate on any sound).
- **Mid-sentence language switch** — code-switching between languages mid-turn. The multilingual
  detector should still behave naturally and keep the conversation flowing when the speaker switches
  language mid-utterance.
