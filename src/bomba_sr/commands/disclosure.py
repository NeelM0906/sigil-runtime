from __future__ import annotations

from xml.sax.saxutils import escape

from bomba_sr.skills.descriptor import SkillDescriptor


class SkillDisclosure:
    def format_skill_index_xml(self, skills: dict[str, SkillDescriptor]) -> str:
        rows = []
        invokable = [s for s in skills.values() if not s.disable_model_invocation]
        rows.append(f'<available_skills count="{len(invokable)}">')
        for skill in sorted(invokable, key=lambda s: s.skill_id):
            command = f"/{skill.name}"
            rows.append(
                '  <skill id="{id}" command="{command}" description="{description}" risk="{risk}" />'.format(
                    id=escape(skill.skill_id),
                    command=escape(command),
                    description=escape(skill.description),
                    risk=escape(skill.risk_level),
                )
            )
        rows.append("</available_skills>")
        return "\n".join(rows)

    def format_skill_body_context(self, skill: SkillDescriptor, body: str) -> str:
        return (
            f"<selected_skill id=\"{escape(skill.skill_id)}\" name=\"{escape(skill.name)}\">\n"
            f"{escape(body)}\n"
            "</selected_skill>"
        )

    def estimate_index_tokens(self, skills: dict[str, SkillDescriptor]) -> int:
        total = 15
        for skill in skills.values():
            if skill.disable_model_invocation:
                continue
            total += 20 + len(skill.skill_id) + len(skill.name) + len(skill.description)
        return total
