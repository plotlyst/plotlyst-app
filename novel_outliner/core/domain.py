from dataclasses import dataclass, field
from typing import List, Optional

ACTION_SCENE = 'action'
REACTION_SCENE = 'reaction'


@dataclass(unsafe_hash=True)
class Character:
    name: str
    id: Optional[int] = None
    personality: str = ''
    age: int = 0
    image_path: str = ''


@dataclass
class Scene:
    title: str
    id: Optional[int] = None
    synopsis: str = ''
    type: str = ''
    pivotal: bool = False
    event_1: str = ''
    event_2: str = ''
    event_3: str = ''
    pov: Optional[Character] = None
    characters: List[Character] = field(default_factory=list)
    wip: bool = False


@dataclass
class Novel:
    title: str
    id: Optional[int] = None
    config_path: str = ''
    characters: List[Character] = field(default_factory=list)
    scenes: List[Scene] = field(default_factory=list)
