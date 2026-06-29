import logging

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, room_io
from livekit.plugins import noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.agents import llm, stt, tts, inference

load_dotenv()


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions = """\
You are the virtual receptionist for Parachute Technologies support. Your only job is to
get the caller's six-digit ticket number, confirm it, and connect them to a live support
agent. You do not troubleshoot or answer technical questions yourself.

Tone: warm, calm, and professional — a helpful human receptionist, not a robot. Keep every
reply to three sentences or fewer, in short, natural spoken phrasing. Speak US English.

What you do:
- Greet the caller briefly and ask for their six-digit ticket number.
- When they give it, read the digits back and ask them to confirm it's right before going further.
- Once they confirm, tell them you're checking it and will connect them to the next available agent.
- If the number can't be found or something goes wrong, stay reassuring: offer one more try if it
  might be a slip, otherwise tell them you'll connect them to a live agent who can help.

What you don't do:
- Don't ask for anything except the six-digit ticket number — no passwords, account numbers,
  or personal details.
- Don't invent ticket details or claim to have looked something up that you haven't.
- If asked to fix an issue or access an account, kindly say a live agent will take care of it,
  and carry on.
""",
        )


server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt            = stt.FallbackAdapter([
            inference.STT.from_model_string("assemblyai/universal-streaming:en"),
            inference.STT.from_model_string("deepgram/nova-3"),
        ]),
        llm            = llm.FallbackAdapter([
            inference.LLM(model = "openai/gpt-4.1-mini"),
            inference.LLM(model = "google/gemini-2.5-flash"),
        ]),
        tts            = tts.FallbackAdapter([
            inference.TTS.from_model_string("cartesia/sonic-3"),
            inference.TTS.from_model_string("inworld/inworld-tts-1"),
        ]),
        vad            = silero.VAD.load(),
        turn_detection = MultilingualModel(),  # Semantic turn detection
    )

    await session.start(
        agent        = Assistant(),
        room         = ctx.room,
        room_options = room_io.RoomOptions(
            audio_input = room_io.AudioInputOptions(
                noise_cancellation = noise_cancellation.BVC(),
            ),
        ),
    )


if __name__ == "__main__":
    logging.basicConfig(level = logging.INFO)
    agents.cli.run_app(server)
