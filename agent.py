import logging
from dataclasses import dataclass

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentServer, AgentSession, AgentTask, JobContext, RunContext, function_tool, room_io
from livekit.plugins import noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.agents import llm, stt, tts, inference
from tools import lookup_ticket, transfer_to_human

load_dotenv()


MAIN_VOICE    = "cartesia/sonic-3:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"
MANAGER_VOICE = "cartesia/sonic-3:6f84f4b8-58a2-430c-8c79-688dad597532"


@dataclass
class TicketId:
    number: int


class CollectTicketId(AgentTask[TicketId]):
    def __init__(self, chat_ctx = None) -> None:
        super().__init__(
            instructions = """\
Collect the caller's six-digit support ticket number. Accept only a number that is exactly six digits.
Read the digits back and ask them to confirm before recording it. If it isn't six digits, politely ask again.""",
            chat_ctx     = chat_ctx,
        )

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions = "Ask the caller for their six-digit ticket number.",
        )

    @function_tool()
    async def record_ticket(self, context: RunContext, ticket_number: str) -> None:
        """Record the caller's six-digit ticket number once they have confirmed it is correct.

        Args:
            ticket_number: The confirmed ticket number, digits only and exactly six digits long.
        """
        context.disallow_interruptions()
        digits = ticket_number.strip()
        if not (digits.isdigit() and len(digits) == 6):
            await self.session.generate_reply(
                instructions = "Explain the ticket number must be exactly six digits, and ask for it again.",
            )
            return
        self.complete(TicketId(number = int(digits)))


class ManagerAgent(Agent):
    def __init__(self, chat_ctx = None) -> None:
        super().__init__(
            instructions = """\
You are a senior support representative — a supervisor — for Parachute Technologies. You take calls
escalated from the front-line assistant: when a caller asks for a manager, or their issue couldn't be
resolved. Be empathetic, calm, and solution-focused. Acknowledge their concern, help where you can, and
if they need a person, use the transfer_to_human tool to connect them. Keep replies to three sentences
or fewer, in short, natural spoken phrasing. Speak US English.""",
            chat_ctx     = chat_ctx,
            tts          = inference.TTS.from_model_string(MANAGER_VOICE),
            tools        = [transfer_to_human],
        )

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions = "Introduce yourself as the manager, acknowledge they asked for someone senior, and ask how you can help.",
        )


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions = """\
You are the virtual receptionist for Parachute Technologies support. Your job is to take the caller's
six-digit ticket number, look it up, and connect them to a live agent. You do not troubleshoot or
answer technical questions yourself.

Tone: warm, calm, and professional — a helpful human receptionist, not a robot. Keep every reply to
three sentences or fewer, in short, natural spoken phrasing. Speak US English.

What you do:
- After you have the caller's confirmed six-digit ticket number, use the lookup_ticket tool to look it
  up, then briefly read back what it returns (the ticket's summary and status) so they know you found
  the right one.
- Then use the transfer_to_human tool to connect them to the next available agent.
- If the lookup fails or the ticket can't be found, stay reassuring: offer one more try if it might be a
  slip, otherwise use transfer_to_human to connect them to a live agent.
- If the caller asks for a manager or a supervisor, or you can't help them, use the escalate_to_manager tool.

What you don't do:
- Don't ask for anything except the six-digit ticket number — no passwords, account numbers, or personal details.
- Don't invent ticket details or claim to have looked something up that you haven't.""",
            tools        = [lookup_ticket, transfer_to_human],
        )

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions = """\
Briefly introduce yourself as the Parachute Technologies support assistant who connects callers to the
right person, and let them know this call is recorded for quality assurance and training. Keep it to one
short sentence. Do NOT ask how you can help, do NOT offer general assistance, and do NOT ask any question
— the next step asks for the ticket number.""",
        )
        ticket = await CollectTicketId(chat_ctx = self.chat_ctx)
        await self.session.generate_reply(
            instructions = f"Look up ticket number {ticket.number} using the lookup_ticket tool.",
        )

    @function_tool()
    async def escalate_to_manager(self, context: RunContext):
        """Transfer the caller to a manager when they ask for one or when you cannot resolve their issue."""
        context.disallow_interruptions()
        return ManagerAgent(chat_ctx = self.chat_ctx), "Transferring you to a manager now."


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
            inference.TTS.from_model_string(MAIN_VOICE),
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
