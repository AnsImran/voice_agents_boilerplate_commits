import logging

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, room_io
from livekit.plugins import noise_cancellation, silero

load_dotenv()


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions = "You are a helpful voice AI assistant.",
        )


server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt = "assemblyai/universal-streaming:en",
        llm = "openai/gpt-4.1-mini",
        tts = "cartesia/sonic-3",
        vad = silero.VAD.load(),
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
