#!/usr/bin/env python3
"""Generate PDF from Sean Callagy Mastery Summary"""
from fpdf import FPDF

class MasteryPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, 'Sai Scholar | How Sean Callagy Teaches Mastery', align='C', new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

pdf = MasteryPDF()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_page()

def title(text):
    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(30, 30, 80)
    pdf.cell(0, 14, text, new_x="LMARGIN", new_y="NEXT", align='C')

def subtitle(text):
    pdf.set_font('Helvetica', 'I', 11)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT", align='C')

def divider():
    pdf.ln(3)
    pdf.set_draw_color(30, 30, 80)
    pdf.set_line_width(0.5)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(6)

def h1(text):
    pdf.ln(4)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(30, 30, 80)
    pdf.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

def h2(text):
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(50, 50, 100)
    pdf.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

def p(text):
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 5.5, text)
    pdf.ln(2)

def src(text):
    pdf.set_font('Helvetica', 'I', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 5, text)
    pdf.ln(2)

def bullet(text):
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(40, 40, 40)
    x = pdf.get_x()
    pdf.cell(8, 5.5, '  -')
    pdf.multi_cell(0, 5.5, text)
    pdf.set_x(x)

def quote(text):
    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_text_color(60, 60, 120)
    pdf.cell(10)  # indent
    pdf.multi_cell(160, 5.5, text)
    pdf.ln(2)

# === BUILD DOCUMENT ===

title('How Sean Callagy Teaches Mastery')
subtitle('A Summary by Sai Scholar | March 4, 2026')
divider()

h1('Source Transparency')
p('This document is based on Sean Callagy\'s foundational frameworks as documented in the ACT-I system architecture (SOUL.md, IDENTITY.md). I have not yet processed Sean\'s 4,000+ hours of recordings. This summary reflects the structural overview of his mastery teaching methodology - not timestamped extractions from specific sessions.')
p('Status: Preliminary framework overview. Full pattern extraction pending content access.')

h1('1. Sean Callagy - Who He Is')
p('Sean Callagy is the creator and visionary behind the ACT-I (Actualized Intelligence) ecosystem. He is one of only two attorneys to win two Top 100 National Jury Verdicts while legally blind. He has built a billion-dollar ecosystem and has produced over 4,000 hours of teaching content across multiple formats.')
p('His stated mission: to co-create the first Complete, Holistic, Diagnostic, Dynamic, Interconnected, Automated Actualization Tool for all of humanity - to end suffering, propel humanity forward, and make Earth a far greater place.')
src('(Source: IDENTITY.md)')

h1('2. The Core Mastery Frameworks')

h2('2.1 The Formula')
p('Sean\'s central teaching methodology, referred to as "the Formula." This is the foundational system that connects all his other frameworks.')
src('(Source: SOUL.md)')

h2('2.2 The 4 Steps')
p('A sequential influence and actualization process. Key dimensions:')
bullet('When Sean deploys each step')
bullet('How long each step takes')
bullet('What triggers the transition between steps')
pdf.ln(2)
src('(Source: SOUL.md)')

h2('2.3 The 4 Energies')
p('A contextual energy management system. Key dimensions:')
bullet('Which energy is used for which context')
bullet('How fast Sean shifts between energies')
bullet('What causes each energy shift')
pdf.ln(2)
src('(Source: SOUL.md)')

h2('2.4 Ecosystem Merging')
p('A system for building, integrating, and scaling ecosystems. Includes:')
bullet('Value assessment - evaluating people and opportunities')
bullet('The 6 Roles: Sourcing, Disrupting, Nurturing, Deposing, Finalizing, Actualizing')
bullet('Each role has distinct patterns Sean deploys in practice')
pdf.ln(2)
src('(Source: SOUL.md)')

h1('3. Sean\'s Influence Patterns')
p('Across all contexts - one-on-one coaching, group influence, public speaking, leadership, and management - Sean employs identifiable patterns:')

# Table header
pdf.set_font('Helvetica', 'B', 10)
pdf.set_fill_color(30, 30, 80)
pdf.set_text_color(255, 255, 255)
pdf.cell(55, 7, '  Pattern', fill=True)
pdf.cell(115, 7, '  Description', fill=True, new_x="LMARGIN", new_y="NEXT")

