import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

FALLBACK_PROMPT = "你是一个有用的助手。请用中文回答。"


@dataclass
class Skill:
    name: str
    description: str
    instructions: str
    enabled: bool = True
    triggers: list[str] = field(default_factory=list)


class SkillLoader:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self._skills: list[Skill] = []

    @property
    def skills(self) -> list[Skill]:
        return list(self._skills)

    def load_all(self) -> None:
        if not self.skills_dir.is_dir():
            logger.warning("Skills directory not found: %s", self.skills_dir)
            return

        for yaml_file in sorted(self.skills_dir.glob("*/skill.yaml")):
            try:
                data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
                skill = Skill(
                    name=data["name"],
                    description=data["description"],
                    instructions=data.get("instructions", ""),
                    enabled=data.get("enabled", True),
                    triggers=data.get("triggers", []),
                )
                if not skill.instructions.strip():
                    logger.warning("Skill '%s' has empty instructions, skipping", skill.name)
                    continue
                self._skills.append(skill)
                logger.info("Loaded skill: %s", skill.name)
            except Exception as e:
                logger.warning("Failed to load skill from %s: %s", yaml_file, e)

    def match(self, user_message: str) -> list[Skill]:
        msg_lower = user_message.lower()
        matched = []
        for skill in self._skills:
            if not skill.enabled or not skill.triggers:
                continue
            if any(t.lower() in msg_lower for t in skill.triggers):
                matched.append(skill)
        return matched

    def build_system_prompt(self, user_message: str) -> str:
        if not self._skills:
            return FALLBACK_PROMPT

        sections = []

        # Always-ON skills (no triggers)
        for skill in self._skills:
            if not skill.enabled:
                continue
            if not skill.triggers:
                sections.append(skill.instructions.strip())

        # Matched skills
        for skill in self.match(user_message):
            sections.append(skill.instructions.strip())

        result = "\n\n".join(sections)
        return result if result.strip() else FALLBACK_PROMPT
