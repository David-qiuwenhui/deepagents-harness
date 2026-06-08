"""Skill 系统测试

覆盖: Skill 解析、关键词匹配、prompt 拼接、错误处理
"""

from pathlib import Path

import pytest
import yaml

from agent.skills import Skill, SkillLoader


class TestSkillDataclass:
    def test_skill_defaults(self):
        skill = Skill(name="test", description="desc", instructions="do stuff")
        assert skill.enabled is True
        assert skill.triggers == []

    def test_skill_with_triggers(self):
        skill = Skill(name="t", description="d", instructions="i", triggers=["a", "b"])
        assert len(skill.triggers) == 2


class TestSkillLoaderLoad:
    def test_load_from_directory(self, tmp_path):
        skill_dir = tmp_path / "test_skill"
        skill_dir.mkdir()
        (skill_dir / "skill.yaml").write_text(
            yaml.dump({
                "name": "测试技能",
                "description": "测试用",
                "enabled": True,
                "triggers": ["测试"],
                "instructions": "这是一个测试技能",
            }),
            encoding="utf-8",
        )

        loader = SkillLoader(tmp_path)
        loader.load_all()
        assert len(loader.skills) == 1
        assert loader.skills[0].name == "测试技能"

    def test_load_multiple_skills(self, tmp_path):
        for i in range(3):
            d = tmp_path / f"skill_{i}"
            d.mkdir()
            (d / "skill.yaml").write_text(
                yaml.dump({
                    "name": f"技能{i}",
                    "description": f"第{i}个",
                    "instructions": f"指令{i}",
                    "triggers": [f"触发{i}"],
                }),
                encoding="utf-8",
            )

        loader = SkillLoader(tmp_path)
        loader.load_all()
        assert len(loader.skills) == 3

    def test_load_skips_empty_instructions(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        (d / "skill.yaml").write_text(
            yaml.dump({"name": "空", "description": "无指令", "instructions": "   "}),
            encoding="utf-8",
        )

        loader = SkillLoader(tmp_path)
        loader.load_all()
        assert len(loader.skills) == 0

    def test_load_skips_invalid_yaml(self, tmp_path):
        d = tmp_path / "bad"
        d.mkdir()
        (d / "skill.yaml").write_text("{{invalid yaml", encoding="utf-8")

        loader = SkillLoader(tmp_path)
        loader.load_all()
        assert len(loader.skills) == 0

    def test_load_missing_dir_uses_fallback(self, tmp_path):
        loader = SkillLoader(tmp_path / "nonexistent")
        loader.load_all()
        assert loader.skills == []
        assert loader.build_system_prompt("hello") == "你是一个有用的助手。请用中文回答。"

    def test_load_disabled_skill(self, tmp_path):
        d = tmp_path / "disabled"
        d.mkdir()
        (d / "skill.yaml").write_text(
            yaml.dump({
                "name": "禁用技能",
                "description": "被禁用",
                "enabled": False,
                "instructions": "不应出现",
                "triggers": ["禁用"],
            }),
            encoding="utf-8",
        )

        loader = SkillLoader(tmp_path)
        loader.load_all()
        matched = loader.match("禁用测试")
        assert len(matched) == 0


class TestSkillLoaderMatch:
    def test_match_single_trigger(self, tmp_path):
        d = tmp_path / "skill"
        d.mkdir()
        (d / "skill.yaml").write_text(
            yaml.dump({
                "name": "记忆",
                "description": "记忆",
                "instructions": "记忆指令",
                "triggers": ["记住", "回忆"],
            }),
            encoding="utf-8",
        )

        loader = SkillLoader(tmp_path)
        loader.load_all()
        matched = loader.match("帮我记住这个")
        assert len(matched) == 1
        assert matched[0].name == "记忆"

    def test_match_multiple_skills(self, tmp_path):
        for name, triggers in [("A", ["苹果"]), ("B", ["香蕉"]), ("C", ["橙子"])]:
            d = tmp_path / name
            d.mkdir()
            (d / "skill.yaml").write_text(
                yaml.dump({
                    "name": name,
                    "description": name,
                    "instructions": f"{name}指令",
                    "triggers": triggers,
                }),
                encoding="utf-8",
            )

        loader = SkillLoader(tmp_path)
        loader.load_all()
        matched = loader.match("我要苹果和香蕉")
        assert len(matched) == 2
        names = {s.name for s in matched}
        assert names == {"A", "B"}

    def test_no_match(self, tmp_path):
        d = tmp_path / "skill"
        d.mkdir()
        (d / "skill.yaml").write_text(
            yaml.dump({
                "name": "X",
                "description": "X",
                "instructions": "X指令",
                "triggers": ["特定词"],
            }),
            encoding="utf-8",
        )

        loader = SkillLoader(tmp_path)
        loader.load_all()
        assert loader.match("完全无关的消息") == []

    def test_always_on_skills_not_in_match(self, tmp_path):
        d = tmp_path / "general"
        d.mkdir()
        (d / "skill.yaml").write_text(
            yaml.dump({
                "name": "通用",
                "description": "通用",
                "instructions": "通用指令",
                "triggers": [],
            }),
            encoding="utf-8",
        )

        loader = SkillLoader(tmp_path)
        loader.load_all()
        assert loader.match("任何消息") == []


class TestBuildSystemPrompt:
    def test_general_only(self, tmp_path):
        d = tmp_path / "general"
        d.mkdir()
        (d / "skill.yaml").write_text(
            yaml.dump({
                "name": "通用",
                "description": "通用",
                "instructions": "你是助手。",
                "triggers": [],
            }),
            encoding="utf-8",
        )

        loader = SkillLoader(tmp_path)
        loader.load_all()
        prompt = loader.build_system_prompt("你好")
        assert "你是助手。" in prompt

    def test_general_plus_matched(self, tmp_path):
        d = tmp_path / "general"
        d.mkdir()
        (d / "skill.yaml").write_text(
            yaml.dump({
                "name": "通用",
                "description": "通用",
                "instructions": "你是助手。",
                "triggers": [],
            }),
            encoding="utf-8",
        )

        d2 = tmp_path / "memory"
        d2.mkdir()
        (d2 / "skill.yaml").write_text(
            yaml.dump({
                "name": "记忆",
                "description": "记忆",
                "instructions": "使用 save_memory。",
                "triggers": ["记住"],
            }),
            encoding="utf-8",
        )

        loader = SkillLoader(tmp_path)
        loader.load_all()
        prompt = loader.build_system_prompt("帮我记住这个")
        assert "你是助手。" in prompt
        assert "使用 save_memory。" in prompt

    def test_fallback_when_no_skills(self, tmp_path):
        loader = SkillLoader(tmp_path)
        loader.load_all()
        prompt = loader.build_system_prompt("hello")
        assert prompt == "你是一个有用的助手。请用中文回答。"


class TestRealSkills:
    """验证项目中实际的 Skill YAML 文件能正确加载"""

    def test_load_project_skills(self):
        skills_dir = Path(__file__).parent.parent / "src" / "agent" / "skills"
        loader = SkillLoader(skills_dir)
        loader.load_all()
        assert len(loader.skills) == 3

        names = {s.name for s in loader.skills}
        assert names == {"通用助手", "记忆助手", "知识库"}

    def test_memory_skill_match(self):
        skills_dir = Path(__file__).parent.parent / "src" / "agent" / "skills"
        loader = SkillLoader(skills_dir)
        loader.load_all()

        matched = loader.match("帮我记住这个名字")
        names = {s.name for s in matched}
        assert "记忆助手" in names

    def test_wiki_skill_match(self):
        skills_dir = Path(__file__).parent.parent / "src" / "agent" / "skills"
        loader = SkillLoader(skills_dir)
        loader.load_all()

        matched = loader.match("查一下知识库")
        names = {s.name for s in matched}
        assert "知识库" in names

    def test_general_always_present(self):
        skills_dir = Path(__file__).parent.parent / "src" / "agent" / "skills"
        loader = SkillLoader(skills_dir)
        loader.load_all()

        prompt = loader.build_system_prompt("你好")
        assert "有用的助手" in prompt