rows = [
    ('Acknowledgment Timing', 'Precisely timed acknowledgment of the other person\'s reality'),
    ('Truth-to-Pain Pivots', 'Transitioning from truth-telling into connecting with pain points'),
    ('Energy Shifts', 'Deliberate changes in energy to match or redirect a conversation'),
    ('Identity Elevation', 'Raising someone\'s sense of who they are and what they can do'),
    ('Contrast Usage', 'Using contrast to create clarity and drive decision-making'),
]

pdf.set_font('Helvetica', '', 9)
pdf.set_text_color(40, 40, 40)
for i, (pat, desc) in enumerate(rows):
    fill = i % 2 == 0
    if fill:
        pdf.set_fill_color(240, 240, 250)
    pdf.cell(55, 7, '  ' + pat, fill=fill)
    pdf.cell(115, 7, '  ' + desc, fill=fill, new_x="LMARGIN", new_y="NEXT")

pdf.ln(3)
src('(Source: SOUL.md)')

h1('4. Content Formats Sean Uses to Teach')
p('Sean delivers mastery teaching across multiple formats, prioritized:')
bullet('1. Heart of Influence - Primary teaching series')
bullet('2. Mastery Sessions - Deep-dive structured sessions')
bullet('3. Coaching Calls - One-on-one and small group coaching')
bullet('4. Huddles - Team-level sessions')
bullet('5. Immersions - Intensive multi-day experiences')
bullet('6. Academy Sessions - Structured learning programs')
bullet('7. Zoom Recordings - Ongoing documented sessions')
pdf.ln(2)
src('(Source: SOUL.md)')

h1('5. Group Influence Methodology')
p('Sean has a distinct approach to group influence:')
bullet('Commanding a room - techniques for capturing and holding group attention')
bullet('Causing action - moving groups from understanding to execution')
bullet('Compound influence - creating influence that multiplies through the group')
pdf.ln(2)
src('(Source: SOUL.md)')

h1('6. The Bigger Vision')
p('Sean\'s mastery teaching is not an end in itself. The ultimate goal is to replicate Sean\'s mastery at scale through ACT-I beings - so that his patterns of influence, actualization, and ecosystem building become available to all of humanity.')
quote('Pipeline: Sean teaches -> Scholar extracts patterns -> Forge injects into judges -> ACT-I beings evolve -> Mastery replicates at scale.')
src('(Source: SOUL.md, IDENTITY.md)')

h1('7. What This Document Does NOT Include (Yet)')
bullet('Specific timestamps from any recording')
bullet('Exact quotes from Sean\'s sessions')
bullet('Detailed breakdowns of each of the 4 Steps')
bullet('Detailed breakdowns of each of the 4 Energies')
bullet('Case studies from specific coaching interactions')
pdf.ln(3)
p('These require direct access to Sean\'s recorded content library. Once systematic extraction begins, each pattern will be documented with: source, timestamp, exact quote, pattern identified, and which judge it calibrates.')

divider()
h1('Conclusion')
p('Sean Callagy teaches mastery through a multi-layered, interconnected system - The Formula, The 4 Steps, The 4 Energies, Ecosystem Merging, and Group Influence patterns. He delivers this across seven content formats, each serving a different depth and context. His influence patterns (acknowledgment timing, truth-to-pain pivots, energy shifts, identity elevation, contrast usage) are consistent across all contexts but adapted to each situation.')
p('This is a framework-level overview. The full depth of Sean\'s mastery will only emerge through systematic content extraction - which is my core mission.')

pdf.ln(5)
pdf.set_font('Helvetica', 'I', 9)
pdf.set_text_color(100, 100, 100)
pdf.cell(0, 5, 'Prepared by Sai Scholar | Super Actualized Intelligence - Scholar', new_x="LMARGIN", new_y="NEXT", align='C')
pdf.cell(0, 5, 'No sources fabricated. All citations reference foundational system documents.', new_x="LMARGIN", new_y="NEXT", align='C')

output_path = '/Users/zidane/Downloads/PROJEKT/workspaces/scholar/Sean_Callagy_Mastery_Summary.pdf'
pdf.output(output_path)
print(f'PDF generated successfully: {output_path}')
