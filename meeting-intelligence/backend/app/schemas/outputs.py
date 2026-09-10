"""
Output schemas for the Meeting Intelligence pipeline.

These Pydantic models define the structured data that the LLM
must produce. They serve as both validation and documentation
of the system's output contract.
"""

from pydantic import BaseModel, Field


class Topic(BaseModel):
    """A discussion topic identified in the meeting."""

    title: str = Field(..., description="Short title of the topic")
    summary: str = Field(
        ..., description="Brief summary of what was discussed"
    )


class Decision(BaseModel):
    """A decision that was made during the meeting."""

    decision: str = Field(..., description="What was decided")
    reason: str = Field(
        "", description="Why this decision was made, if stated"
    )
    source_reference: str = Field(
        "",
        description="Quote or reference from the transcript",
    )


class ActionItem(BaseModel):
    """A task assigned during the meeting."""

    task: str = Field(..., description="Description of the task")
    owner: str = Field(
        "", description="Person responsible, if mentioned"
    )
    deadline: str = Field(
        "", description="Due date or timeframe, if mentioned"
    )
    source_reference: str = Field(
        "",
        description="Quote or reference from the transcript",
    )


class OpenQuestion(BaseModel):
    """A question raised but not resolved in the meeting."""

    question: str = Field(..., description="The unresolved question")
    context: str = Field(
        "",
        description="Context around why this question was raised",
    )


class MeetingInsights(BaseModel):
    """
    The complete structured output of the Meeting Intelligence pipeline.

    This is the top-level response returned by the API.
    """

    meeting_id: str = Field(..., description="ID of the analyzed meeting")
    summary: str = Field(..., description="Overall meeting summary")
    topics: list[Topic] = Field(
        default_factory=list, description="Discussion topics"
    )
    decisions: list[Decision] = Field(
        default_factory=list, description="Decisions made"
    )
    action_items: list[ActionItem] = Field(
        default_factory=list, description="Action items assigned"
    )
    open_questions: list[OpenQuestion] = Field(
        default_factory=list, description="Unresolved questions"
    )
