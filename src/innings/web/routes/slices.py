"""Matchups, impact boards and the question box: any slice of every ball."""
from __future__ import annotations

from dataclasses import fields

from fastapi import APIRouter, HTTPException, Request

from .. import ask as asking
from ..slices import Slice, run

router = APIRouter(prefix="/api")

_TEXT = {f.name for f in fields(Slice) if f.type == "str"}
_NUMBER = {f.name for f in fields(Slice) if f.type == "int"}


def _slice_of(request: Request) -> Slice:
    """A Slice from the address's query: unknown names are ignored, bad values refused."""
    given = request.query_params
    try:
        values = {name: given[name] for name in _TEXT if given.get(name)}
        values |= {name: int(given[name]) for name in _NUMBER if given.get(name)}
        return Slice(**values)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@router.get("/slice")
def slice_of(request: Request, sort: str = ""):
    """One slice's line, and a line per part if it is split (`by`)."""
    return run(_slice_of(request), sort)


@router.get("/ask")
def ask(q: str = "", sort: str = ""):
    """A question in plain words, read into a slice and answered."""
    reading = asking.read(q)
    answer = run(reading.slice, sort or reading.sort) if reading.understood else None
    return dict(question=q, understood=reading.understood, unknown=reading.unknown,
                sort=sort or reading.sort, answer=answer, examples=asking.EXAMPLES)
