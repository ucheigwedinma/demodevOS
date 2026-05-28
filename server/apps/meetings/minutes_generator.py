"""
Meeting Minutes Generation Service.

Two approaches:
  1. AI from Live Notes — sends raw notes to AI, returns structured minutes
  2. Structured Form — formats discussion_points, decisions_made, issues_raised, action_items

Supports multiple AI providers (auto-detects from env vars):
  - ANTHROPIC_API_KEY → Claude
  - OPENAI_API_KEY → GPT-4
  - GOOGLE_API_KEY → Gemini

Falls back through providers in order. If no API key is set, structured form
generation works without AI.
"""

import json
import logging
import os

from django.utils import timezone

logger = logging.getLogger(__name__)


# ── Multi-Provider AI Client ──────────────────────────────────────────


def _call_ai(prompt: str) -> str:
    """Call the first available AI provider. Raises ValueError if none configured."""

    # Try Anthropic (Claude)
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            message = client.messages.create(
                model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text
        except ImportError:
            logger.debug("anthropic package not installed, trying next provider")
        except Exception as e:
            logger.warning(f"Anthropic API failed: {e}, trying next provider")

    # Try OpenAI (GPT-4)
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if openai_key:
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        except ImportError:
            logger.debug("openai package not installed, trying next provider")
        except Exception as e:
            logger.warning(f"OpenAI API failed: {e}, trying next provider")

    # Try Google Gemini
    google_key = os.environ.get("GOOGLE_API_KEY", "")
    if google_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=google_key)
            model = genai.GenerativeModel(os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"))
            response = model.generate_content(prompt)
            return response.text
        except ImportError:
            logger.debug("google-generativeai package not installed")
        except Exception as e:
            logger.warning(f"Google Gemini API failed: {e}")

    raise ValueError(
        "No AI provider configured. Set one of: ANTHROPIC_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY"
    )


def _get_ai_provider_name() -> str:
    """Return the name of the first available AI provider."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "Claude (Anthropic)"
    if os.environ.get("OPENAI_API_KEY"):
        return "GPT-4 (OpenAI)"
    if os.environ.get("GOOGLE_API_KEY"):
        return "Gemini (Google)"
    return "None"


# ── Meeting Context Builder ───────────────────────────────────────────


def _get_meeting_context(meeting) -> dict:
    """Extract meeting metadata for the AI prompt."""
    attendees = list(meeting.attendees.values_list("name", "role", "company", "attendance_status"))
    present = [
        f"{name} ({role}, {company})" if company else f"{name} ({role})"
        for name, role, company, status in attendees
        if status == "attended"
    ]
    absent = [
        f"{name} — {status}"
        for name, role, company, status in attendees
        if status != "attended"
    ]

    action_items = list(
        meeting.action_items.values("description", "assigned_to", "due_date", "status", "priority")
    )

    return {
        "meeting_number": meeting.meeting_number,
        "title": meeting.title,
        "meeting_type": meeting.get_meeting_type_display(),
        "series": meeting.series_name or "",
        "date": meeting.scheduled_start.strftime("%A, %d %B %Y") if meeting.scheduled_start else "",
        "time": meeting.scheduled_start.strftime("%H:%M") if meeting.scheduled_start else "",
        "location": meeting.location or "N/A",
        "project": meeting.project.name if meeting.project else "N/A",
        "recorded_by": meeting.recorded_by or "N/A",
        "present": present,
        "absent": absent,
        "agenda": meeting.agenda or [],
        "action_items": action_items,
    }


def _build_minutes_prompt(meeting, context: dict) -> str:
    """Build the AI prompt for minutes generation from live notes."""
    return f"""You are a professional meeting minutes writer for a real estate development company.
Generate formal, structured meeting minutes from the raw notes below.

MEETING DETAILS:
- Reference: {context['meeting_number']}
- Title: {context['title']}
- Type: {context['meeting_type']}
- Date: {context['date']} at {context['time']}
- Location: {context['location']}
- Project: {context['project']}
- Recorded by: {context['recorded_by']}

ATTENDEES PRESENT:
{chr(10).join(f"  • {p}" for p in context['present']) or "  Not recorded"}

APOLOGIES:
{chr(10).join(f"  • {a}" for a in context['absent']) or "  None"}

AGENDA (if set):
{json.dumps(context['agenda'], indent=2) if context['agenda'] else "  No formal agenda"}

RAW NOTES FROM THE MEETING:
---
{meeting.live_notes}
---

EXISTING ACTION ITEMS ALREADY RECORDED:
{json.dumps(context['action_items'], indent=2, default=str) if context['action_items'] else "  None recorded yet"}

INSTRUCTIONS:
1. Extract and organise the raw notes into professional meeting minutes
2. Identify DECISIONS made (who decided, what was decided, rationale if mentioned)
3. Identify ACTION ITEMS (what needs to be done, who is responsible, deadline if mentioned)
4. Identify ISSUES/RISKS raised and their resolution or next steps
5. Summarise each discussion topic clearly and concisely
6. Use professional tone appropriate for a construction/development project
7. Flag any items that seem urgent or time-critical
8. Do NOT invent information — only use what's in the notes
9. If something is unclear in the notes, mark it as "[UNCLEAR — verify with recorder]"

Format the output as clean, readable text with clear sections:
- DISCUSSION POINTS (numbered, with summary of each)
- KEY DECISIONS (numbered, with who decided)
- ACTION ITEMS (numbered, with assignee and deadline)
- ISSUES & RISKS (if any)
- NEXT MEETING (if mentioned)

Do not include any preamble or meta-commentary. Start directly with the minutes content."""


# ── Option 1: AI from Live Notes ─────────────────────────────────────


def generate_minutes_from_notes(meeting) -> str:
    """Use AI to process raw live notes into structured meeting minutes."""
    if not meeting.live_notes:
        raise ValueError("No live notes to process.")

    context = _get_meeting_context(meeting)
    prompt = _build_minutes_prompt(meeting, context)

    try:
        generated_text = _call_ai(prompt)
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"AI minutes generation failed: {e}", exc_info=True)
        raise ValueError(f"AI generation failed: {str(e)}")

    header = _format_header(context)
    provider = _get_ai_provider_name()
    footer = (
        f"\n{'=' * 72}\n"
        f"Minutes generated by AI ({provider}) from live notes on {timezone.now().strftime('%d %B %Y at %H:%M')}\n"
        f"Source: Live Notes ({len(meeting.live_notes)} characters)\n"
        f"Prepared by: {context['recorded_by']}\n"
        f"{'=' * 72}"
    )

    return f"{header}\n\n{generated_text}\n{footer}"


# ── Option 2: Structured Form ────────────────────────────────────────


def generate_minutes_from_form(meeting) -> str:
    """Generate minutes from the post-meeting structured form fields."""
    context = _get_meeting_context(meeting)
    lines = []

    # Header
    lines.append(_format_header(context))
    lines.append("")

    # Attendees
    lines.append(f"{'─' * 72}")
    lines.append("ATTENDEES")
    lines.append(f"{'─' * 72}")
    if context["present"]:
        lines.append("\nPresent:")
        for p in context["present"]:
            lines.append(f"  • {p}")
    if context["absent"]:
        lines.append("\nApologies:")
        for a in context["absent"]:
            lines.append(f"  • {a}")
    lines.append("")

    # Discussion Points
    if meeting.discussion_points:
        lines.append(f"{'─' * 72}")
        lines.append("DISCUSSION POINTS")
        lines.append(f"{'─' * 72}")
        lines.append("")
        for idx, dp in enumerate(meeting.discussion_points, 1):
            topic = dp.get("topic", "")
            summary = dp.get("summary", "")
            raised_by = dp.get("raised_by", "")
            lines.append(f"  {idx}. {topic}")
            if raised_by:
                lines.append(f"     Raised by: {raised_by}")
            if summary:
                lines.append(f"     {summary}")
            lines.append("")

    # Decisions Made
    if meeting.decisions_made:
        lines.append(f"{'─' * 72}")
        lines.append("KEY DECISIONS")
        lines.append(f"{'─' * 72}")
        lines.append("")
        for idx, dec in enumerate(meeting.decisions_made, 1):
            decision = dec.get("decision", "")
            decided_by = dec.get("decided_by", "")
            rationale = dec.get("rationale", "")
            impact = dec.get("impact", "")
            lines.append(f"  {idx}. {decision}")
            if decided_by:
                lines.append(f"     Decided by: {decided_by}")
            if rationale:
                lines.append(f"     Rationale: {rationale}")
            if impact:
                lines.append(f"     Impact: {impact}")
            lines.append("")

    # Issues Raised
    if meeting.issues_raised:
        lines.append(f"{'─' * 72}")
        lines.append("ISSUES & RISKS")
        lines.append(f"{'─' * 72}")
        lines.append("")
        for idx, issue in enumerate(meeting.issues_raised, 1):
            text = issue.get("issue", "")
            raised_by = issue.get("raised_by", "")
            resolution = issue.get("resolution", "")
            lines.append(f"  {idx}. {text}")
            if raised_by:
                lines.append(f"     Raised by: {raised_by}")
            if resolution:
                lines.append(f"     Resolution: {resolution}")
            lines.append("")

    # Action Items
    action_items = meeting.action_items.all()
    if action_items.exists():
        lines.append(f"{'─' * 72}")
        lines.append("ACTION ITEMS")
        lines.append(f"{'─' * 72}")
        lines.append("")
        for idx, ai in enumerate(action_items, 1):
            due = ai.due_date.strftime("%d/%m/%Y") if ai.due_date else "TBD"
            lines.append(f"  {idx}. {ai.description}")
            lines.append(f"     Assigned to: {ai.assigned_to}  |  Due: {due}  |  Priority: {ai.priority.title()}")
            lines.append("")

    # Notes
    if meeting.notes:
        lines.append(f"{'─' * 72}")
        lines.append("ADDITIONAL NOTES")
        lines.append(f"{'─' * 72}")
        lines.append(f"\n  {meeting.notes}\n")

    # Footer
    lines.append(f"{'=' * 72}")
    lines.append(f"Minutes generated from structured form on {timezone.now().strftime('%d %B %Y at %H:%M')}")
    lines.append(f"Prepared by: {context['recorded_by']}")
    lines.append(f"{'=' * 72}")

    return "\n".join(lines)


# ── AI Enhancement of Structured Form ─────────────────────────────────


def enhance_form_minutes_with_ai(meeting) -> str:
    """Take structured form minutes and have AI polish them into natural language."""
    raw_minutes = generate_minutes_from_form(meeting)

    try:
        polished = _call_ai(
            f"""Rewrite these meeting minutes into more natural, professional language.
Keep all factual content exactly the same — do not add or remove any information.
Improve readability, flow, and professional tone.
Keep the section structure (Discussion Points, Decisions, Action Items, etc.).
Keep it concise — these are formal minutes, not a narrative.

RAW MINUTES:
---
{raw_minutes}
---

Return only the improved minutes text. No preamble."""
        )
        return polished
    except Exception:
        logger.debug("AI enhancement failed, returning raw structured minutes", exc_info=True)
        return raw_minutes


# ── Auto-detect best approach ─────────────────────────────────────────


def auto_generate_minutes(meeting) -> tuple[str, str]:
    """Automatically pick the best generation method and return (text, source).

    Returns:
        tuple: (minutes_text, source) where source is one of MinutesSource values
    """
    # Priority 1: Live notes → AI
    if meeting.live_notes and len(meeting.live_notes.strip()) > 50:
        try:
            text = generate_minutes_from_notes(meeting)
            return text, "ai_from_notes"
        except ValueError:
            logger.info("AI generation unavailable, falling back to structured form")

    # Priority 2: Structured form data
    has_form_data = (
        meeting.discussion_points
        or meeting.decisions_made
        or meeting.issues_raised
        or meeting.action_items.exists()
    )
    if has_form_data:
        try:
            text = enhance_form_minutes_with_ai(meeting)
            return text, "ai_from_form"
        except Exception:
            text = generate_minutes_from_form(meeting)
            return text, "ai_from_form"

    # Priority 3: Nothing to generate
    raise ValueError(
        "Cannot generate minutes — no live notes or structured form data. "
        "Either type notes during the meeting (Live Notes) or fill out the "
        "post-meeting form (Discussion Points, Decisions, Action Items)."
    )


# ── Helpers ───────────────────────────────────────────────────────────


def _format_header(context: dict) -> str:
    lines = [
        f"{'=' * 72}",
        f"MEETING MINUTES",
        f"{'=' * 72}",
        "",
        f"Reference:    {context['meeting_number']}",
        f"Title:        {context['title']}",
        f"Type:         {context['meeting_type']}",
    ]
    if context["series"]:
        lines.append(f"Series:       {context['series']}")
    lines.extend([
        f"Date:         {context['date']}",
        f"Time:         {context['time']}",
        f"Location:     {context['location']}",
        f"Project:      {context['project']}",
        f"Recorded By:  {context['recorded_by']}",
    ])
    return "\n".join(lines)
